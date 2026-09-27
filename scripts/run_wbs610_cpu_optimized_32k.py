#!/usr/bin/env python3
"""WBS 6.10 — Ornith 35B optimized CPU true-32K C vs D comparison.

Exactly two measured requests:
  C32: -b 4096 -ub 512
  D32: -b 4096 -ub 1024

Purpose:
- extend the WBS 6.9 true-4K finding to 32K
- isolate ubatch effect by disabling prompt/prefix cache for the measured request
- keep the optimized OpenBLAS+LTO serving image and all other runtime settings fixed

No full-size warmup request is issued. Each case starts from a fresh server.
The built-in llama-server warmup is retained, but measured inference count is
exactly one request per case.
"""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import bench_harness as h
import build_128k_workload as w
from measurement_policy import future_config

ROOT = Path(__file__).resolve().parents[1]
WORKLOAD_MANIFEST = ROOT / "workloads/capacity/v1-32k.json"

DEFAULT_IMAGE = "p520-cpu-llama-opt:b10775-blas"
MODEL_PATH = "/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf"
MODEL_NAME = "Ornith-1.5-35B-Q4_K_M.gguf"
PORT = 8084
CONTAINER = "p520-cpu-ornith-opt32k"
OUTPUT_RESERVE = 1024

CASES: List[Dict[str, Any]] = [
    {
        "case": "C32",
        "b": 4096,
        "ub": 512,
        "exp_id": "EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-003",
    },
    {
        "case": "D32",
        "b": 4096,
        "ub": 1024,
        "exp_id": "EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-004",
    },
]


def command(args: List[str], *, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        capture_output=True,
        check=check,
        timeout=timeout,
    )


def stop_container() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER], text=True, capture_output=True)


def image_digest(image: str) -> str:
    cp = command(["docker", "image", "inspect", image, "--format", "{{index .RepoDigests 0}}"], check=False, timeout=15)
    if cp.returncode == 0 and cp.stdout.strip():
        return cp.stdout.strip()
    cp = command(["docker", "image", "inspect", image, "--format", "{{.Id}}"], timeout=15)
    return cp.stdout.strip()


def list_devices(image: str) -> str:
    cp = command([
        "docker", "run", "--rm",
        "--entrypoint", "/app/llama-server",
        image,
        "--list-devices",
    ], check=False, timeout=60)
    output = (cp.stdout or "") + "\n" + (cp.stderr or "")
    if cp.returncode != 0:
        raise RuntimeError(f"optimized image --list-devices failed:\n{output}")
    if "blas" not in output.lower():
        raise RuntimeError("BLAS device is not visible; refusing fallback.\n" + output)
    return output


def server_command(case: Dict[str, Any], image: str) -> List[str]:
    return [
        "docker", "run", "-d",
        "--name", CONTAINER,
        "-p", f"{PORT}:{PORT}",
        "--cpuset-cpus", "1,2,3,4",
        "-v", "/srv/models:/srv/models:ro",
        "-e", "GGML_OPENVINO_DEVICE=",
        image,
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "-m", MODEL_PATH,
        "--n-gpu-layers", "0",
        "--ctx-size", "131072",
        "--parallel", "1",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-fa", "on",
        "-t", "4",
        "-tb", "4",
        "-b", str(case["b"]),
        "-ub", str(case["ub"]),
        "--cpu-strict", "1",
        "--cpu-strict-batch", "1",
        "--prio", "1",
        "--prio-batch", "1",
        "--poll", "50",
        "--poll-batch", "1",
        "--repack",
        "--load-mode", "mmap",
        "--lazy-mode", "off",
        "--warmup",
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


def wait_health(timeout_s: int = 600) -> h.HTTPAdapter:
    adapter = h.HTTPAdapter(f"http://127.0.0.1:{PORT}", "llama.cpp", timeout_s=9000)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if adapter.health().get("healthy"):
                return adapter
        except Exception:
            pass
        time.sleep(3)
    logs = command(["docker", "logs", CONTAINER], check=False, timeout=30)
    raise RuntimeError(
        "optimized 32K server health timeout\n"
        + (logs.stdout or "")
        + "\n"
        + (logs.stderr or "")
    )


def materialize_32k(adapter: h.HTTPAdapter) -> Dict[str, Any]:
    manifest = w.load_manifest(WORKLOAD_MANIFEST)
    workload = w.build(manifest, adapter, MODEL_NAME)
    evidence = workload.get("build_evidence", [])
    if len(evidence) != 1:
        raise RuntimeError(f"expected one 32K request, got build_evidence={evidence}")

    item = evidence[0]
    prompt_tokens = item.get("prompt_tokens")
    total_budget = item.get("total_budget_used")
    if type(prompt_tokens) is not int:
        raise RuntimeError(f"invalid prompt token evidence: {item}")
    if prompt_tokens + OUTPUT_RESERVE > 32768:
        raise RuntimeError(
            f"32K budget exceeded: prompt={prompt_tokens}, reserve={OUTPUT_RESERVE}"
        )
    if isinstance(total_budget, int) and total_budget > 32768:
        raise RuntimeError(f"materialized total budget exceeds 32K: {total_budget}")
    return workload


def run_case(case: Dict[str, Any], image: str, device_evidence: str) -> Dict[str, Any]:
    raw = ROOT / "results/raw" / case["exp_id"]
    if raw.exists():
        raise RuntimeError(f"immutable experiment directory exists: {raw}")

    digest = image_digest(image)
    launch_args = server_command(case, image)
    config = future_config({
        "experiment_id": case["exp_id"],
        "measured_repetitions": 1,
        "warmup_count": 0,
        "model": MODEL_NAME,
        "model_key": "ornith-1.5-35b-a3b",
        "model_identity": {
            "path": MODEL_PATH,
            "weight_quant": "Q4_K_M",
        },
        "runtime": "llama.cpp",
        "runtime_revision": "b10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb",
        "runtime_flavor": "cpu-only-openblas-lto",
        "runtime_image": image,
        "runtime_image_digest": digest,
        "launch_command": shlex.join(launch_args),
        "backend_variant": "CPU-ONLY-W2135-OPTBLAS",
        "topology": "cpu-standalone-4core",
        "topology_detail": "logical CPU IDs 1,2,3,4 mapped to four distinct physical cores",
        "concurrency": 1,
        "server_ctx_size": 131072,
        "measured_request_class": "32K",
        "context_tokens": 32768,
        "weight_quant": "Q4_K_M",
        "kv_cache": "Q8_0",
        "speculative": "ngram-mod",
        "ngram": "ngram-mod-24-48-64",
        "prefix_cache_lane": "cold-independent",
        "chat_template": "model-native/default llama.cpp chat template",
        "tool_parser": "none",
        "thinking": False,
        "b": case["b"],
        "ub": case["ub"],
        "optimization_stack": [
            "OpenBLAS build",
            "GGML_LTO=ON",
            "GGML_CPU_ALL_VARIANTS=ON",
            "Flash Attention forced on",
            "mmap + lazy-mode off + server warmup",
            "weight repack",
            "strict batch affinity",
            "medium priority",
            "polling",
        ],
        "workload_manifest": str(WORKLOAD_MANIFEST),
        "notes": (
            "WBS 6.10 32K C-vs-D comparison. Prompt cache intentionally disabled "
            "so both cases evaluate the same full materialized prompt."
        ),
    })

    # Validate the complete harness identity before starting a container or
    # creating immutable raw evidence. This prevents preparation-only failures
    # from consuming an experiment ID.
    h.validate(config)

    stop_container()
    time.sleep(1)

    cp = command(launch_args, check=False, timeout=60)
    if cp.returncode != 0:
        raise RuntimeError(f"failed to start {case['case']}: {cp.stderr}")

    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / "runtime"
    runtime.mkdir()

    h.save(runtime / "planned-config.json", config)
    h.save(runtime / "device-evidence.json", {
        "image": image,
        "image_digest": digest,
        "list_devices": device_evidence,
    })

    try:
        adapter = wait_health()

        workload = materialize_32k(adapter)
        evidence = workload["build_evidence"][0]
        workload_hash = h.sha(h.canon(workload))
        prompt_hash = evidence["raw_prompt_sha256"]
        h.save(runtime / "workload-evidence.json", {
            "workload_sha256": workload_hash,
            "request_id": evidence.get("request_id"),
            "prompt_tokens": evidence.get("prompt_tokens"),
            "total_budget_used": evidence.get("total_budget_used"),
            "utilization": evidence.get("utilization"),
            "raw_prompt_sha256": prompt_hash,
            "output_reserve": OUTPUT_RESERVE,
        })

        started = time.time()
        verdict = h.run_batch(raw, config, workload, adapter)
        wall_outer = time.time() - started

        logs = command(["docker", "logs", CONTAINER], check=False, timeout=60)
        (runtime / "server.log").write_text((logs.stdout or "") + "\n" + (logs.stderr or ""))

        post_health = adapter.health()
        h.save(runtime / "post-health.json", post_health)
        if not post_health.get("healthy"):
            raise RuntimeError(f"server unhealthy after measured request: {post_health}")

        metrics_path = raw / "metrics.json"
        if not metrics_path.exists():
            raise RuntimeError("harness did not produce metrics.json")
        metrics = json.loads(metrics_path.read_text())

        result = {
            "case": case["case"],
            "experiment_id": case["exp_id"],
            "b": case["b"],
            "ub": case["ub"],
            "verdict": verdict,
            "prompt_tokens": evidence.get("prompt_tokens"),
            "raw_prompt_sha256": prompt_hash,
            "workload_sha256": workload_hash,
            "prefill_tps": metrics.get("prefill_tps"),
            "ttft_ms": metrics.get("ttft_ms"),
            "decode_tps": metrics.get("mean_request_decode_tps"),
            "batch_wall_s": metrics.get("batch_wall_s"),
            "outer_wall_s": wall_outer,
            "peak_vram_gpu0_mib": metrics.get("peak_vram_gpu0_mib"),
            "peak_vram_gpu1_mib": metrics.get("peak_vram_gpu1_mib"),
        }
        h.save(raw / "wbs610-result.json", result)
        return result

    finally:
        stop_container()
        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="run exactly two measured 32K requests: C32 then D32")
    parser.add_argument("--selected-image", default=DEFAULT_IMAGE)
    args = parser.parse_args()

    if not args.run:
        print("Safety stop: pass --run to execute WBS 6.10 (exactly 2 measured requests).")
        return

    if socket.gethostname().split(".")[0] != "p520-llm":
        raise RuntimeError("WBS 6.10 requires p520-llm host")

    lock_path = ROOT / "results/experiment.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)

        summary_path = ROOT / "results/raw/WBS610-OPTBLAS-32K-C-VS-D.json"
        if summary_path.exists():
            raise RuntimeError(f"immutable comparison summary exists: {summary_path}")

        device_evidence = list_devices(args.selected_image)
        results: List[Dict[str, Any]] = []
        for case in CASES:
            results.append(run_case(case, args.selected_image, device_evidence))

        prompt_tokens = {r["prompt_tokens"] for r in results}
        prompt_hashes = {r["raw_prompt_sha256"] for r in results}
        if len(prompt_tokens) != 1:
            raise RuntimeError(f"C32/D32 prompt token counts differ: {prompt_tokens}")
        if len(prompt_hashes) != 1:
            raise RuntimeError("C32/D32 materialized prompt hashes differ")

        c, d = results
        comparison = {
            "wbs": "6.10",
            "measured_request_count": 2,
            "comparison": "C32 ub512 vs D32 ub1024; b4096 fixed",
            "prompt_tokens": next(iter(prompt_tokens)),
            "raw_prompt_sha256": next(iter(prompt_hashes)),
            "cache_policy": "disabled for measured request",
            "cases": results,
            "derived": {},
            "completed_at_utc": h.utc(),
        }

        if isinstance(c.get("prefill_tps"), (int, float)) and c["prefill_tps"]:
            comparison["derived"]["d_vs_c_prefill_pct"] = (d["prefill_tps"] / c["prefill_tps"] - 1.0) * 100.0
        if isinstance(c.get("ttft_ms"), (int, float)) and c["ttft_ms"]:
            comparison["derived"]["d_vs_c_ttft_pct"] = (d["ttft_ms"] / c["ttft_ms"] - 1.0) * 100.0
        if isinstance(c.get("batch_wall_s"), (int, float)) and c["batch_wall_s"]:
            comparison["derived"]["d_vs_c_wall_pct"] = (d["batch_wall_s"] / c["batch_wall_s"] - 1.0) * 100.0

        h.save(summary_path, comparison)

        print("\nWBS 6.10 true-32K C vs D")
        print("Case   b     ub    prompt_tokens   prefill_tps   ttft_s   wall_s")
        for r in results:
            ttft_s = (r["ttft_ms"] / 1000.0) if isinstance(r.get("ttft_ms"), (int, float)) else 0.0
            print(
                f"{r['case']:<4} {r['b']:>5} {r['ub']:>6} "
                f"{r['prompt_tokens']:>13} {r['prefill_tps']:>12.2f} "
                f"{ttft_s:>8.2f} {r['batch_wall_s']:>8.2f}"
            )
        print(json.dumps(comparison["derived"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
