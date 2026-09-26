#!/usr/bin/env python3
"""CPU+RAM 전용 dual-resident 128K 서버 + 32K measured request 러너 (WBS 6).

Contract:
- WBS 6.1: P520 Xeon W-2135 호스트에서 직접 빌드한 native CPU-only Docker image
  (선정된 공식 build: b10775 / commit 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb)
- Coexistence envelope:
  - logical CPU IDs 1, 2, 3, 4 (each mapped to distinct physical cores CORE 1, 2, 3, 4)
  - -t 4 -tb 4 -b 1024 -ub 256 --cpu-strict 1 --poll 50
  - --load-mode mmap --cache-ram 0 --no-cache-prompt --no-context-shift --threads-http 1 --no-webui
- ngram-mod: --spec-type ngram-mod --spec-ngram-mod-n-match 24 --spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64
- GPU 격리:
  - CPU-only Docker에는 GPU device 전달 금지
  - GGML_CUDA=OFF
  - --n-gpu-layers 0
  - 두 CPU container의 VRAM allocation = 0B
  - 기존 GPU0/GPU1 서빙 프로세스와 공존 가능
- 서버 vs 측정 요청 계약:
  - 두 서버 모두 --ctx-size 131072 (128K context capacity)로 동시 resident 유지
  - 실제 measured inference는 32K class (prompt + output reserve <= 32768)로 직렬 실행
  - 워크로드는 코딩이 아닌 장문 기술 문서 요약 / 리서치 합성용 워크로드
- Safety:
  - 기본 실행으로 긴 measured inference가 자동 시작되지 않음
  - --run-32k-measured 플래그를 통한 명시적 opt-in 필수
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import bench_harness as h
import build_128k_workload as w
import gpu_telemetry as telemetry
from measurement_policy import future_config

ROOT = Path(__file__).resolve().parents[1]
C1_32K_WORKLOAD_MANIFEST = ROOT / "workloads/capacity/v1-32k.json"

LLAMA_COMMITS = {
    "b10428": "885c5bbe8e04dc78db25beb911a2715312ad7b54",
    "b10775": "67a17c17caa95742186f8b1ecadd1b5abd6d5ebb",
}

DEFAULT_IMAGE = "p520-cpu-llama:b10775"

GEMMA_EXP_ID = "EXP-P520-CPU-GEMMA4-26B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001"
ORNITH_EXP_ID = "EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001"

GEMMA_MODEL_PATH = "/srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf"
ORNITH_MODEL_PATH = "/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf"

GEMMA_PORT = 8082
ORNITH_PORT = 8083


def command(args: List[str], timeout: int = 300, check: bool = True) -> str:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
    ).stdout


def checkpoint(raw: Path, phase: str, **extra: Any) -> None:
    path = raw / "runtime/progress.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    h.save(path, state | dict(phase=phase, updated_at_utc=h.utc(), **extra))


def get_image_digest(tag: str) -> str:
    try:
        out = command(["docker", "image", "inspect", tag, "--format", "{{index .RepoDigests 0}}"], timeout=10)
        if out.strip():
            return out.strip()
    except Exception:
        pass
    try:
        out = command(["docker", "image", "inspect", tag, "--format", "{{.Id}}"], timeout=10)
        if out.strip():
            return out.strip()
    except Exception:
        pass
    return tag


def get_container_pid(container_name: str) -> Optional[int]:
    try:
        out = command(["docker", "inspect", "-f", "{{.State.Pid}}", container_name], timeout=5)
        pid = int(out.strip())
        return pid if pid > 0 else None
    except Exception:
        return None


def read_smaps_rollup(pid: int) -> Dict[str, int]:
    """Read Rss, Pss, Pss_Anon, Pss_File, Swap in kB from /proc/<pid>/smaps_rollup."""
    metrics = {"Rss": 0, "Pss": 0, "Pss_Anon": 0, "Pss_File": 0, "Swap": 0}
    path = Path(f"/proc/{pid}/smaps_rollup")
    if not path.exists():
        return metrics
    try:
        for line in path.read_text().splitlines():
            parts = line.split(":")
            if len(parts) == 2:
                k = parts[0].strip()
                if k in metrics:
                    val = parts[1].strip().split()[0]
                    metrics[k] = int(val)
    except Exception:
        pass
    return metrics


def read_vmstat() -> Dict[str, int]:
    """Read pswpin, pswpout, pgmajfault from /proc/vmstat."""
    metrics = {"pswpin": 0, "pswpout": 0, "pgmajfault": 0}
    path = Path("/proc/vmstat")
    if not path.exists():
        return metrics
    try:
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] in metrics:
                metrics[parts[0]] = int(parts[1])
    except Exception:
        pass
    return metrics


def read_system_memory() -> Dict[str, int]:
    """Read MemTotal, MemAvailable, SwapTotal, SwapFree, SwapUsed in kB from /proc/meminfo."""
    metrics = {"MemTotal": 0, "MemAvailable": 0, "SwapTotal": 0, "SwapFree": 0, "SwapUsed": 0}
    path = Path("/proc/meminfo")
    if not path.exists():
        return metrics
    try:
        for line in path.read_text().splitlines():
            parts = line.split(":")
            if len(parts) == 2:
                k = parts[0].strip()
                if k in metrics:
                    val = parts[1].strip().split()[0]
                    metrics[k] = int(val)
        metrics["SwapUsed"] = max(0, metrics["SwapTotal"] - metrics["SwapFree"])
    except Exception:
        pass
    return metrics


def capture_memory_checkpoint(
    label: str,
    gemma_pid: Optional[int] = None,
    ornith_pid: Optional[int] = None,
) -> Dict[str, Any]:
    """Capture full system and per-process memory state at a given checkpoint."""
    sys_mem = read_system_memory()
    vmstat = read_vmstat()
    gemma_smaps = read_smaps_rollup(gemma_pid) if gemma_pid else {}
    ornith_smaps = read_smaps_rollup(ornith_pid) if ornith_pid else {}

    return {
        "checkpoint": label,
        "timestamp_utc": h.utc(),
        "system_memory_kib": sys_mem,
        "system_vmstat": vmstat,
        "gemma_process": {
            "pid": gemma_pid,
            "smaps_rollup_kib": gemma_smaps,
        },
        "ornith_process": {
            "pid": ornith_pid,
            "smaps_rollup_kib": ornith_smaps,
        },
    }


def compute_memory_deltas(
    start_snap: Dict[str, Any],
    end_snap: Dict[str, Any],
    min_mem_available_kib: Optional[int] = None,
    peaks: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute exact deltas between two memory checkpoints."""
    start_sys = start_snap.get("system_memory_kib", {})
    end_sys = end_snap.get("system_memory_kib", {})
    start_vm = start_snap.get("system_vmstat", {})
    end_vm = end_snap.get("system_vmstat", {})

    mem_avail_min = min_mem_available_kib
    if mem_avail_min is None or mem_avail_min >= (1 << 60):
        start_avail = start_sys.get("MemAvailable", 0)
        end_avail = end_sys.get("MemAvailable", 0)
        mem_avail_min = min(start_avail, end_avail) if (start_avail and end_avail) else (start_avail or end_avail or 0)

    res = {
        "swap_used_start_kib": start_sys.get("SwapUsed", 0),
        "swap_used_end_kib": end_sys.get("SwapUsed", 0),
        "swap_used_delta_kib": end_sys.get("SwapUsed", 0) - start_sys.get("SwapUsed", 0),
        "pswpin_start": start_vm.get("pswpin", 0),
        "pswpin_end": end_vm.get("pswpin", 0),
        "pswpin_delta": end_vm.get("pswpin", 0) - start_vm.get("pswpin", 0),
        "pswpout_start": start_vm.get("pswpout", 0),
        "pswpout_end": end_vm.get("pswpout", 0),
        "pswpout_delta": end_vm.get("pswpout", 0) - start_vm.get("pswpout", 0),
        "pgmajfault_start": start_vm.get("pgmajfault", 0),
        "pgmajfault_end": end_vm.get("pgmajfault", 0),
        "pgmajfault_delta": end_vm.get("pgmajfault", 0) - start_vm.get("pgmajfault", 0),
        "mem_available_minimum_kib": mem_avail_min,
    }

    if peaks:
        res.update(peaks)
    else:
        res["gemma_process_peaks_kib"] = {
            "rss": max(start_snap.get("gemma_process", {}).get("smaps_rollup_kib", {}).get("Rss", 0),
                       end_snap.get("gemma_process", {}).get("smaps_rollup_kib", {}).get("Rss", 0)),
            "pss": max(start_snap.get("gemma_process", {}).get("smaps_rollup_kib", {}).get("Pss", 0),
                       end_snap.get("gemma_process", {}).get("smaps_rollup_kib", {}).get("Pss", 0)),
            "swap": max(start_snap.get("gemma_process", {}).get("smaps_rollup_kib", {}).get("Swap", 0),
                        end_snap.get("gemma_process", {}).get("smaps_rollup_kib", {}).get("Swap", 0)),
        }
        res["ornith_process_peaks_kib"] = {
            "rss": max(start_snap.get("ornith_process", {}).get("smaps_rollup_kib", {}).get("Rss", 0),
                       end_snap.get("ornith_process", {}).get("smaps_rollup_kib", {}).get("Rss", 0)),
            "pss": max(start_snap.get("ornith_process", {}).get("smaps_rollup_kib", {}).get("Pss", 0),
                       end_snap.get("ornith_process", {}).get("smaps_rollup_kib", {}).get("Pss", 0)),
            "swap": max(start_snap.get("ornith_process", {}).get("smaps_rollup_kib", {}).get("Swap", 0),
                        end_snap.get("ornith_process", {}).get("smaps_rollup_kib", {}).get("Swap", 0)),
        }
    return res


class MemoryTelemetryCollector:
    """Periodic memory, swap, and major fault telemetry thread."""

    def __init__(
        self,
        output_csv: Path,
        gemma_pid: Optional[int] = None,
        ornith_pid: Optional[int] = None,
        interval_s: float = 1.0,
    ) -> None:
        self.output_csv = output_csv
        self.gemma_pid = gemma_pid
        self.ornith_pid = ornith_pid
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.min_mem_available_kib: int = 1 << 62
        self.max_swap_used_kib: int = 0
        self.gemma_rss_peak_kib: int = 0
        self.gemma_pss_peak_kib: int = 0
        self.gemma_swap_peak_kib: int = 0
        self.ornith_rss_peak_kib: int = 0
        self.ornith_pss_peak_kib: int = 0
        self.ornith_swap_peak_kib: int = 0

    def start(self) -> None:
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        with self.output_csv.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp_utc", "mem_total_kib", "mem_available_kib", "swap_total_kib", "swap_used_kib",
                "pswpin", "pswpout", "pgmajfault",
                "gemma_rss_kib", "gemma_pss_kib", "gemma_swap_kib",
                "ornith_rss_kib", "ornith_pss_kib", "ornith_swap_kib",
            ])
            while not self._stop.is_set():
                ts = h.utc()
                sys_mem = read_system_memory()
                vmstat = read_vmstat()

                avail = sys_mem.get("MemAvailable", 0)
                swap_used = sys_mem.get("SwapUsed", 0)
                if avail > 0:
                    self.min_mem_available_kib = min(self.min_mem_available_kib, avail)
                self.max_swap_used_kib = max(self.max_swap_used_kib, swap_used)

                g_smaps = read_smaps_rollup(self.gemma_pid) if self.gemma_pid else {}
                o_smaps = read_smaps_rollup(self.ornith_pid) if self.ornith_pid else {}

                self.gemma_rss_peak_kib = max(self.gemma_rss_peak_kib, g_smaps.get("Rss", 0))
                self.gemma_pss_peak_kib = max(self.gemma_pss_peak_kib, g_smaps.get("Pss", 0))
                self.gemma_swap_peak_kib = max(self.gemma_swap_peak_kib, g_smaps.get("Swap", 0))

                self.ornith_rss_peak_kib = max(self.ornith_rss_peak_kib, o_smaps.get("Rss", 0))
                self.ornith_pss_peak_kib = max(self.ornith_pss_peak_kib, o_smaps.get("Pss", 0))
                self.ornith_swap_peak_kib = max(self.ornith_swap_peak_kib, o_smaps.get("Swap", 0))

                writer.writerow([
                    ts, sys_mem.get("MemTotal", 0), avail, sys_mem.get("SwapTotal", 0), swap_used,
                    vmstat.get("pswpin", 0), vmstat.get("pswpout", 0), vmstat.get("pgmajfault", 0),
                    g_smaps.get("Rss", 0), g_smaps.get("Pss", 0), g_smaps.get("Swap", 0),
                    o_smaps.get("Rss", 0), o_smaps.get("Pss", 0), o_smaps.get("Swap", 0),
                ])
                f.flush()
                self._stop.wait(self.interval_s)

    def compute_summary_deltas(
        self,
        start_snap: Dict[str, Any],
        end_snap: Dict[str, Any],
    ) -> Dict[str, Any]:
        peaks = {
            "gemma_process_peaks_kib": {
                "rss": self.gemma_rss_peak_kib,
                "pss": self.gemma_pss_peak_kib,
                "swap": self.gemma_swap_peak_kib,
            },
            "ornith_process_peaks_kib": {
                "rss": self.ornith_rss_peak_kib,
                "pss": self.ornith_pss_peak_kib,
                "swap": self.ornith_swap_peak_kib,
            },
        }
        return compute_memory_deltas(
            start_snap,
            end_snap,
            min_mem_available_kib=self.min_mem_available_kib if self.min_mem_available_kib < (1 << 60) else None,
            peaks=peaks,
        )



def build_cpu_images(root: Path) -> Dict[str, str]:
    digests = {}
    dockerfile = root / "docker/cpu/Dockerfile"
    if not dockerfile.exists():
        raise RuntimeError(f"Missing Dockerfile: {dockerfile}")

    for tag_name, commit_sha in LLAMA_COMMITS.items():
        image_tag = f"p520-cpu-llama:{tag_name}"
        print(f"[*] Building CPU Docker image: {image_tag} (commit {commit_sha[:8]})...")
        cmd = [
            "docker", "build",
            "-t", image_tag,
            "-f", str(dockerfile),
            "--build-arg", f"LLAMA_COMMIT={commit_sha}",
            str(root),
        ]
        proc = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to build {image_tag}")
        digest = get_image_digest(image_tag)
        digests[tag_name] = digest
        print(f"[+] Built {image_tag} -> {digest}")

    return digests


def run_preflight_ab(root: Path, digests: Dict[str, str]) -> str:
    print("\n" + "=" * 60)
    print(" [Preflight A/B] b10428 vs b10775 short prompt comparison")
    print("=" * 60)

    preflight_dir = root / "results/raw/WBS6-PREFLIGHT-AB"
    preflight_dir.mkdir(parents=True, exist_ok=True)
    preflight_file = preflight_dir / "preflight_ab_result.json"
    if preflight_file.exists():
        raise RuntimeError(
            f"Immutable preflight raw evidence already exists at {preflight_file}. "
            "Refusing to overwrite existing evidence."
        )

    results = {}
    test_port = 8089
    prompt_text = "Summarize the architectural differences between dense Transformers and Mixture-of-Experts (MoE) in 5 bullet points. " * 30

    for tag_name in ["b10428", "b10775"]:
        image_tag = f"p520-cpu-llama:{tag_name}"
        container_name = f"preflight-cpu-{tag_name}"

        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

        cmd = [
            "docker", "run", "-d", "--rm",
            "--name", container_name,
            "--cpuset-cpus", "1,2,3,4",
            "-p", f"{test_port}:{test_port}",
            "-v", "/srv/models:/srv/models:ro",
            image_tag,
            "--host", "0.0.0.0",
            "--port", str(test_port),
            "-m", ORNITH_MODEL_PATH,
            "--n-gpu-layers", "0",
            "--ctx-size", "8192",
            "--parallel", "1",
            "-ctk", "q8_0",
            "-ctv", "q8_0",
            "-fa", "auto",
            "-t", "4",
            "-tb", "4",
            "-b", "1024",
            "-ub", "256",
            "--cpu-strict", "1",
            "--poll", "50",
            "--load-mode", "mmap",
            "--cache-ram", "0",
            "--no-cache-prompt",
            "--no-context-shift",
            "--threads-http", "1",
            "--no-webui",
        ]

        print(f"[*] Starting container {container_name} on port {test_port}...")
        subprocess.run(cmd, check=True)

        adapter = h.HTTPAdapter(f"http://127.0.0.1:{test_port}", "llama.cpp", timeout_s=180)
        healthy = False
        start_wait = time.time()
        while time.time() - start_wait < 180:
            if adapter.health().get("healthy"):
                healthy = True
                break
            time.sleep(2)

        if not healthy:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            raise RuntimeError(f"Container {container_name} failed to become healthy within 180s")

        print(f"[+] Container {container_name} is healthy. Sending preflight request...")
        req_body = {
            "model": "Ornith-1.5-35B-Q4_K_M.gguf",
            "messages": [{"role": "user", "content": prompt_text}],
            "max_tokens": 128,
            "temperature": 0.0,
        }

        t0 = time.time()
        res = adapter.call("/v1/chat/completions", body=req_body)
        duration_s = time.time() - t0

        timings = res.get("timings", {})
        usage = res.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", timings.get("prompt_n", 0))
        completion_tokens = usage.get("completion_tokens", timings.get("predicted_n", 0))

        prompt_tps = timings.get("prompt_per_second")
        if not prompt_tps and prompt_tokens and timings.get("prompt_ms"):
            prompt_tps = prompt_tokens / (timings["prompt_ms"] / 1000.0)

        decode_tps = timings.get("predicted_per_second")
        if not decode_tps and completion_tokens and timings.get("predicted_ms"):
            decode_tps = completion_tokens / (timings["predicted_ms"] / 1000.0)

        ttft_s = (timings.get("prompt_ms", 0) / 1000.0) if timings.get("prompt_ms") else duration_s

        res_data = {
            "tag": tag_name,
            "image": image_tag,
            "digest": digests.get(tag_name, ""),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_s": duration_s,
            "ttft_s": ttft_s,
            "prompt_tps": prompt_tps,
            "decode_tps": decode_tps,
            "timings": timings,
        }
        results[tag_name] = res_data
        print(f"[{tag_name}] prompt_tokens={prompt_tokens}, decode_tokens={completion_tokens}, TTFT={ttft_s:.2f}s, prompt_tps={prompt_tps}, decode_tps={decode_tps}")

        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        time.sleep(2)

    preflight_file = preflight_dir / "preflight_ab_result.json"
    h.save(preflight_file, results)
    print(f"[+] Saved preflight results to {preflight_file}")

    b10428_ptps = results["b10428"].get("prompt_tps") or 1.0
    b10775_ptps = results["b10775"].get("prompt_tps") or 1.0

    print(f"\n[Comparison] b10428 prompt TPS: {b10428_ptps:.2f} | b10775 prompt TPS: {b10775_ptps:.2f}")

    if b10775_ptps >= b10428_ptps * 0.85:
        selected = "b10775"
        print("[+] No material CPU regression observed for b10775 relative to b10428 in pinned preflight -> Selecting b10775 for WBS 6.")
    else:
        selected = "b10428"
        print("[-] Material CPU regression observed for b10775 relative to b10428 -> Selecting b10428 for WBS 6.")

    return f"p520-cpu-llama:{selected}"


def start_dual_resident_servers(selected_image: str) -> Tuple[Optional[int], Optional[int]]:
    """Start Gemma and Ornith CPU servers simultaneously with 128K context capacity."""
    print("\n" + "=" * 60)
    print(" [Dual-Resident Startup] Launching Gemma & Ornith 128K-Context Servers")
    print("=" * 60)

    subprocess.run(["docker", "rm", "-f", "p520-cpu-gemma", "p520-cpu-ornith"], capture_output=True)

    common_args = [
        "--cpuset-cpus", "1,2,3,4",
        "-v", "/srv/models:/srv/models:ro",
        selected_image,
        "--n-gpu-layers", "0",
        "--ctx-size", "131072",
        "--parallel", "1",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-fa", "auto",
        "-t", "4",
        "-tb", "4",
        "-b", "1024",
        "-ub", "256",
        "--cpu-strict", "1",
        "--poll", "50",
        "--load-mode", "mmap",
        "--cache-ram", "0",
        "--no-cache-prompt",
        "--no-context-shift",
        "--threads-http", "1",
        "--no-webui",
        "--spec-type", "ngram-mod",
        "--spec-ngram-mod-n-match", "24",
        "--spec-ngram-mod-n-min", "48",
        "--spec-ngram-mod-n-max", "64",
    ]

    gemma_cmd = [
        "docker", "run", "-d",
        "--name", "p520-cpu-gemma",
        "-p", f"{GEMMA_PORT}:{GEMMA_PORT}",
    ] + common_args + [
        "--host", "0.0.0.0",
        "--port", str(GEMMA_PORT),
        "-m", GEMMA_MODEL_PATH,
    ]

    print("[*] Launching p520-cpu-gemma (128K context capacity) on port 8082...")
    subprocess.run(gemma_cmd, check=True)

    ornith_cmd = [
        "docker", "run", "-d",
        "--name", "p520-cpu-ornith",
        "-p", f"{ORNITH_PORT}:{ORNITH_PORT}",
    ] + common_args + [
        "--host", "0.0.0.0",
        "--port", str(ORNITH_PORT),
        "-m", ORNITH_MODEL_PATH,
    ]

    print("[*] Launching p520-cpu-ornith (128K context capacity) on port 8083...")
    subprocess.run(ornith_cmd, check=True)

    gemma_pid = get_container_pid("p520-cpu-gemma")
    ornith_pid = get_container_pid("p520-cpu-ornith")
    print(f"[+] Container PIDs: Gemma host PID={gemma_pid}, Ornith host PID={ornith_pid}")
    return gemma_pid, ornith_pid


def wait_for_dual_resident_health() -> None:
    print("[*] Waiting for both CPU servers to become healthy...")
    gemma_adapter = h.HTTPAdapter(f"http://127.0.0.1:{GEMMA_PORT}", "llama.cpp", timeout_s=180)
    ornith_adapter = h.HTTPAdapter(f"http://127.0.0.1:{ORNITH_PORT}", "llama.cpp", timeout_s=180)

    gemma_healthy = False
    ornith_healthy = False
    start_wait = time.time()

    while time.time() - start_wait < 300:
        if not gemma_healthy:
            gemma_healthy = gemma_adapter.health().get("healthy", False)
        if not ornith_healthy:
            ornith_healthy = ornith_adapter.health().get("healthy", False)

        if gemma_healthy and ornith_healthy:
            print("[+] Both CPU servers are HEALTHY and DUAL-RESIDENT!")
            return

        time.sleep(3)

    raise RuntimeError(f"Dual-resident health timeout: gemma={gemma_healthy}, ornith={ornith_healthy}")


def record_startup_gate(
    gate_dir: Path,
    selected_image: str,
    gemma_pid: Optional[int] = None,
    ornith_pid: Optional[int] = None,
    snap_a: Optional[Dict[str, Any]] = None,
    snap_b: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    gate_dir.mkdir(parents=True, exist_ok=True)
    target_gate_file = gate_dir / "startup_gate.json"
    if target_gate_file.exists():
        raise RuntimeError(
            f"Immutable startup gate raw evidence already exists at {target_gate_file}. "
            "Refusing to overwrite existing evidence."
        )

    if snap_a:
        h.save(gate_dir / "memory-baseline-before-startup.json", snap_a)

    try:
        gpu_snapshot = telemetry.read_gpus(timeout_s=5.0)
    except Exception as e:
        gpu_snapshot = {"error": str(e)}
    gpu_processes = command(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv"], timeout=10, check=False)

    docker_stats = command(["docker", "stats", "--no-stream", "--format", "json", "p520-cpu-gemma", "p520-cpu-ornith"], timeout=10, check=False)

    if not snap_b:
        snap_b = capture_memory_checkpoint("checkpoint_b_startup_healthy", gemma_pid, ornith_pid)

    startup_deltas = compute_memory_deltas(snap_a, snap_b) if snap_a else {}
    if startup_deltas:
        h.save(gate_dir / "memory-startup-deltas.json", startup_deltas)

    gate_data = {
        "timestamp_utc": h.utc(),
        "selected_image": selected_image,
        "image_digest": get_image_digest(selected_image),
        "topology": "logical CPU IDs 1, 2, 3, 4, each mapped to distinct physical cores (CORE 1, 2, 3, 4)",
        "server_context_capacity": 131072,
        "gemma_port": GEMMA_PORT,
        "ornith_port": ORNITH_PORT,
        "gemma_host_pid": gemma_pid,
        "ornith_host_pid": ornith_pid,
        "gpu_telemetry_snapshot": gpu_snapshot,
        "gpu_compute_apps": gpu_processes,
        "docker_stats": docker_stats,
        "memory_checkpoint": snap_b,
        "memory_startup_deltas": startup_deltas,
        "notes": (
            "PASS_STARTUP_GATE verifies dual server 128K context startup, health, and CPU/GPU isolation. "
            "Due to mmap loading, startup snapshot MemAvailable does not guarantee physical RAM headroom once working sets are fault-in. "
            "Actual memory pressure and stability are measured during 32K request execution."
        ),
        "gate_verdict": "PASS_STARTUP_GATE",
    }

    h.save(target_gate_file, gate_data)
    print(f"[+] Recorded WBS 6.5 startup gate evidence to {target_gate_file}")
    return gate_data


def run_measured_experiment_32k(
    root: Path,
    exp_id: str,
    model_name: str,
    model_key: str,
    model_path: str,
    port: int,
    selected_image: str,
    peer_name: str,
    peer_port: int,
    gemma_pid: Optional[int],
    ornith_pid: Optional[int],
    snap_a: Dict[str, Any],
    snap_b: Dict[str, Any],
    pre_snap_label: str,
    post_snap_label: str,
) -> Tuple[str, Dict[str, Any]]:
    """Execute exactly one serial 32K measured request with hardened memory delta telemetry."""
    print("\n" + "=" * 60)
    print(f" [Measured 32K Run] {exp_id}")
    print(f" Model: {model_name} on port {port} (Server ctx=128K, Request class=32K, Peer {peer_name} resident)")
    print("=" * 60)

    raw = root / "results/raw" / exp_id
    if raw.exists():
        raise RuntimeError(
            f"Immutable raw experiment evidence directory already exists at {raw}. "
            "Refusing to overwrite existing experiment evidence."
        )
    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / "runtime"
    runtime.mkdir()

    # Persist Checkpoints A and B (Startup Phase) in experiment evidence
    h.save(runtime / "checkpoint_a_baseline_before_startup.json", snap_a)
    h.save(raw / "memory-baseline-before-startup.json", snap_a)
    h.save(runtime / "checkpoint_b_startup_healthy.json", snap_b)
    startup_deltas = compute_memory_deltas(snap_a, snap_b)
    h.save(runtime / "memory-startup-deltas.json", startup_deltas)

    endpoint = f"http://127.0.0.1:{port}"
    peer_endpoint = f"http://127.0.0.1:{peer_port}"

    adapter = h.HTTPAdapter(endpoint, "llama.cpp", timeout_s=7200)
    peer_adapter = h.HTTPAdapter(peer_endpoint, "llama.cpp", timeout_s=180)

    if not peer_adapter.health().get("healthy"):
        raise RuntimeError(f"Peer {peer_name} is unhealthy before measurement!")

    planned = {
        "schema_version": 1,
        "experiment_id": exp_id,
        "model": model_name,
        "model_key": model_key,
        "runtime": "llama.cpp",
        "runtime_flavor": "cpu-only",
        "runtime_image": selected_image,
        "runtime_image_digest": get_image_digest(selected_image),
        "backend_variant": "CPU-ONLY-W2135-NATIVE",
        "topology": "cpu-standalone-4core",
        "topology_detail": "logical CPU IDs 1, 2, 3, 4, each mapped to distinct physical cores (CORE 1, 2, 3, 4)",
        "concurrency": 1,
        "server_ctx_size": 131072,
        "measured_request_class": "32K",
        "context_tokens": 32768,
        "weight_quant": "UD-Q6_K_XL" if "GEMMA" in exp_id else "Q4_K_M",
        "kv_cache": "Q8_0",
        "speculative": "ngram-mod",
        "ngram": "ngram-mod-24-48-64",
        "endpoint": endpoint,
        "peer_resident_model": peer_name,
        "peer_resident_endpoint": peer_endpoint,
        "workload_manifest": str(C1_32K_WORKLOAD_MANIFEST),
        "notes": f"WBS 6 CPU+RAM dual-resident 128K server context with 32K serial measured request; peer {peer_name} idle resident",
    }

    config = future_config(planned)
    h.save(runtime / "planned-config.json", config)
    checkpoint(raw, "prepared", step="config_written")

    stop_gpu_telemetry = threading.Event()

    def _gpu_telemetry_loop() -> None:
        csv_file = runtime / "gpu-telemetry.csv"
        with csv_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_utc", "gpu0_used_mib", "gpu1_used_mib", "gpu0_util", "gpu1_util"])
            while not stop_gpu_telemetry.is_set():
                try:
                    gpus = telemetry.read_gpus(timeout_s=2.0)
                    g0 = gpus[0].get("metrics", {}) if len(gpus) > 0 else {}
                    g1 = gpus[1].get("metrics", {}) if len(gpus) > 1 else {}
                    writer.writerow([
                        h.utc(),
                        g0.get("memory_used_mib", 0.0),
                        g1.get("memory_used_mib", 0.0),
                        g0.get("utilization_pct", 0.0),
                        g1.get("utilization_pct", 0.0),
                    ])
                    f.flush()
                except Exception:
                    pass
                stop_gpu_telemetry.wait(1.0)

    gpu_telemetry_thread = threading.Thread(target=_gpu_telemetry_loop, daemon=True)
    gpu_telemetry_thread.start()

    mem_collector = MemoryTelemetryCollector(
        output_csv=runtime / "memory-telemetry.csv",
        gemma_pid=gemma_pid,
        ornith_pid=ornith_pid,
        interval_s=1.0,
    )
    mem_collector.start()

    pre_snap = capture_memory_checkpoint(pre_snap_label, gemma_pid, ornith_pid)
    h.save(runtime / f"{pre_snap_label}.json", pre_snap)

    post_snap = None
    memory_deltas = None
    run_batch_err = None
    verdict = None

    try:
        checkpoint(raw, "running", step="materializing_32k_workload")
        manifest = w.load_manifest(C1_32K_WORKLOAD_MANIFEST)
        workload = w.build(manifest, adapter, model_name)

        checkpoint(raw, "running", step="measured_request", workload_sha256=h.sha(h.canon(workload)))
        print("[*] Dispatching 32K measured request (timeout=7200s)...")
        verdict = h.run_batch(raw, config, workload, adapter)

        checkpoint(raw, "results_saved", step="measurement_complete", verdict=verdict)
        print(f"[+] Measurement complete with verdict: {verdict}")

    except Exception as exc:
        run_batch_err = exc
        verdict = f"FAIL_ERROR_{type(exc).__name__}"
        checkpoint(raw, "failed", error=str(exc), verdict=verdict)
        print(f"[!] Error during measured inference batch: {exc}")

    finally:
        try:
            post_snap = capture_memory_checkpoint(post_snap_label, gemma_pid, ornith_pid)
            h.save(runtime / f"{post_snap_label}.json", post_snap)

            memory_deltas = mem_collector.compute_summary_deltas(pre_snap, post_snap)
            h.save(raw / "memory-deltas.json", memory_deltas)
            print(f"[+] Recorded memory deltas: Swap delta={memory_deltas['swap_used_delta_kib']} kB, pswpin delta={memory_deltas['pswpin_delta']}, pswpout delta={memory_deltas['pswpout_delta']}, pgmajfault delta={memory_deltas['pgmajfault_delta']}")
        except Exception as snap_err:
            print(f"[!] Error recording post memory snapshot/deltas: {snap_err}")

        mem_collector.stop()
        stop_gpu_telemetry.set()
        gpu_telemetry_thread.join(timeout=10)

        # Summarize GPU VRAM peak
        gpu_peak = {"gpu0_max_mib": 0.0, "gpu1_max_mib": 0.0}
        csv_file = runtime / "gpu-telemetry.csv"
        if csv_file.exists():
            try:
                with csv_file.open() as f:
                    r = csv.DictReader(f)
                    for row in r:
                        gpu_peak["gpu0_max_mib"] = max(gpu_peak["gpu0_max_mib"], float(row.get("gpu0_used_mib", 0.0)))
                        gpu_peak["gpu1_max_mib"] = max(gpu_peak["gpu1_max_mib"], float(row.get("gpu1_used_mib", 0.0)))
            except Exception:
                pass
        h.save(raw / "gpu-peak.json", gpu_peak)

    my_health = adapter.health()
    peer_health = peer_adapter.health()
    post_health_data = {
        "active_model_health": my_health,
        "peer_model_health": peer_health,
        "both_healthy": bool(my_health.get("healthy") and peer_health.get("healthy")),
    }
    h.save(raw / "dual_resident_post_health.json", post_health_data)

    if not post_health_data["both_healthy"]:
        print(f"[!] Warning: One or both servers unhealthy post-inference: {post_health_data}")

    if run_batch_err is not None:
        raise run_batch_err

    return verdict, memory_deltas


def cleanup_containers() -> None:
    print("[*] Cleaning up dual-resident containers...")
    subprocess.run(["docker", "rm", "-f", "p520-cpu-gemma", "p520-cpu-ornith"], capture_output=True)
    print("[+] Containers cleaned up.")


def run(args: argparse.Namespace) -> None:
    if socket.gethostname().split(".")[0] != "p520-llm":
        raise RuntimeError("WBS 6 runner requires p520-llm host")

    if not (args.run_32k_measured or args.gate_only or args.preflight_only):
        print("=" * 60)
        print(" [-] Safety Stop: No explicit execution action specified.")
        print("=" * 60)
        print("  Available actions:")
        print("    --preflight-only    : Run only preflight A/B comparison")
        print("    --gate-only         : Run WBS 6.5 dual-resident startup gate only")
        print("    --run-32k-measured  : Explicit opt-in required to execute serial 32K measured inference")
        print()
        print("  Runner exits without starting long-running measured inference.")
        return

    lock_path = ROOT / "results/experiment.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run_locked(args)


def run_locked(args: argparse.Namespace) -> None:
    print("=" * 60)
    print(" [WBS 6] CPU+RAM Dual-Resident 128K Server + 32K Measured Runner")
    print("=" * 60)

    selected_image = args.selected_image or DEFAULT_IMAGE

    if args.preflight_only:
        digests = build_cpu_images(ROOT)
        selected_image = run_preflight_ab(ROOT, digests)
        print(f"\n[+] Preflight completed. Selected image: {selected_image}")
        return

    # Checkpoint A: baseline_before_startup
    snap_a = capture_memory_checkpoint("checkpoint_a_baseline_before_startup")
    print(f"[*] [Checkpoint A] Baseline host memory before startup: MemAvailable={snap_a['system_memory_kib'].get('MemAvailable')} kB, SwapUsed={snap_a['system_memory_kib'].get('SwapUsed')} kB")

    gemma_pid, ornith_pid = start_dual_resident_servers(selected_image)

    try:
        wait_for_dual_resident_health()

        # Checkpoint B: startup_healthy
        snap_b = capture_memory_checkpoint("checkpoint_b_startup_healthy", gemma_pid, ornith_pid)
        print(f"[*] [Checkpoint B] Dual servers healthy: MemAvailable={snap_b['system_memory_kib'].get('MemAvailable')} kB, SwapUsed={snap_b['system_memory_kib'].get('SwapUsed')} kB")

        if args.gate_only:
            gate_dir = ROOT / "results/raw/WBS6-STARTUP-GATE"
            record_startup_gate(gate_dir, selected_image, gemma_pid, ornith_pid, snap_a=snap_a, snap_b=snap_b)
            print("\n[+] Dual-resident startup gate passed and recorded. Stopping per --gate-only.")
            return

        if not args.run_32k_measured:
            print("\n[+] Startup gate complete. Measured 32K runs require --run-32k-measured. Exiting safely.")
            return

        print("\n" + "=" * 60)
        print(" [WBS 6] Proceeding to 32K Serial Measured Runs (--run-32k-measured confirmed)")
        print("=" * 60)

        # Checkpoints C & D in Gemma run
        gemma_verdict, gemma_mem = run_measured_experiment_32k(
            root=ROOT,
            exp_id=GEMMA_EXP_ID,
            model_name="gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf",
            model_key="gemma4-26b-a4b",
            model_path=GEMMA_MODEL_PATH,
            port=GEMMA_PORT,
            selected_image=selected_image,
            peer_name="Ornith-1.5-35B-Q4_K_M.gguf",
            peer_port=ORNITH_PORT,
            gemma_pid=gemma_pid,
            ornith_pid=ornith_pid,
            snap_a=snap_a,
            snap_b=snap_b,
            pre_snap_label="checkpoint_c_gemma_32k_pre",
            post_snap_label="checkpoint_d_gemma_32k_post",
        )
        print(f"[+] Gemma 32K completed: {gemma_verdict}")

        # Intermediate health check between requests
        gemma_adapter = h.HTTPAdapter(f"http://127.0.0.1:{GEMMA_PORT}", "llama.cpp", timeout_s=60)
        ornith_adapter = h.HTTPAdapter(f"http://127.0.0.1:{ORNITH_PORT}", "llama.cpp", timeout_s=60)
        if not gemma_adapter.health().get("healthy") or not ornith_adapter.health().get("healthy"):
            raise RuntimeError("Server health check failed before Ornith request!")

        # Checkpoints E & F in Ornith run
        ornith_verdict, ornith_mem = run_measured_experiment_32k(
            root=ROOT,
            exp_id=ORNITH_EXP_ID,
            model_name="Ornith-1.5-35B-Q4_K_M.gguf",
            model_key="ornith-1.5-35b-a3b",
            model_path=ORNITH_MODEL_PATH,
            port=ORNITH_PORT,
            selected_image=selected_image,
            peer_name="gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf",
            peer_port=GEMMA_PORT,
            gemma_pid=gemma_pid,
            ornith_pid=ornith_pid,
            snap_a=snap_a,
            snap_b=snap_b,
            pre_snap_label="checkpoint_e_ornith_32k_pre",
            post_snap_label="checkpoint_f_ornith_32k_post",
        )
        print(f"[+] Ornith 32K completed: {ornith_verdict}")

        # Checkpoint G: final_post_health
        snap_g = capture_memory_checkpoint("checkpoint_g_final_post_health", gemma_pid, ornith_pid)
        print(f"[*] [Checkpoint G] Final post-health memory: MemAvailable={snap_g['system_memory_kib'].get('MemAvailable')} kB, SwapUsed={snap_g['system_memory_kib'].get('SwapUsed')} kB")

        for exp_id in (GEMMA_EXP_ID, ORNITH_EXP_ID):
            exp_runtime = ROOT / "results/raw" / exp_id / "runtime"
            if exp_runtime.exists():
                h.save(exp_runtime / "checkpoint_g_final_post_health.json", snap_g)
                session_deltas = compute_memory_deltas(snap_a, snap_g)
                h.save(exp_runtime / "memory-session-deltas.json", session_deltas)

        print("\n" + "=" * 60)
        print(" [WBS 6 All 32K Measured Items Finished]")
        print(f" Gemma Verdict: {gemma_verdict}")
        print(f" Ornith Verdict: {ornith_verdict}")
        print("=" * 60)

    finally:
        cleanup_containers()


def main() -> None:
    parser = argparse.ArgumentParser(description="WBS 6 CPU+RAM Dual-Resident Runner (128K Server + 32K Request)")
    parser.add_argument("--preflight-only", action="store_true", help="Run only the preflight A/B comparison")
    parser.add_argument("--gate-only", action="store_true", help="Run up to WBS 6.5 dual-resident startup gate only")
    parser.add_argument("--run-32k-measured", action="store_true", help="Explicit opt-in required to execute serial 32K measured inference")
    parser.add_argument("--selected-image", type=str, default="", help="Skip preflight and use specified image tag")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
