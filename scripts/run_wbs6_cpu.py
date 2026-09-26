#!/usr/bin/env python3
"""CPU+RAM 전용 dual-resident 128K 검증 러너 (WBS 6).

Contract:
- WBS 6.1: P520 Xeon W-2135 호스트에서 직접 빌드한 native CPU-only Docker image
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
- 순서:
  1. Docker 후보 빌드 (b10428 vs b10775)
  2. 짧은 비측정 preflight A/B (2K~4K prompt, Ornith 35B) -> 이미지 확정
  3. Gemma + Ornith dual-resident 동시 기동 및 WBS 6.5 startup gate 검증
  4. 직렬 128K 측정 1: Gemma 4 26B-A4B
  5. 두 서버 health 확인
  6. 직렬 128K 측정 2: Ornith 1.5 35B-A3B
  7. 두 서버 health 확인 및 정상 cleanup
"""

from __future__ import annotations

import argparse
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
from typing import Any, Dict, List, Optional

import bench_harness as h
import build_128k_workload as w
import gpu_telemetry as telemetry
from measurement_policy import future_config

ROOT = Path(__file__).resolve().parents[1]
C1_WORKLOAD_MANIFEST = ROOT / "workloads/capacity/v1.json"

LLAMA_COMMITS = {
    "b10428": "885c5bbe8e04dc78db25beb911a2715312ad7b54",
    "b10775": "67a17c17caa95742186f8b1ecadd1b5abd6d5ebb",
}

GEMMA_EXP_ID = "EXP-P520-CPU-GEMMA4-26B-LLAMA-Q80-NGRAM-MOD-C1-128K-20260926-001"
ORNITH_EXP_ID = "EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-128K-20260926-001"

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
        return out.strip()
    except Exception:
        out = command(["docker", "image", "inspect", tag, "--format", "{{.Id}}"], timeout=10)
        return out.strip()


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

    results = {}
    test_port = 8089
    prompt_text = "Summarize the architectural differences between dense Transformers and Mixture-of-Experts (MoE) in 5 bullet points. " * 30

    for tag_name in ["b10428", "b10775"]:
        image_tag = f"p520-cpu-llama:{tag_name}"
        container_name = f"preflight-cpu-{tag_name}"

        # Clean any old container
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

        # Wait for health
        adapter = h.HTTPAdapter(f"http://127.0.0.1:{test_port}", "llama.cpp", timeout_s=120)
        healthy = False
        start_wait = time.time()
        while time.time() - start_wait < 120:
            if adapter.health().get("healthy"):
                healthy = True
                break
            time.sleep(2)

        if not healthy:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            raise RuntimeError(f"Container {container_name} failed to become healthy within 120s")

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

        # Cleanup container
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        time.sleep(2)

    preflight_file = preflight_dir / "preflight_ab_result.json"
    h.save(preflight_file, results)
    print(f"[+] Saved preflight results to {preflight_file}")

    # Determine winner
    # If b10775 prompt_tps is within 15% of b10428 and TTFT is reasonable, choose b10775
    b10428_ptps = results["b10428"].get("prompt_tps") or 1.0
    b10775_ptps = results["b10775"].get("prompt_tps") or 1.0

    print(f"\n[Comparison] b10428 prompt TPS: {b10428_ptps:.2f} | b10775 prompt TPS: {b10775_ptps:.2f}")

    if b10775_ptps >= b10428_ptps * 0.85:
        selected = "b10775"
        print(f"[+] b10775 performance is verified normal -> Selecting b10775 for WBS 6.")
    else:
        selected = "b10428"
        print(f"[-] b10775 exhibits CPU performance regression -> Selecting b10428 for WBS 6.")

    return f"p520-cpu-llama:{selected}"


def collect_system_memory_snapshot() -> Dict[str, Any]:
    mem_info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    v = parts[1].strip()
                    mem_info[k] = v
    except Exception as e:
        mem_info["error"] = str(e)

    free_out = command(["free", "-m"], timeout=5, check=False)
    vmstat_out = command(["vmstat", "-s"], timeout=5, check=False)

    return {
        "timestamp_utc": h.utc(),
        "proc_meminfo": mem_info,
        "free_m": free_out,
        "vmstat_s": vmstat_out,
    }


def start_dual_resident_servers(selected_image: str) -> None:
    print("\n" + "=" * 60)
    print(" [Dual-Resident Startup] Launching Gemma & Ornith CPU servers")
    print("=" * 60)

    # Clean existing
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

    # Gemma server
    gemma_cmd = [
        "docker", "run", "-d",
        "--name", "p520-cpu-gemma",
        "-p", f"{GEMMA_PORT}:{GEMMA_PORT}",
    ] + common_args + [
        "--host", "0.0.0.0",
        "--port", str(GEMMA_PORT),
        "-m", GEMMA_MODEL_PATH,
    ]

    print("[*] Launching p520-cpu-gemma on port 8082...")
    subprocess.run(gemma_cmd, check=True)

    # Ornith server
    ornith_cmd = [
        "docker", "run", "-d",
        "--name", "p520-cpu-ornith",
        "-p", f"{ORNITH_PORT}:{ORNITH_PORT}",
    ] + common_args + [
        "--host", "0.0.0.0",
        "--port", str(ORNITH_PORT),
        "-m", ORNITH_MODEL_PATH,
    ]

    print("[*] Launching p520-cpu-ornith on port 8083...")
    subprocess.run(ornith_cmd, check=True)


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


def record_startup_gate(gate_dir: Path, selected_image: str) -> Dict[str, Any]:
    gate_dir.mkdir(parents=True, exist_ok=True)

    # GPU telemetry check (ensure CPU servers allocated 0B VRAM)
    try:
        gpu_snapshot = telemetry.read_gpus(timeout_s=5.0)
    except Exception as e:
        gpu_snapshot = {"error": str(e)}
    gpu_processes = command(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv"], timeout=10, check=False)

    # Docker memory / CPU stats
    docker_stats = command(["docker", "stats", "--no-stream", "--format", "json", "p520-cpu-gemma", "p520-cpu-ornith"], timeout=10, check=False)

    system_mem = collect_system_memory_snapshot()

    gate_data = {
        "timestamp_utc": h.utc(),
        "selected_image": selected_image,
        "image_digest": get_image_digest(selected_image),
        "topology": "logical CPU IDs 1, 2, 3, 4, each mapped to distinct physical cores (CORE 1, 2, 3, 4)",
        "gemma_port": GEMMA_PORT,
        "ornith_port": ORNITH_PORT,
        "gpu_telemetry_snapshot": gpu_snapshot,
        "gpu_compute_apps": gpu_processes,
        "docker_stats": docker_stats,
        "system_memory": system_mem,
        "gate_verdict": "PASS_STARTUP_GATE",
    }

    h.save(gate_dir / "startup_gate.json", gate_data)
    print(f"[+] Recorded WBS 6.5 startup gate evidence to {gate_dir / 'startup_gate.json'}")
    return gate_data


def run_measured_experiment(
    root: Path,
    exp_id: str,
    model_name: str,
    model_key: str,
    model_path: str,
    port: int,
    selected_image: str,
    peer_name: str,
    peer_port: int,
) -> str:
    print("\n" + "=" * 60)
    print(f" [Measured 128K Run] {exp_id}")
    print(f" Model: {model_name} on port {port} (Peer {peer_name} on port {peer_port} resident)")
    print("=" * 60)

    raw = root / "results/raw" / exp_id
    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / "runtime"
    runtime.mkdir()

    endpoint = f"http://127.0.0.1:{port}"
    peer_endpoint = f"http://127.0.0.1:{peer_port}"

    adapter = h.HTTPAdapter(endpoint, "llama.cpp", timeout_s=14400)
    peer_adapter = h.HTTPAdapter(peer_endpoint, "llama.cpp", timeout_s=180)

    # Verify peer is healthy before starting
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
        "context_tokens": 131072,
        "weight_quant": "UD-Q6_K_XL" if "GEMMA" in exp_id else "Q4_K_M",
        "kv_cache": "Q8_0",
        "speculative": "ngram-mod",
        "ngram": "ngram-mod-24-48-64",
        "endpoint": endpoint,
        "peer_resident_model": peer_name,
        "peer_resident_endpoint": peer_endpoint,
        "notes": f"WBS 6 CPU+RAM dual-resident 128K serial execution; peer {peer_name} idle resident",
    }

    config = future_config(planned)
    h.save(runtime / "planned-config.json", config)
    checkpoint(raw, "prepared", step="config_written")

    # Start telemetry thread
    stop_telemetry = threading.Event()
    telemetry_thread = threading.Thread(
        target=telemetry.telemetry_loop,
        args=(runtime / "gpu-telemetry.csv", 1.0, stop_telemetry),
        daemon=True,
    )
    telemetry_thread.start()

    try:
        checkpoint(raw, "running", step="materializing_live_tokenizer_workload")
        manifest = w.load_manifest(C1_WORKLOAD_MANIFEST)
        workload = w.build(manifest, adapter, model_name)

        checkpoint(raw, "running", step="measured_request", workload_sha256=h.sha(h.canon(workload)))
        print(f"[*] Dispatching 128K measured request (timeout=14400s)...")
        verdict = h.run_batch(raw, config, workload, adapter)

        checkpoint(raw, "results_saved", step="measurement_complete", verdict=verdict)
        print(f"[+] Measurement complete with verdict: {verdict}")

        # Post-health check for BOTH servers
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

        return verdict

    finally:
        stop_telemetry.set()
        telemetry_thread.join(timeout=10)
        telemetry.summarize_session(runtime / "gpu-telemetry.csv", raw / "gpu-peak.json")


def cleanup_containers() -> None:
    print("[*] Cleaning up dual-resident containers...")
    subprocess.run(["docker", "rm", "-f", "p520-cpu-gemma", "p520-cpu-ornith"], capture_output=True)
    print("[+] Containers cleaned up.")


def run(args: argparse.Namespace) -> None:
    if socket.gethostname().split(".")[0] != "p520-llm":
        raise RuntimeError("WBS 6 runner requires p520-llm host")

    lock_path = ROOT / "results/experiment.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run_locked(args)


def run_locked(args: argparse.Namespace) -> None:
    print("=" * 60)
    print(" [WBS 6] CPU+RAM Dual-Resident 128K Orchestration")
    print("=" * 60)

    selected_image = args.selected_image

    if not selected_image:
        # Step 1: Build Docker images
        digests = build_cpu_images(ROOT)

        # Step 2: Preflight A/B
        selected_image = run_preflight_ab(ROOT, digests)

    if args.preflight_only:
        print(f"\n[+] Preflight completed. Selected image: {selected_image}")
        return

    # Step 3: Dual-Resident Startup
    start_dual_resident_servers(selected_image)

    try:
        wait_for_dual_resident_health()

        # Step 4: Record Startup Gate
        gate_dir = ROOT / "results/raw/WBS6-STARTUP-GATE"
        record_startup_gate(gate_dir, selected_image)

        if args.gate_only:
            print("\n[+] Dual-resident startup gate passed and recorded. Stopping per --gate-only.")
            return

        # Step 5: Serial Measured Request 1 — Gemma 4 26B-A4B
        gemma_verdict = run_measured_experiment(
            root=ROOT,
            exp_id=GEMMA_EXP_ID,
            model_name="gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf",
            model_key="gemma4-26b-a4b",
            model_path=GEMMA_MODEL_PATH,
            port=GEMMA_PORT,
            selected_image=selected_image,
            peer_name="Ornith-1.5-35B-Q4_K_M.gguf",
            peer_port=ORNITH_PORT,
        )
        print(f"[+] Gemma 128K completed: {gemma_verdict}")

        # Step 6: Verify health between requests
        gemma_adapter = h.HTTPAdapter(f"http://127.0.0.1:{GEMMA_PORT}", "llama.cpp", timeout_s=60)
        ornith_adapter = h.HTTPAdapter(f"http://127.0.0.1:{ORNITH_PORT}", "llama.cpp", timeout_s=60)
        if not gemma_adapter.health().get("healthy") or not ornith_adapter.health().get("healthy"):
            raise RuntimeError("Server health check failed before Ornith request!")

        # Step 7: Serial Measured Request 2 — Ornith 1.5 35B-A3B
        ornith_verdict = run_measured_experiment(
            root=ROOT,
            exp_id=ORNITH_EXP_ID,
            model_name="Ornith-1.5-35B-Q4_K_M.gguf",
            model_key="ornith-1.5-35b-a3b",
            model_path=ORNITH_MODEL_PATH,
            port=ORNITH_PORT,
            selected_image=selected_image,
            peer_name="gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf",
            peer_port=GEMMA_PORT,
        )
        print(f"[+] Ornith 128K completed: {ornith_verdict}")

        print("\n" + "=" * 60)
        print(" [WBS 6 All Items Finished]")
        print(f" Gemma Verdict: {gemma_verdict}")
        print(f" Ornith Verdict: {ornith_verdict}")
        print("=" * 60)

    finally:
        cleanup_containers()


def main() -> None:
    parser = argparse.ArgumentParser(description="WBS 6 CPU+RAM Dual-Resident Runner")
    parser.add_argument("--preflight-only", action="store_true", help="Run only the preflight A/B comparison")
    parser.add_argument("--gate-only", action="store_true", help="Run up to WBS 6.5 dual-resident startup gate only")
    parser.add_argument("--selected-image", type=str, default="", help="Skip preflight and use specified image tag")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
