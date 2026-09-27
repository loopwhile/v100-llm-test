#!/usr/bin/env python3
"""WBS 6.9 combined optimized CPU serving stack — true-4K, exactly 4 measured cases.

Measured variable:
  A: -b 1024 -ub 256
  B: -b 2048 -ub 512
  C: -b 4096 -ub 512
  D: -b 4096 -ub 1024

Everything else is fixed:
- Ornith 1.5 35B-A3B Q4_K_M
- 4 physical CPU cores via cpuset 1,2,3,4; -t/-tb 4
- Q8_0 KV, 128K server capacity, ngram-mod 24/48/64
- OpenVINO CPU backend, OpenBLAS-enabled build, LTO
- Flash Attention forced ON
- mmap + lazy-mode off + normal server warmup
- prompt cache/reuse with an unmeasured ~1K common-prefix priming request
- strict batch affinity, medium priority, polling, repack

There are exactly four measured requests. Backend/device checks, a compile-shape
warmup request, and a cache-priming request are setup gates and are not measured
benchmark requests.

No silent fallback: if OpenVINO is not visible/active, the run stops before
accepting measured evidence.
"""
from __future__ import annotations

import argparse
import fcntl
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import bench_harness as h
from measurement_policy import future_config

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_IMAGE = "p520-cpu-llama-opt:b10775-blas"
ORNITH_MODEL_PATH = "/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf"
ORNITH_MODEL_NAME = "Ornith-1.5-35B-Q4_K_M.gguf"
PORT = 8084
CONTAINER = "p520-cpu-ornith-opt"

TARGET_MIN = 4000
TARGET_MAX = 4096
PREFIX_MIN = 1600
PREFIX_MAX = 1638
COMPLETION_TOKENS = 256
CACHE_REUSE_MIN = 256
CACHE_HIT_ACCEPT_MIN = 512
TIE_TOLERANCE = 0.02

CASES: List[Dict[str, Any]] = [
    {
        "case": "A",
        "b": 1024,
        "ub": 256,
        "exp_id": "EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-005",
    },
    {
        "case": "B",
        "b": 2048,
        "ub": 512,
        "exp_id": "EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-006",
    },
    {
        "case": "C",
        "b": 4096,
        "ub": 512,
        "exp_id": "EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-007",
    },
    {
        "case": "D",
        "b": 4096,
        "ub": 1024,
        "exp_id": "EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-4K-20260927-008",
    },
]

SYSTEM_PROMPT = (
    "You are a background technical research worker. Analyze source material "
    "precisely, preserve technical distinctions, and produce a concise synthesis."
)
PREFIX_UNIT = (
    " Shared project context: this benchmark represents a persistent research "
    "agent with reusable instructions, schema, terminology, and prior project state."
)
FRESH_UNIT = (
    " New source section: compare implementation constraints, runtime behavior, "
    "memory traffic, scheduling, cache behavior, and reproducibility evidence. "
    "Distinguish measured facts from inference and retain concrete configuration details."
)
WARMUP_SYSTEM = "Independent compile-shape warmup. Do not reuse this content as project context."
WARMUP_UNIT = (
    " Distinct warmup material for compiling the backend graph at the same prompt "
    "shape while avoiding the measured project's reusable prefix."
)
FINE_PAD_UNIT = " pad"


def command(args: List[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, check=check)


def stop_container() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER], text=True, capture_output=True)


def image_digest(image: str) -> str:
    cp = command(["docker", "image", "inspect", image, "--format", "{{index .RepoDigests 0}}"], check=False)
    value = cp.stdout.strip()
    if value:
        return value
    cp = command(["docker", "image", "inspect", image, "--format", "{{.Id}}"])
    return cp.stdout.strip()


def list_devices(image: str) -> str:
    cp = command([
        "docker", "run", "--rm",
        "--entrypoint", "/app/llama-server",
        image,
        "--list-devices",
    ], check=False)
    output = (cp.stdout or "") + "\n" + (cp.stderr or "")
    if cp.returncode != 0:
        raise RuntimeError(f"optimized image --list-devices failed:\n{output}")
    if "blas" not in output.lower():
        raise RuntimeError(
            "BLAS device is not visible in optimized image; refusing fallback.\n"
            + output
        )
    return output


def server_command(case: Dict[str, Any], image: str, cache_dir: Path) -> List[str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
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
        "-m", ORNITH_MODEL_PATH,
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
        "--cache-prompt",
        "--cache-reuse", str(CACHE_REUSE_MIN),
        "--cache-ram", "4096",
        "--no-context-shift",
        "--threads-http", "1",
        "--no-webui",
        "--spec-type", "ngram-mod",
        "--spec-ngram-mod-n-match", "24",
        "--spec-ngram-mod-n-min", "48",
        "--spec-ngram-mod-n-max", "64",
    ]


def wait_health(timeout_s: int = 600) -> None:
    adapter = h.HTTPAdapter(f"http://127.0.0.1:{PORT}", "llama.cpp", timeout_s=60)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if adapter.health().get("healthy"):
            return
        time.sleep(3)
    logs = command(["docker", "logs", CONTAINER], check=False)
    raise RuntimeError(
        "optimized server health timeout\n"
        + (logs.stdout or "")
        + "\n"
        + (logs.stderr or "")
    )


def request_body(system_prompt: str, content: str, max_tokens: int) -> Dict[str, Any]:
    return {
        "model": ORNITH_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }


def token_count(
    adapter: h.HTTPAdapter,
    system_prompt: str,
    content: str,
) -> Tuple[int, Dict[str, Any]]:
    receipt = adapter.receipt(request_body(system_prompt, content, 1))
    count = receipt.get("prompt_tokens")
    if type(count) is not int or count < 1:
        raise RuntimeError(f"invalid tokenizer receipt: {receipt}")
    return count, receipt


def calibrate_content(
    adapter: h.HTTPAdapter,
    system_prompt: str,
    base_unit: str,
    target_min: int,
    target_max: int,
    *,
    prefix: str = "",
) -> Tuple[str, int, Dict[str, Any]]:
    def render(units: int, pads: int = 0) -> str:
        return prefix + (base_unit * units) + (FINE_PAD_UNIT * pads)

    low = 0
    high = 1
    while True:
        content = render(high)
        count, _ = token_count(adapter, system_prompt, content)
        if count > target_max:
            break
        low = high
        high *= 2
        if high > 4096:
            raise RuntimeError("unable to bracket token target")

    best_content = ""
    best_count = 0
    best_receipt: Dict[str, Any] = {}
    lo, hi = low, high - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        content = render(mid)
        count, receipt = token_count(adapter, system_prompt, content)
        if count <= target_max:
            best_content = content
            best_count = count
            best_receipt = receipt
            lo = mid + 1
        else:
            hi = mid - 1

    if not best_content:
        content = render(0)
        best_count, best_receipt = token_count(adapter, system_prompt, content)
        best_content = content

    if best_count < target_min:
        for pads in range(1, 8193):
            content = best_content + (FINE_PAD_UNIT * pads)
            count, receipt = token_count(adapter, system_prompt, content)
            if count < target_min:
                continue
            if count > target_max:
                raise RuntimeError(
                    f"calibration jumped over target: count={count}, "
                    f"target={target_min}..{target_max}"
                )
            best_content = content
            best_count = count
            best_receipt = receipt
            break

    if not (target_min <= best_count <= target_max):
        raise RuntimeError(
            f"calibration failed: count={best_count}, target={target_min}..{target_max}"
        )

    return best_content, best_count, best_receipt


def backend_logs() -> str:
    cp = command(["docker", "logs", CONTAINER], check=False)
    return (cp.stdout or "") + "\n" + (cp.stderr or "")


def require_openvino_runtime(log_text: str) -> None:
    if "openvino" not in log_text.lower():
        raise RuntimeError(
            "OpenVINO backend was not observed in runtime logs; "
            "refusing to accept a native-GGML fallback result."
        )


def select_winner(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    peak = max(r["prompt_eval_tps"] for r in results)
    floor = peak * (1.0 - TIE_TOLERANCE)
    tied = [r for r in results if r["prompt_eval_tps"] >= floor]
    return min(tied, key=lambda r: (r["b"], r["ub"]))


def run_case(
    case: Dict[str, Any],
    image: str,
    device_evidence: str,
) -> Dict[str, Any]:
    raw = ROOT / "results/raw" / case["exp_id"]
    if raw.exists():
        raise RuntimeError(f"immutable experiment directory already exists: {raw}")

    cache_dir = ROOT / "results/runtime-cache/wbs69" / case["case"].lower()
    raw.mkdir(parents=True, exist_ok=False)
    (raw / "runtime").mkdir()
    h.save(raw / "config.json", future_config({
        "experiment_id": case["exp_id"],
        "measured_repetitions": 1,
        "warmup_count": 0,
        "case": case["case"],
        "b": case["b"],
        "ub": case["ub"],
        "measured_prompt_target": f"{TARGET_MIN}..{TARGET_MAX}",
        "common_prefix_target": f"{PREFIX_MIN}..{PREFIX_MAX}",
        "setup_requests": 2,
        "setup_requests_measured": False,
        "optimization_stack": [
            "OpenBLAS build",
            "GGML_LTO=ON",
            "GGML_CPU_ALL_VARIANTS=ON",
            "Flash Attention forced on",
            "mmap + lazy-mode off + server warmup",
            "prompt cache + cache reuse",
            "weight repack",
            "strict batch affinity",
            "medium priority",
            "polling",
        ],
    }))

    stop_container()
    time.sleep(1)
    cp = command(server_command(case, image, cache_dir), check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"failed to start optimized server: {cp.stderr}")

    try:
        wait_health()
        adapter = h.HTTPAdapter(
            f"http://127.0.0.1:{PORT}",
            "llama.cpp",
            timeout_s=1800,
        )

        warm_content, warm_tokens, warm_receipt = calibrate_content(
            adapter,
            WARMUP_SYSTEM,
            WARMUP_UNIT,
            TARGET_MIN,
            TARGET_MAX,
        )
        warm_res = adapter.call(
            "/v1/chat/completions",
            body=request_body(WARMUP_SYSTEM, warm_content, 1),
        )
        h.save(raw / "setup-compile-warmup.json", {
            "measured": False,
            "prompt_tokens": warm_tokens,
            "tokenizer_receipt": warm_receipt,
            "response_usage": warm_res.get("usage"),
            "response_timings": warm_res.get("timings"),
        })

        logs_after_warmup = backend_logs()
        h.save(raw / "runtime/backend-log.json", {
            "list_devices": device_evidence,
            "server_log": logs_after_warmup,
        })

        prefix_content, prefix_tokens, prefix_receipt = calibrate_content(
            adapter,
            SYSTEM_PROMPT,
            PREFIX_UNIT,
            PREFIX_MIN,
            PREFIX_MAX,
        )
        prefix_hash = h.sha(h.canon([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prefix_content},
        ]))
        prime_res = adapter.call(
            "/v1/chat/completions",
            body=request_body(SYSTEM_PROMPT, prefix_content, 1),
        )
        h.save(raw / "setup-prefix-prime.json", {
            "measured": False,
            "prompt_tokens": prefix_tokens,
            "prefix_messages_sha256": prefix_hash,
            "tokenizer_receipt": prefix_receipt,
            "response_usage": prime_res.get("usage"),
            "response_timings": prime_res.get("timings"),
        })

        measured_content, calibrated_tokens, measured_receipt = calibrate_content(
            adapter,
            SYSTEM_PROMPT,
            FRESH_UNIT,
            TARGET_MIN,
            TARGET_MAX,
            prefix=prefix_content,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": measured_content},
        ]
        prompt_hash = h.sha(h.canon(messages))
        body = {
            "model": ORNITH_MODEL_NAME,
            "messages": messages,
            "max_tokens": COMPLETION_TOKENS,
            "temperature": 0.0,
        }

        t0 = time.time()
        res = adapter.call("/v1/chat/completions", body=body)
        wall_s = time.time() - t0

        usage = res.get("usage", {})
        timings = res.get("timings", {})
        prompt_tokens = usage.get("prompt_tokens", timings.get("prompt_n"))
        completion_tokens = usage.get("completion_tokens", timings.get("predicted_n"))
        cache_n = timings.get("cache_n", 0)

        if type(prompt_tokens) is not int or not (TARGET_MIN <= prompt_tokens <= TARGET_MAX):
            raise RuntimeError(f"measured prompt is not true-4K: {prompt_tokens}")
        if prompt_tokens != calibrated_tokens:
            raise RuntimeError(
                f"tokenizer drift: receipt={calibrated_tokens}, measured={prompt_tokens}"
            )
        if type(cache_n) not in (int, float) or cache_n < CACHE_HIT_ACCEPT_MIN:
            raise RuntimeError(
                f"prompt-cache optimization not proven: cache_n={cache_n}, "
                f"required>={CACHE_HIT_ACCEPT_MIN}"
            )

        prompt_tps = timings.get("prompt_per_second")
        if not isinstance(prompt_tps, (int, float)) or prompt_tps <= 0:
            prompt_ms = timings.get("prompt_ms")
            prompt_n = timings.get("prompt_n")
            if not isinstance(prompt_ms, (int, float)) or not isinstance(prompt_n, (int, float)):
                raise RuntimeError(f"missing prompt timing evidence: {timings}")
            prompt_tps = prompt_n / (prompt_ms / 1000.0)

        metrics = {
            "experiment_id": case["exp_id"],
            "case": case["case"],
            "b": case["b"],
            "ub": case["ub"],
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cache_n": cache_n,
            "common_prefix_prompt_tokens": prefix_tokens,
            "prompt_eval_tps": prompt_tps,
            "ttft_ms": timings.get("prompt_ms"),
            "decode_tps": timings.get("predicted_per_second"),
            "wall_s": wall_s,
            "prompt_messages_sha256": prompt_hash,
            "prefix_messages_sha256": prefix_hash,
            "tokenizer_receipt": measured_receipt,
            "timings": timings,
            "measured_at_utc": h.utc(),
        }
        h.save(raw / "metrics.json", metrics)
        h.save(raw / "completion.json", {
            "verdict": "PASS",
            "completed_at_utc": h.utc(),
            "response": res,
        })
        h.save(raw / "runtime/progress.json", {
            "phase": "done",
            "updated_at_utc": h.utc(),
        })
        return metrics

    except Exception as exc:
        h.save(raw / "runtime/progress.json", {
            "phase": "failed",
            "error": repr(exc),
            "updated_at_utc": h.utc(),
        })
        raise
    finally:
        stop_container()
        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="run exactly four measured A/B/C/D cases")
    parser.add_argument("--selected-image", default=DEFAULT_IMAGE)
    args = parser.parse_args()

    if not args.run:
        print("Safety stop: pass --run to execute WBS 6.9 (exactly 4 measured cases).")
        return

    hostname = socket.gethostname().split(".")[0]
    if hostname != "p520-llm":
        raise RuntimeError(f"WBS 6.9 requires p520-llm host, got {hostname}")

    lock_path = ROOT / "results/experiment.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)

        summary_path = ROOT / "results/raw/WBS69-OPTBLAS-4K-SCREENING-SUMMARY.json"
        winner_path = ROOT / "results/raw/WBS69-OPTBLAS-4K-WINNER.json"
        preflight_path = ROOT / "results/raw/WBS69-OPTBLAS-4K-PREFLIGHT.json"
        if summary_path.exists() or winner_path.exists():
            raise RuntimeError("WBS 6.9 summary/winner already exists; refusing overwrite")

        device_evidence = list_devices(args.selected_image)
        h.save(preflight_path, {
            "at_utc": h.utc(),
            "image": args.selected_image,
            "image_digest": image_digest(args.selected_image),
            "blas_device_visible": True,
            "list_devices": device_evidence,
            "measured_requests": 0,
        })

        results: List[Dict[str, Any]] = []
        for case in CASES:
            results.append(run_case(case, args.selected_image, device_evidence))

        token_counts = {r["prompt_tokens"] for r in results}
        prompt_hashes = {r["prompt_messages_sha256"] for r in results}
        prefix_hashes = {r["prefix_messages_sha256"] for r in results}
        if len(token_counts) != 1:
            raise RuntimeError(f"A-D prompt token counts differ: {token_counts}")
        if len(prompt_hashes) != 1:
            raise RuntimeError("A-D measured prompt payloads differ")
        if len(prefix_hashes) != 1:
            raise RuntimeError("A-D cache-priming prefixes differ")

        winner = select_winner(results)
        peak = max(r["prompt_eval_tps"] for r in results)
        floor = peak * (1.0 - TIE_TOLERANCE)
        tied_cases = [r["case"] for r in results if r["prompt_eval_tps"] >= floor]

        h.save(summary_path, {
            "wbs": "6.9",
            "stack": "combined-optimized-cpu-serving",
            "measured_request_count": 4,
            "prompt_tokens": next(iter(token_counts)),
            "identical_prompt_messages_sha256": next(iter(prompt_hashes)),
            "identical_prefix_messages_sha256": next(iter(prefix_hashes)),
            "cases": results,
            "completed_at_utc": h.utc(),
        })
        h.save(winner_path, {
            "wbs": "6.9",
            "selection_policy": "within_2pct_of_peak_then_smallest_b_ub",
            "peak_prompt_eval_tps": peak,
            "tie_floor_prompt_eval_tps": floor,
            "tied_cases": tied_cases,
            "winner_case": winner["case"],
            "winner_b": winner["b"],
            "winner_ub": winner["ub"],
            "winner_prompt_eval_tps": winner["prompt_eval_tps"],
            "selected_at_utc": h.utc(),
        })

        print("\nWBS 6.9 optimized true-4K results")
        print("Case   b     ub    prompt  cache_n  prompt_tps  wall_s")
        for r in results:
            print(
                f"{r['case']:<4} {r['b']:>5} {r['ub']:>6} "
                f"{r['prompt_tokens']:>7} {r['cache_n']:>8} "
                f"{r['prompt_eval_tps']:>10.2f} {r['wall_s']:>7.2f}"
            )
        print(
            f"Winner: {winner['case']} "
            f"(b={winner['b']}, ub={winner['ub']}); tied={tied_cases}"
        )


if __name__ == "__main__":
    main()
