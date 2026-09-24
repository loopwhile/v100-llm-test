#!/usr/bin/env python3
"""Bounded 1Cat-vLLM diagnostic runner for realistic 128K context evaluation.

This script executes exactly one measured inference request on Qwen3.8-27B
using a diversified realistic multi-file codebase context to evaluate whether
128K output integrity issues persist on realistic code workloads.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time

import bench_harness as h
import runtime_launcher as launcher
from measurement_policy import future_config

ROOT = Path(__file__).resolve().parents[1]


def command(args, timeout=30, env=None):
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
        env=env,
    ).stdout


def checkpoint(raw, phase, **extra):
    path = raw / "runtime/progress.json"
    state = json.loads(path.read_text()) if path.exists() else {}
    h.save(path, state | dict(phase=phase, updated_at_utc=h.utc(), **extra))


def metadata_receipt(identity):
    root = Path(identity["path"])
    files = {}
    for name in (
        "config.json",
        "hf_quant_config.json",
        "model.safetensors.index.json",
        "tokenizer_config.json",
        "chat_template.jinja",
    ):
        path = root / name
        if path.is_file():
            files[name] = h.sha(path.read_bytes())
    return {
        "path": str(root),
        "repository": identity.get("repository"),
        "revision": identity.get("revision"),
        "weight_quant": identity.get("weight_quant"),
        "metadata_sha256": files,
        "note": "Large model tensors are identified by pinned repository/revision; selected local metadata files are hashed as a host receipt.",
    }


def measure(raw, workload_path: Path):
    config = json.loads((raw / "runtime/planned-config.json").read_text())
    adapter = h.HTTPAdapter(config["endpoint"], "1Cat-vLLM", timeout_s=1800)
    checkpoint(raw, "running", step="loading_calibrated_workload", workload_path=str(workload_path))
    
    workload = json.loads(workload_path.read_text(encoding="utf-8"))
    
    checkpoint(
        raw,
        "running",
        step="measured_request",
        workload_sha256=h.sha(h.canon(workload)),
    )
    verdict = h.run_batch(raw, config, workload, adapter)
    checkpoint(raw, "results_saved", step="measurement_complete", verdict=verdict)


def run(args):
    if socket.gethostname().split(".")[0] != "p520-llm":
        raise RuntimeError("requires p520-llm")
    lock_path = ROOT / "results/experiment.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(args)


def run_locked(args):
    raw = ROOT / "results/raw" / args.experiment_id
    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / "runtime"
    runtime.mkdir()

    plan = launcher.build_plan(
        ROOT, args.model, "STOCK", 1, "tp2-shared", args.port
    )
    if not plan.get("supported_for_planning"):
        raise RuntimeError("unsupported plan: " + plan.get("reason", "unknown reason"))

    cmd = list(plan["commands"][0])
    cmd_env = os.environ.copy()
    cmd_env.update(
        {k: str(v) for k, v in (plan.get("command_environments") or [{}])[0].items()}
    )

    thinking = True
    reasoning_effort = "medium"
    sampling = {"temperature": 0.7, "top_p": 0.8, "seed": 520}

    chat_template = (
        f"HF tokenizer chat template; enable_thinking=true; reasoning_effort=medium; temperature=0.7"
    )
    template_kwargs = {"enable_thinking": True, "reasoning_effort": "medium"}

    config = future_config(
        plan
        | dict(
            experiment_id=args.experiment_id,
            launch_command=shlex.join(cmd),
            backend_variant="stock",
            context_tokens=131072,
            context_test=True,
            min_context_utilization=0.98,
            prefix_cache_lane="cold-independent",
            chat_template=chat_template,
            tool_parser="none",
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            sampling=sampling,
            chat_template_kwargs=template_kwargs,
            endpoint=plan["endpoints"][0],
            notes=(
                "Root-cause diagnostic run: realistic diversified 128K context workload; "
                "one measured request only after healthy startup; no synthetic repetition; "
                "2048 output reserve, minimum 256."
            ),
        )
    )

    h.validate(config)
    h.save(runtime / "plan.json", plan)
    h.save(runtime / "planned-config.json", config)
    checkpoint(
        raw,
        "prepared",
        experiment_id=args.experiment_id,
        model=args.model,
        lane="STOCK",
        host=socket.gethostname(),
        remote_path=str(raw),
        started_at_utc=h.utc(),
        boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        pid=os.getpid(),
        process_start_ticks=Path("/proc/self/stat").read_text().split()[21],
        measurement_timeout_s=2400,
        startup_timeout_s=900,
        scope="Root-cause diagnostic: 1Cat STOCK Qwen3.8 realistic diversified 128K context test",
        cleanup_policy="owned process group only",
        planned_config_sha256=h.sha(h.canon(config)),
        source_sha256={
            str(p.relative_to(ROOT)): h.sha(p.read_bytes())
            for p in sorted((ROOT / "scripts").glob("*.py"))
        },
    )

    server = None
    stop = threading.Event()
    collector = None
    verdict = "INCONCLUSIVE"
    error = None
    exit_code = 1

    def telemetry():
        with (runtime / "gpu-telemetry.jsonl").open("x") as stream:
            while not stop.is_set():
                try:
                    value = command(
                        [
                            "nvidia-smi",
                            "--query-gpu=index,uuid,memory.used,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu",
                            "--format=csv,noheader,nounits",
                        ],
                        5,
                    )
                    stream.write(json.dumps(dict(at_utc=h.utc(), csv=value)) + "\n")
                    stream.flush()
                except Exception as exc:
                    stream.write(
                        json.dumps(dict(at_utc=h.utc(), error=str(exc))) + "\n"
                    )
                    stream.flush()
                stop.wait(2)

    try:
        inventory = command(["nvidia-smi"]) + "\n" + command(["ss", "-ltnp"])
        (runtime / "host-before.txt").write_text(inventory)
        if command(
            [
                "nvidia-smi",
                "--query-compute-apps=pid",
                "--format=csv,noheader",
            ]
        ).strip():
            raise RuntimeError("GPU has an existing compute process; refusing launch")

        checkpoint(raw, "starting_server")

        log = (runtime / "server-0.log").open("wb")
        collector = threading.Thread(target=telemetry, daemon=True)
        collector.start()

        server = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(ROOT),
            env=cmd_env,
            start_new_session=True,
        )
        h.save(
            runtime / "server-process.json",
            {
                "pid": server.pid,
                "pgid": os.getpgid(server.pid),
                "started_at_utc": h.utc(),
                "command": cmd,
            },
        )

        adapter = h.HTTPAdapter(config["endpoint"], "1Cat-vLLM", timeout_s=1800)
        deadline = time.monotonic() + 900
        checkpoint(
            raw,
            "polling_health",
            pid=server.pid,
            poll_interval_s=2,
            startup_timeout_s=900,
        )
        healthy = False
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(
                    f"server exited prematurely with code {server.returncode}"
                )
            try:
                res = adapter.health()
                if res.get("healthy"):
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(2)

        if not healthy:
            raise TimeoutError("server failed to become healthy within 900s")

        checkpoint(raw, "healthy", pid=server.pid)
        workload_path = Path(args.workload)
        if not workload_path.is_absolute():
            workload_path = ROOT / workload_path
        measure(raw, workload_path)
        verdict = json.loads((raw / "completion.json").read_text())["verdict"]
        exit_code = 0 if verdict == "PASS" else 2

    except Exception as exc:
        error = exc
        verdict = h.classify(exc)
        exit_code = 1
        checkpoint(raw, "failed", error=str(exc), verdict=verdict)
    finally:
        stop.set()
        if collector:
            collector.join(timeout=5)
        clean_state = None
        clean_error = None
        server_post_health = None
        if server is not None:
            try:
                server_post_health = (
                    h.HTTPAdapter(config["endpoint"], "1Cat-vLLM", timeout_s=30).health()
                )
            except Exception as exc:
                server_post_health = {"healthy": False, "error": str(exc), "at_utc": h.utc()}

            pgid = os.getpgid(server.pid) if server.poll() is None else None
            if pgid is not None:
                try:
                    os.killpg(pgid, signal.SIGTERM)
                    server.wait(timeout=30)
                except Exception:
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                        server.wait(timeout=10)
                    except Exception as kill_exc:
                        clean_error = str(kill_exc)
            clean_state = "cleaned" if server.poll() is not None else "failed"

        time.sleep(5)
        remaining = command(
            [
                "nvidia-smi",
                "--query-compute-apps=pid",
                "--format=csv,noheader",
            ]
        ).strip()
        ports = command(["ss", "-ltnp"])
        clean_ok = clean_state == "cleaned" and not remaining
        if not clean_ok and clean_error is None:
            clean_error = f"residual compute processes remain: {remaining}" if remaining else "server failed to terminate"

        h.save(
            raw / "completion.json",
            {
                "experiment_id": args.experiment_id,
                "completed_at_utc": h.utc(),
                "verdict": verdict,
                "error": str(error) if error else None,
                "exit_code": exit_code,
                "server_post_health": server_post_health,
                "cleanup": {
                    "state": "cleaned" if clean_ok else "failed",
                    "error": clean_error,
                    "residual_compute_pids": [p for p in remaining.splitlines() if p],
                    "port_state": ports,
                },
                "metadata_receipt": metadata_receipt(config["model_identity"]),
            },
        )
        (runtime / "host-after.txt").write_text(
            command(["nvidia-smi"]) + "\n" + ports
        )
        checkpoint(
            raw,
            "completed",
            verdict=verdict,
            exit_code=exit_code,
            cleanup_ok=clean_ok,
        )

    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="One measured 1Cat-vLLM diagnostic run with realistic 128K context"
    )
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--model", default="qwen3.8-27b")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--workload", default="workloads/diagnostic/v100_q38_realistic_128k.json")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
