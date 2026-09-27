#!/usr/bin/env python3
"""WBS 6.8 CPU prefill batch/ubatch 최소 튜닝.

6.8.1: Ornith 35B true-2K 4가지 b/ub screening
       (live tokenizer 기준 prompt_tokens 2000~2048 강제)
6.8.2: true-2K에서 material winner가 있을 때 Ornith 35B 32K 측정
6.8.3: Ornith 32K 개선 확인 후 동일 winner로 Gemma 26B 32K 측정

Safety: --run-screening / --run-ornith-32k / --run-gemma-32k 중 하나를
명시하지 않으면 즉시 종료.
Host check: p520-llm 호스트에서만 실행 가능.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# ── scripts/ 디렉터리를 path에 추가해 run_wbs6_cpu 헬퍼를 재사용 ──
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import bench_harness as h
import build_128k_workload as w
from measurement_policy import future_config

# run_wbs6_cpu 헬퍼 재사용 (import 전에 sys.path 준비 완료)
from run_wbs6_cpu import (  # noqa: E402
    command,
    get_image_digest,
    get_container_pid,
    capture_memory_checkpoint,
    compute_memory_deltas,
    MemoryTelemetryCollector,
    read_system_memory,
    read_vmstat,
    cleanup_containers,
)

# ── 상수 ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
C1_32K_WORKLOAD_MANIFEST = ROOT / "workloads/capacity/v1-32k.json"

DEFAULT_IMAGE = "p520-cpu-llama:b10775"

GEMMA_MODEL_PATH = "/srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf"
ORNITH_MODEL_PATH = "/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf"

GEMMA_PORT = 8082
ORNITH_PORT = 8083

# 6.8.1 true-2K screening 실험 ID 목록
# NOTE: 20260927-001~004는 "2K"로 라벨링되었지만 live usage가 922 prompt tokens였던
# legacy short-prompt diagnostic이다. Raw evidence는 불변 보존하고 재사용/덮어쓰기하지 않는다.
SCREENING_CASES: List[Dict[str, Any]] = [
    {"case": "A", "b": 1024, "ub": 256,  "exp_id": "EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-2K-20260927-005"},
    {"case": "B", "b": 2048, "ub": 512,  "exp_id": "EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-2K-20260927-006"},
    {"case": "C", "b": 4096, "ub": 512,  "exp_id": "EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-2K-20260927-007"},
    {"case": "D", "b": 4096, "ub": 1024, "exp_id": "EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-2K-20260927-008"},
]

# 6.8.2 / 6.8.3 실험 ID
ORNITH_32K_EXP_ID = "EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260927-001"
GEMMA_32K_EXP_ID  = "EXP-P520-CPU-GEMMA4-26B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260927-001"

# true-2K screening은 "대략 2K"가 아니라 live llama.cpp tokenizer의 chat-template 적용 후
# 실제 prompt_tokens가 이 범위에 들어와야만 measured request를 허용한다.
SCREENING_TARGET_MIN = 2000
SCREENING_TARGET_MAX = 2048
SCREENING_TIE_TOLERANCE = 0.02

SCREENING_BASE_UNIT = (
    "Summarize the architectural differences between dense Transformers and Mixture-of-Experts (MoE) models. "
    "Describe how MoE routing mechanisms work, the trade-offs between top-k gating and expert capacity, "
    "and the implications for inference throughput on CPU-only hardware with limited memory bandwidth. "
    "Include a discussion of how speculative decoding via n-gram methods can partially mitigate prefill bottlenecks. "
)
SCREENING_FINE_PAD_UNIT = " pad"

# ── 헬퍼 ────────────────────────────────────────────────────────────────────


def _screening_request_body(content: str) -> Dict[str, Any]:
    return {
        "model": "Ornith-1.5-35B-Q4_K_M.gguf",
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 256,
        "temperature": 0.0,
    }


def _screening_prompt_receipt(
    adapter: h.HTTPAdapter,
    content: str,
) -> Tuple[int, Dict[str, Any]]:
    receipt = adapter.receipt(_screening_request_body(content))
    prompt_tokens = receipt.get("prompt_tokens")
    if type(prompt_tokens) is not int or prompt_tokens < 1:
        raise RuntimeError(f"Invalid live tokenizer receipt: {receipt}")
    return prompt_tokens, receipt


def calibrate_screening_prompt(
    adapter: h.HTTPAdapter,
) -> Tuple[str, int, Dict[str, Any]]:
    """Deterministically materialize a live-tokenized 2000~2048 token prompt."""
    low = 1
    high = 1

    while True:
        content = SCREENING_BASE_UNIT * high
        prompt_tokens, _ = _screening_prompt_receipt(adapter, content)
        if prompt_tokens > SCREENING_TARGET_MAX:
            break
        low = high
        high *= 2
        if high > 256:
            raise RuntimeError("Unable to bracket true-2K screening prompt")

    best_content = ""
    best_tokens = 0
    best_receipt: Dict[str, Any] = {}
    lo = low
    hi = high - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        content = SCREENING_BASE_UNIT * mid
        prompt_tokens, receipt = _screening_prompt_receipt(adapter, content)
        if prompt_tokens <= SCREENING_TARGET_MAX:
            best_content = content
            best_tokens = prompt_tokens
            best_receipt = receipt
            lo = mid + 1
        else:
            hi = mid - 1

    if not best_content:
        raise RuntimeError("Failed to materialize a <=2048-token screening prompt")

    if best_tokens < SCREENING_TARGET_MIN:
        for pad_count in range(1, 257):
            content = best_content + (SCREENING_FINE_PAD_UNIT * pad_count)
            prompt_tokens, receipt = _screening_prompt_receipt(adapter, content)
            if prompt_tokens < SCREENING_TARGET_MIN:
                continue
            if prompt_tokens > SCREENING_TARGET_MAX:
                raise RuntimeError(
                    "Prompt calibration jumped over the true-2K acceptance window: "
                    f"{prompt_tokens} tokens"
                )
            best_content = content
            best_tokens = prompt_tokens
            best_receipt = receipt
            break

    if not (SCREENING_TARGET_MIN <= best_tokens <= SCREENING_TARGET_MAX):
        raise RuntimeError(
            "True-2K prompt calibration failed: "
            f"prompt_tokens={best_tokens}, "
            f"required={SCREENING_TARGET_MIN}..{SCREENING_TARGET_MAX}"
        )

    return best_content, best_tokens, best_receipt


def checkpoint(raw: Path, phase: str, **extra: Any) -> None:
    path = raw / "runtime/progress.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    h.save(path, state | dict(phase=phase, updated_at_utc=h.utc(), **extra))


def _build_ornith_server_cmd(
    b_size: int,
    ub_size: int,
    selected_image: str,
) -> List[str]:
    """단독 Ornith 서버 기동 커맨드 (screening 전용)."""
    return [
        "docker", "run", "-d",
        "--name", "p520-cpu-ornith",
        "-p", f"{ORNITH_PORT}:{ORNITH_PORT}",
        "--cpuset-cpus", "1,2,3,4",
        "-v", "/srv/models:/srv/models:ro",
        selected_image,
        "--host", "0.0.0.0",
        "--port", str(ORNITH_PORT),
        "-m", ORNITH_MODEL_PATH,
        "--n-gpu-layers", "0",
        "--ctx-size", "131072",
        "--parallel", "1",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-fa", "auto",
        "-t", "4",
        "-tb", "4",
        "-b", str(b_size),
        "-ub", str(ub_size),
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


def _build_dual_server_cmds(
    b_size: int,
    ub_size: int,
    selected_image: str,
) -> Tuple[List[str], List[str]]:
    """Gemma + Ornith dual-resident 기동 커맨드."""
    common_server_args = [
        "--n-gpu-layers", "0",
        "--ctx-size", "131072",
        "--parallel", "1",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-fa", "auto",
        "-t", "4",
        "-tb", "4",
        "-b", str(b_size),
        "-ub", str(ub_size),
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
    common_docker_prefix = [
        "--cpuset-cpus", "1,2,3,4",
        "-v", "/srv/models:/srv/models:ro",
        selected_image,
    ]

    gemma_cmd = [
        "docker", "run", "-d",
        "--name", "p520-cpu-gemma",
        "-p", f"{GEMMA_PORT}:{GEMMA_PORT}",
    ] + common_docker_prefix + common_server_args + [
        "--host", "0.0.0.0",
        "--port", str(GEMMA_PORT),
        "-m", GEMMA_MODEL_PATH,
    ]

    ornith_cmd = [
        "docker", "run", "-d",
        "--name", "p520-cpu-ornith",
        "-p", f"{ORNITH_PORT}:{ORNITH_PORT}",
    ] + common_docker_prefix + common_server_args + [
        "--host", "0.0.0.0",
        "--port", str(ORNITH_PORT),
        "-m", ORNITH_MODEL_PATH,
    ]

    return gemma_cmd, ornith_cmd


def _wait_for_server(port: int, timeout_s: int = 300, label: str = "") -> None:
    """서버가 healthy 상태가 될 때까지 대기."""
    adapter = h.HTTPAdapter(f"http://127.0.0.1:{port}", "llama.cpp", timeout_s=180)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if adapter.health().get("healthy"):
                print(f"[+] {label or f'Server:{port}'} is HEALTHY.")
                return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError(f"Server health timeout ({timeout_s}s): {label or port}")


def _wait_for_dual_health(timeout_s: int = 300) -> None:
    """Gemma + Ornith 양쪽 건강 확인."""
    print("[*] Waiting for both CPU servers to become healthy...")
    gemma_adapter = h.HTTPAdapter(f"http://127.0.0.1:{GEMMA_PORT}", "llama.cpp", timeout_s=180)
    ornith_adapter = h.HTTPAdapter(f"http://127.0.0.1:{ORNITH_PORT}", "llama.cpp", timeout_s=180)
    gemma_ok = ornith_ok = False
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if not gemma_ok:
            try:
                gemma_ok = gemma_adapter.health().get("healthy", False)
            except Exception:
                pass
        if not ornith_ok:
            try:
                ornith_ok = ornith_adapter.health().get("healthy", False)
            except Exception:
                pass
        if gemma_ok and ornith_ok:
            print("[+] Both CPU servers HEALTHY and DUAL-RESIDENT!")
            return
        time.sleep(3)
    raise RuntimeError(f"Dual-resident health timeout: gemma={gemma_ok}, ornith={ornith_ok}")


def _stop_ornith_only() -> None:
    subprocess.run(["docker", "rm", "-f", "p520-cpu-ornith"], capture_output=True)


def _stop_all() -> None:
    subprocess.run(["docker", "rm", "-f", "p520-cpu-gemma", "p520-cpu-ornith"], capture_output=True)


# ── 6.8.1 Screening ─────────────────────────────────────────────────────────


def run_screening_case(case_cfg: Dict[str, Any], selected_image: str) -> Dict[str, Any]:
    """단일 true-2K screening 케이스 실행. Ornith 단독 서버."""
    exp_id = case_cfg["exp_id"]
    b_size = case_cfg["b"]
    ub_size = case_cfg["ub"]
    case_label = case_cfg["case"]

    print("\n" + "=" * 60)
    print(f" [WBS 6.8.1 true-2K] Case {case_label}: b={b_size}, ub={ub_size}")
    print(f" EXP_ID: {exp_id}")
    print("=" * 60)

    raw = ROOT / "results/raw" / exp_id
    metrics_path = raw / "metrics.json"
    if raw.exists():
        if metrics_path.exists():
            print(f"[~] Case {case_label}: immutable result already exists — reusing metrics.json.")
            return json.loads(metrics_path.read_text())
        raise RuntimeError(
            f"Immutable raw evidence directory already exists but is incomplete: {raw}. "
            "Refusing to overwrite."
        )

    _stop_ornith_only()
    time.sleep(1)

    server_cmd = _build_ornith_server_cmd(b_size, ub_size, selected_image)
    print(f"[*] Starting Ornith server (b={b_size}, ub={ub_size})...")
    subprocess.run(server_cmd, check=True)

    try:
        _wait_for_server(ORNITH_PORT, timeout_s=300, label=f"Ornith-b{b_size}-ub{ub_size}")
        adapter = h.HTTPAdapter(f"http://127.0.0.1:{ORNITH_PORT}", "llama.cpp", timeout_s=600)

        screening_prompt, calibrated_tokens, tokenizer_receipt = calibrate_screening_prompt(adapter)
        raw_prompt_sha256 = h.sha(screening_prompt.encode())
        print(
            f"[*] Live-tokenized screening prompt: {calibrated_tokens} tokens "
            f"(required {SCREENING_TARGET_MIN}..{SCREENING_TARGET_MAX})"
        )

        raw.mkdir(parents=True, exist_ok=False)
        runtime_dir = raw / "runtime"
        runtime_dir.mkdir()

        req_body = _screening_request_body(screening_prompt)
        h.save(raw / "prompt-evidence.json", {
            "experiment_id": exp_id,
            "target_min_prompt_tokens": SCREENING_TARGET_MIN,
            "target_max_prompt_tokens": SCREENING_TARGET_MAX,
            "calibrated_prompt_tokens": calibrated_tokens,
            "raw_prompt_sha256": raw_prompt_sha256,
            "tokenizer_receipt": tokenizer_receipt,
        })

        print("[*] Sending true-2K screening request...")
        t0 = time.time()
        try:
            res = adapter.call("/v1/chat/completions", body=req_body)
        except Exception as exc:
            h.save(runtime_dir / "progress.json", {
                "phase": "failed",
                "case": case_label,
                "error": repr(exc),
                "updated_at_utc": h.utc(),
            })
            raise RuntimeError(f"Case {case_label}: inference request failed: {exc}") from exc
        wall_s = time.time() - t0

        timings = res.get("timings", {})
        usage = res.get("usage", {})
        prompt_n = usage.get("prompt_tokens", timings.get("prompt_n", 0))
        predicted_n = usage.get("completion_tokens", timings.get("predicted_n", 0))

        if type(prompt_n) is not int or not (SCREENING_TARGET_MIN <= prompt_n <= SCREENING_TARGET_MAX):
            raise RuntimeError(
                f"Case {case_label}: measured request is not true-2K: prompt_tokens={prompt_n}"
            )
        if prompt_n != calibrated_tokens:
            raise RuntimeError(
                f"Case {case_label}: tokenizer drift between receipt and measured request: "
                f"receipt={calibrated_tokens}, measured={prompt_n}"
            )

        prompt_ms = timings.get("prompt_ms", 0)
        predicted_ms = timings.get("predicted_ms", 0)

        prompt_tps = timings.get("prompt_per_second")
        if not prompt_tps and prompt_n and prompt_ms:
            prompt_tps = prompt_n / (prompt_ms / 1000.0)

        decode_tps = timings.get("predicted_per_second")
        if not decode_tps and predicted_n and predicted_ms:
            decode_tps = predicted_n / (predicted_ms / 1000.0)

        ttft_ms = prompt_ms if prompt_ms else (wall_s * 1000.0)

        metrics = {
            "experiment_id": exp_id,
            "case": case_label,
            "b": b_size,
            "ub": ub_size,
            "prompt_tokens": prompt_n,
            "completion_tokens": predicted_n,
            "prompt_ms": prompt_ms,
            "predicted_ms": predicted_ms,
            "ttft_ms": ttft_ms,
            "prompt_eval_tps": prompt_tps,
            "decode_tps": decode_tps,
            "wall_s": wall_s,
            "cache_n": timings.get("cache_n"),
            "raw_prompt_sha256": raw_prompt_sha256,
            "tokenizer_receipt": tokenizer_receipt,
            "timings": timings,
            "measured_at_utc": h.utc(),
        }

        h.save(raw / "metrics.json", metrics)
        h.save(raw / "completion.json", {
            "experiment_id": exp_id,
            "case": case_label,
            "b": b_size,
            "ub": ub_size,
            "verdict": "PASS",
            "completed_at_utc": h.utc(),
            "response": res,
        })
        h.save(runtime_dir / "progress.json", {
            "phase": "done",
            "case": case_label,
            "updated_at_utc": h.utc(),
        })

        decode_tps_str = f"{decode_tps:.2f}" if decode_tps else "N/A"
        prompt_tps_str = f"{prompt_tps:.2f}" if prompt_tps else "N/A"
        print(
            f"[+] Case {case_label} done: prompt_tokens={prompt_n}, "
            f"prompt_tps={prompt_tps_str}, decode_tps={decode_tps_str}, "
            f"TTFT={ttft_ms:.0f}ms"
        )
        return metrics

    finally:
        _stop_ornith_only()
        time.sleep(2)


def select_winner(screening_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """±2% 이내는 동률로 보고 그중 더 작은 b/ub 조합을 우선한다."""
    valid = [
        r for r in screening_results
        if isinstance(r.get("prompt_eval_tps"), (int, float)) and r["prompt_eval_tps"] > 0
    ]
    if not valid:
        raise RuntimeError("No valid screening result with prompt_eval_tps")

    peak_tps = max(r["prompt_eval_tps"] for r in valid)
    tie_floor = peak_tps * (1.0 - SCREENING_TIE_TOLERANCE)
    tied = [r for r in valid if r["prompt_eval_tps"] >= tie_floor]
    return min(tied, key=lambda r: (r["b"], r["ub"]))


# ── 6.8.2 / 6.8.3 Dual-resident 32K 측정 ────────────────────────────────────


def run_32k_with_peer(
    exp_id: str,
    model_name: str,
    model_key: str,
    model_path: str,
    port: int,
    peer_name: str,
    peer_port: int,
    b_size: int,
    ub_size: int,
    selected_image: str,
) -> str:
    """Dual-resident 서버 기동 후 32K measured request 실행."""
    print("\n" + "=" * 60)
    print(f" [WBS 6.8 32K Run] {exp_id}")
    print(f" Model: {model_name} on port {port}  Peer: {peer_name} on port {peer_port}")
    print(f" b={b_size}, ub={ub_size}")
    print("=" * 60)

    raw = ROOT / "results/raw" / exp_id
    if raw.exists():
        raise RuntimeError(
            f"Immutable raw evidence directory already exists: {raw}. "
            "Refusing to overwrite."
        )
    raw.mkdir(parents=True, exist_ok=False)
    runtime_dir = raw / "runtime"
    runtime_dir.mkdir()

    # 이전 컨테이너 정리
    _stop_all()
    time.sleep(1)

    # Checkpoint A: baseline_before_startup
    snap_a = capture_memory_checkpoint("checkpoint_a_baseline_before_startup")
    print(
        f"[*] [Checkpoint A] MemAvailable={snap_a['system_memory_kib'].get('MemAvailable')} kB, "
        f"SwapUsed={snap_a['system_memory_kib'].get('SwapUsed')} kB"
    )

    # Dual-resident 서버 기동
    gemma_cmd, ornith_cmd = _build_dual_server_cmds(b_size, ub_size, selected_image)
    print("[*] Starting Gemma 26B server (128K ctx)...")
    subprocess.run(gemma_cmd, check=True)
    print("[*] Starting Ornith 35B server (128K ctx)...")
    subprocess.run(ornith_cmd, check=True)

    gemma_pid = get_container_pid("p520-cpu-gemma")
    ornith_pid = get_container_pid("p520-cpu-ornith")
    print(f"[+] Container PIDs: Gemma={gemma_pid}, Ornith={ornith_pid}")

    try:
        _wait_for_dual_health(timeout_s=300)

        # Checkpoint B: startup_healthy
        snap_b = capture_memory_checkpoint("checkpoint_b_startup_healthy", gemma_pid, ornith_pid)
        print(
            f"[*] [Checkpoint B] MemAvailable={snap_b['system_memory_kib'].get('MemAvailable')} kB, "
            f"SwapUsed={snap_b['system_memory_kib'].get('SwapUsed')} kB"
        )

        h.save(runtime_dir / "checkpoint_a_baseline_before_startup.json", snap_a)
        h.save(runtime_dir / "checkpoint_b_startup_healthy.json", snap_b)
        startup_deltas = compute_memory_deltas(snap_a, snap_b)
        h.save(runtime_dir / "memory-startup-deltas.json", startup_deltas)

        endpoint = f"http://127.0.0.1:{port}"
        peer_endpoint = f"http://127.0.0.1:{peer_port}"
        adapter = h.HTTPAdapter(endpoint, "llama.cpp", timeout_s=7200)
        peer_adapter = h.HTTPAdapter(peer_endpoint, "llama.cpp", timeout_s=180)

        # Peer 건강 확인
        try:
            peer_health_pre = peer_adapter.health()
        except Exception as exc:
            peer_health_pre = {"healthy": False, "error": repr(exc)}
        if not peer_health_pre.get("healthy"):
            raise RuntimeError(f"Peer {peer_name} unhealthy before measurement: {peer_health_pre}")

        # 측정 컨테이너 이름 결정
        container_name = "p520-cpu-gemma" if "GEMMA" in exp_id else "p520-cpu-ornith"

        planned = {
            "schema_version": 1,
            "experiment_id": exp_id,
            "model": model_name,
            "model_key": model_key,
            "model_identity": {"path": model_path},
            "launch_command": (
                f"docker run -d --name {container_name} -p {port}:{port} "
                f"--cpuset-cpus 1,2,3,4 -v /srv/models:/srv/models:ro {selected_image} "
                f"--n-gpu-layers 0 --ctx-size 131072 --parallel 1 -ctk q8_0 -ctv q8_0 -fa auto "
                f"-t 4 -tb 4 -b {b_size} -ub {ub_size} --cpu-strict 1 --poll 50 "
                f"--load-mode mmap --cache-ram 0 --no-cache-prompt --no-context-shift "
                f"--threads-http 1 --no-webui "
                f"--spec-type ngram-mod --spec-ngram-mod-n-match 24 "
                f"--spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64 "
                f"--host 0.0.0.0 --port {port} -m {model_path}"
            ),
            "runtime": "llama.cpp",
            "runtime_flavor": "cpu-only",
            "runtime_image": selected_image,
            "runtime_image_digest": get_image_digest(selected_image),
            "runtime_revision": f"{selected_image} ({get_image_digest(selected_image)[:19]})",
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
            "prefix_cache_lane": "cold-independent",
            "chat_template": "none",
            "tool_parser": "none",
            "thinking": False,
            "endpoint": endpoint,
            "peer_resident_model": peer_name,
            "peer_resident_endpoint": peer_endpoint,
            "workload_manifest": str(C1_32K_WORKLOAD_MANIFEST),
            "batch_size": b_size,
            "ubatch_size": ub_size,
            "notes": (
                f"WBS 6.8 CPU+RAM dual-resident 128K server context with 32K serial measured request; "
                f"peer {peer_name} idle resident; b={b_size} ub={ub_size} (WBS 6.8 winner)"
            ),
        }

        config = future_config(planned)
        h.save(runtime_dir / "planned-config.json", config)
        checkpoint(raw, "prepared", step="config_written")

        # 메모리 텔레메트리 수집
        mem_collector = MemoryTelemetryCollector(
            output_csv=runtime_dir / "memory-telemetry.csv",
            gemma_pid=gemma_pid,
            ornith_pid=ornith_pid,
            interval_s=1.0,
        )
        mem_collector.start()

        pre_snap_label = "checkpoint_c_32k_pre"
        post_snap_label = "checkpoint_d_32k_post"

        pre_snap = capture_memory_checkpoint(pre_snap_label, gemma_pid, ornith_pid)
        h.save(runtime_dir / f"{pre_snap_label}.json", pre_snap)

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
            print(f"[+] Measurement complete: {verdict}")

        except Exception as exc:
            run_batch_err = exc
            verdict = f"FAIL_ERROR_{type(exc).__name__}"
            checkpoint(raw, "failed", error=str(exc), verdict=verdict)
            print(f"[!] Error during measured inference batch: {exc}")

        finally:
            try:
                post_snap = capture_memory_checkpoint(post_snap_label, gemma_pid, ornith_pid)
                h.save(runtime_dir / f"{post_snap_label}.json", post_snap)
                memory_deltas = mem_collector.compute_summary_deltas(pre_snap, post_snap)
                h.save(raw / "memory-baseline-before-startup.json", snap_a)
                h.save(raw / "memory-deltas.json", memory_deltas)
                print(
                    f"[+] Memory deltas: swap_delta={memory_deltas['swap_used_delta_kib']} kB, "
                    f"pswpin={memory_deltas['pswpin_delta']}, pswpout={memory_deltas['pswpout_delta']}, "
                    f"pgmajfault={memory_deltas['pgmajfault_delta']}"
                )
            except Exception as snap_err:
                print(f"[!] Error recording memory deltas: {snap_err}")
            mem_collector.stop()

        # Post-health check
        try:
            my_health = adapter.health()
        except Exception as exc:
            my_health = {"healthy": False, "error": repr(exc)}
        try:
            peer_health_post = peer_adapter.health()
        except Exception as exc:
            peer_health_post = {"healthy": False, "error": repr(exc)}
        h.save(raw / "dual_resident_post_health.json", {
            "active_model_health": my_health,
            "peer_model_health": peer_health_post,
            "both_healthy": bool(my_health.get("healthy") and peer_health_post.get("healthy")),
        })

        if run_batch_err is not None:
            raise run_batch_err

        return verdict

    finally:
        _stop_all()


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="WBS 6.8 CPU prefill batch/ubatch 최소 튜닝 실험 러너"
    )
    parser.add_argument(
        "--run-screening",
        action="store_true",
        help="6.8.1: live-tokenized true-2K (2000~2048 tokens) Ornith 4-case screening 실행",
    )
    parser.add_argument(
        "--run-ornith-32k",
        action="store_true",
        help="6.8.2: Winner b/ub로 Ornith 35B 32K 측정",
    )
    parser.add_argument(
        "--run-gemma-32k",
        action="store_true",
        help="6.8.3: Winner b/ub로 Gemma 26B 32K 측정",
    )
    parser.add_argument(
        "--winner-b",
        type=int,
        default=0,
        help="winner batch size (-b) (32K 실험에 필요)",
    )
    parser.add_argument(
        "--winner-ub",
        type=int,
        default=0,
        help="winner ubatch size (-ub) (32K 실험에 필요)",
    )
    parser.add_argument(
        "--selected-image",
        type=str,
        default=DEFAULT_IMAGE,
        help=f"Docker image tag (default: {DEFAULT_IMAGE})",
    )
    args = parser.parse_args()

    # Safety stop
    if not any([args.run_screening, args.run_ornith_32k, args.run_gemma_32k]):
        print("=" * 60)
        print(" [-] Safety Stop: No explicit execution action specified.")
        print("=" * 60)
        print("  Available actions:")
        print("    --run-screening       : 6.8.1 Ornith true-2K (2000~2048) 4-case b/ub screening")
        print("    --run-ornith-32k      : 6.8.2 Ornith 35B 32K measured (--winner-b / --winner-ub 필요)")
        print("    --run-gemma-32k       : 6.8.3 Gemma 26B 32K measured (--winner-b / --winner-ub 필요)")
        print()
        print("  Runner exits without starting any long-running inference.")
        sys.exit(0)

    # Host check
    hostname = socket.gethostname().split(".")[0]
    if hostname != "p520-llm":
        raise RuntimeError(
            f"WBS 6.8 runner requires p520-llm host, got: {hostname}"
        )

    selected_image = args.selected_image

    # Experiment lock
    lock_path = ROOT / "results/experiment.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _run_locked(args, selected_image)


def _run_locked(args: argparse.Namespace, selected_image: str) -> None:
    # ── 6.8.1 Screening ──────────────────────────────────────────────────────
    if args.run_screening:
        print("\n" + "=" * 60)
        print(" [WBS 6.8.1] Ornith true-2K b/ub Screening (4 cases)")
        print("=" * 60)

        summary_path = ROOT / "results/raw/WBS68-TRUE2K-SCREENING-SUMMARY.json"
        winner_path = ROOT / "results/raw/WBS68-TRUE2K-WINNER.json"
        if summary_path.exists() or winner_path.exists():
            raise RuntimeError(
                "True-2K summary/winner evidence already exists. Refusing to overwrite: "
                f"{summary_path}, {winner_path}"
            )

        screening_results: List[Dict[str, Any]] = []
        for case_cfg in SCREENING_CASES:
            result = run_screening_case(case_cfg, selected_image)
            screening_results.append(result)

        prompt_counts = {r.get("prompt_tokens") for r in screening_results}
        prompt_hashes = {r.get("raw_prompt_sha256") for r in screening_results}
        if len(prompt_counts) != 1 or not all(
            isinstance(x, int) and SCREENING_TARGET_MIN <= x <= SCREENING_TARGET_MAX
            for x in prompt_counts
        ):
            raise RuntimeError(
                f"Screening cases did not use one identical true-2K token count: {prompt_counts}"
            )
        if len(prompt_hashes) != 1 or None in prompt_hashes:
            raise RuntimeError(
                f"Screening cases did not use one identical prompt payload: {prompt_hashes}"
            )

        h.save(summary_path, {
            "wbs": "6.8.1",
            "screening_revision": "true-2k-v2",
            "target_prompt_tokens": {
                "min": SCREENING_TARGET_MIN,
                "max": SCREENING_TARGET_MAX,
            },
            "identical_prompt_tokens": next(iter(prompt_counts)),
            "identical_raw_prompt_sha256": next(iter(prompt_hashes)),
            "completed_at_utc": h.utc(),
            "cases": screening_results,
        })

        winner = select_winner(screening_results)
        peak_tps = max(r["prompt_eval_tps"] for r in screening_results)
        tie_floor = peak_tps * (1.0 - SCREENING_TIE_TOLERANCE)
        tied_cases = [
            r["case"] for r in screening_results
            if r["prompt_eval_tps"] >= tie_floor
        ]

        print("\n" + "=" * 60)
        print(" [WBS 6.8.1] True-2K Screening Results")
        print("=" * 60)
        print(f"{'Case':<6} {'b':>6} {'ub':>6} {'tokens':>8} {'prompt_tps':>12} {'TTFT(ms)':>10}")
        print("-" * 54)
        for r in screening_results:
            tps = r.get("prompt_eval_tps")
            tps_str = f"{tps:.2f}" if tps else "N/A"
            print(
                f"{r['case']:<6} {r['b']:>6} {r['ub']:>6} "
                f"{r['prompt_tokens']:>8} {tps_str:>12} {r['ttft_ms']:>10.0f}"
            )
        print()
        print(
            f"Winner by ±{SCREENING_TIE_TOLERANCE * 100:.0f}% tie policy: "
            f"Case {winner['case']} (b={winner['b']}, ub={winner['ub']}, "
            f"prompt_tps={winner.get('prompt_eval_tps', 0):.2f}); tied={tied_cases}"
        )

        h.save(winner_path, {
            "wbs": "6.8.1",
            "screening_revision": "true-2k-v2",
            "selection_policy": "within_2pct_of_peak_then_smallest_b_ub",
            "tie_tolerance": SCREENING_TIE_TOLERANCE,
            "peak_prompt_eval_tps": peak_tps,
            "tie_floor_prompt_eval_tps": tie_floor,
            "tied_cases": tied_cases,
            "winner_case": winner["case"],
            "winner_b": winner["b"],
            "winner_ub": winner["ub"],
            "winner_prompt_eval_tps": winner.get("prompt_eval_tps"),
            "selected_at_utc": h.utc(),
        })

    # ── 6.8.2 Ornith 32K ─────────────────────────────────────────────────────
    if args.run_ornith_32k:
        b_size = args.winner_b
        ub_size = args.winner_ub
        if not b_size or not ub_size:
            raise ValueError("--run-ornith-32k requires --winner-b and --winner-ub")
        print(f"\n[WBS 6.8.2] Ornith 35B 32K with winner b={b_size}, ub={ub_size}")
        verdict = run_32k_with_peer(
            exp_id=ORNITH_32K_EXP_ID,
            model_name="Ornith-1.5-35B-Q4_K_M.gguf",
            model_key="ornith-1.5-35b-a3b",
            model_path=ORNITH_MODEL_PATH,
            port=ORNITH_PORT,
            peer_name="gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf",
            peer_port=GEMMA_PORT,
            b_size=b_size,
            ub_size=ub_size,
            selected_image=selected_image,
        )
        print(f"[+] WBS 6.8.2 Ornith 32K verdict: {verdict}")

    # ── 6.8.3 Gemma 32K ──────────────────────────────────────────────────────
    if args.run_gemma_32k:
        b_size = args.winner_b
        ub_size = args.winner_ub
        if not b_size or not ub_size:
            raise ValueError("--run-gemma-32k requires --winner-b and --winner-ub")
        print(f"\n[WBS 6.8.3] Gemma 26B 32K with winner b={b_size}, ub={ub_size}")
        verdict = run_32k_with_peer(
            exp_id=GEMMA_32K_EXP_ID,
            model_name="gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf",
            model_key="gemma4-26b-a4b",
            model_path=GEMMA_MODEL_PATH,
            port=GEMMA_PORT,
            peer_name="Ornith-1.5-35B-Q4_K_M.gguf",
            peer_port=ORNITH_PORT,
            b_size=b_size,
            ub_size=ub_size,
            selected_image=selected_image,
        )
        print(f"[+] WBS 6.8.3 Gemma 32K verdict: {verdict}")


if __name__ == "__main__":
    main()
