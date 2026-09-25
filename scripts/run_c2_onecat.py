#!/usr/bin/env python3
"""One bounded 1Cat-vLLM STOCK C2 128K run for WBS 3.2.x.

The server-startup phase is the runtime compatibility gate. A measured C2 batch
(two independent 128K requests) is sent only after the pinned artifact/runtime plan
is healthy. This script never retries, changes KV/spec/topology, or launches another WBS item.
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
import build_128k_workload as w
import runtime_launcher as launcher
from measurement_policy import RETRY_REASONS, future_config

ROOT = Path(__file__).resolve().parents[1]
WORKLOAD_MANIFEST = ROOT / "workloads/concurrency/v2.json"
SEMANTIC_ORACLE = ROOT / "workloads/concurrency/v2-ground-truth.json"

MODEL_WBS = {
    "qwen3.8-27b": "3.2.1",
    "ornith-1.5-9b": "3.2.2",
    "ornith-1.5-35b-a3b": "3.2.3",
}


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


def measure(raw):
    config = json.loads((raw / "runtime/planned-config.json").read_text())
    adapter = h.HTTPAdapter(config["endpoint"], "1Cat-vLLM", timeout_s=2400)
    checkpoint(raw, "running", step="materializing_live_tokenizer_workload")
    workload = w.build(
        w.load_manifest(WORKLOAD_MANIFEST),
        adapter,
        config["model"],
        thinking=config.get("thinking", False),
        chat_template_kwargs=config.get("chat_template_kwargs"),
        sampling=config.get("sampling"),
    )
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
    wbs = MODEL_WBS[args.model]
    raw = ROOT / "results/raw" / args.experiment_id
    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / "runtime"
    runtime.mkdir()

    plan = launcher.build_plan(
        ROOT, args.model, "STOCK", 2, "tp2-shared", args.port
    )
    if not plan.get("supported_for_planning"):
        raise RuntimeError("unsupported plan: " + plan.get("reason", "unknown reason"))

    cmd = list(plan["commands"][0])
    cmd_env = os.environ.copy()
    cmd_env.update(
        {k: str(v) for k, v in (plan.get("command_environments") or [{}])[0].items()}
    )

    if args.model == "qwen3.8-27b":
        if "--kv-cache-dtype" in cmd:
            idx = cmd.index("--kv-cache-dtype")
            cmd[idx + 1] = "fp8_e4m3"
        else:
            cmd.extend(["--kv-cache-dtype", "fp8_e4m3"])

        if "--max-num-batched-tokens" in cmd:
            idx = cmd.index("--max-num-batched-tokens")
            cmd[idx + 1] = "2048"
        else:
            cmd.extend(["--max-num-batched-tokens", "2048"])

        if "--reasoning-parser" not in cmd:
            cmd.extend(["--reasoning-parser", "qwen3"])
        if "--tool-call-parser" not in cmd:
            cmd.extend(["--tool-call-parser", "qwen3_coder"])
        if "--default-chat-template-kwargs" not in cmd:
            cmd.extend(["--default-chat-template-kwargs", '{"enable_thinking": false}'])

        cmd_env["VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL"] = "0"
        cmd_env["VLLM_SM70_GDN_DECODE_FLASHQLA"] = "0"
        cmd_env["VLLM_FLASH_V100_DECODE_PARTITION_SIZE"] = "256"

        thinking = False
        reasoning_effort = None
        sampling = {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "presence_penalty": 0.15,
            "frequency_penalty": 0.05,
            "seed": 38,
        }
        chat_template = (
            "HF tokenizer chat template; enable_thinking=false; reasoning-parser=qwen3; temperature=1.0; top_k=20; presence_penalty=0.15"
        )
        template_kwargs = {"enable_thinking": False}
        tool_parser = "qwen3_coder"
        kv_cache = "fp8_e4m3"
    else:
        tool_parser = "none"
        kv_cache = plan.get("kv_cache")
        thinking = bool(args.thinking) if getattr(args, "thinking", None) is not None else False
        reasoning_effort = args.reasoning_effort if thinking else None
        sampling = None
        chat_template = (
            f"HF tokenizer chat template; enable_thinking={'true' if thinking else 'false'}"
            + (f"; reasoning_effort={reasoning_effort}" if reasoning_effort else "")
        )
        template_kwargs = (
            {"enable_thinking": thinking, "reasoning_effort": reasoning_effort}
            if reasoning_effort
            else {"enable_thinking": thinking}
        )

    config = future_config(
        plan
        | dict(
            experiment_id=args.experiment_id,
            launch_command=shlex.join(cmd),
            backend_variant="stock",
            kv_cache=kv_cache,
            concurrency=2,
            context_tokens=131072,
            context_test=True,
            min_context_utilization=0.99,
            prefix_cache_lane="cold-independent",
            chat_template=chat_template,
            tool_parser=tool_parser,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            sampling=sampling,
            chat_template_kwargs=template_kwargs,
            endpoint=plan["endpoints"][0],
            notes=(
                f"WBS {wbs}; two concurrent independent 128K requests (C2); "
                "server startup is the compatibility gate; one measured C2 batch after healthy startup; "
                "authoritative workload=concurrency/v2 with pre-registered semantic oracle; "
                "2048 output reserve, minimum 256 per request."
            ),
        )
    )
    if args.retry_of:
        config.update(
            retry_of=args.retry_of,
            retry_reason=args.retry_reason,
            retry_evidence=args.retry_evidence,
        )
        config = future_config(config)

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
        measurement_timeout_s=3600,
        startup_timeout_s=900,
        scope=f"WBS {wbs}: 1Cat STOCK compatibility gate + one C2 128K batch (concurrency=2)",
        cleanup_policy="owned process group only",
        planned_config_sha256=h.sha(h.canon(config)),
        launch_command_sha256=h.sha(config["launch_command"].encode()),
        workload_manifest_sha256=h.sha(WORKLOAD_MANIFEST.read_bytes()),
        semantic_oracle_sha256=h.sha(SEMANTIC_ORACLE.read_bytes()),
        runtime_hook_sha256=h.sha((ROOT / "scripts/runtime_hooks/sitecustomize.py").read_bytes()),
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

        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", args.port))

        check = launcher.preflight(plan)
        h.save(runtime / "preflight.json", check)
        if not check["pass"]:
            raise RuntimeError("runtime preflight failed")

        h.save(runtime / "artifact-check.json", metadata_receipt(plan["model_identity"]))

        py = os.environ["V100_1CAT_PYTHON"]
        version_code = (
            "import importlib.metadata as m\n"
            "for n in ('1cat-vllm','1cat_vllm'):\n"
            " try:\n  print(m.version(n)); break\n"
            " except m.PackageNotFoundError: pass\n"
            "else: raise SystemExit(2)"
        )
        (runtime / "runtime-version.txt").write_text(
            command([py, "-c", version_code], 60, env=cmd_env)
        )

        collector = threading.Thread(target=telemetry)
        collector.start()
        checkpoint(raw, "running", step="server_startup_compatibility_gate")
        with (runtime / "server-0.log").open("x") as log:
            server = subprocess.Popen(
                cmd,
                env=cmd_env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        (runtime / "server.pid").write_text(str(server.pid) + "\n")
        checkpoint(raw, "running", server_pid=server.pid,
                   server_start_ticks=Path(f"/proc/{server.pid}/stat").read_text().split()[21])

        adapter = h.HTTPAdapter(config["endpoint"], "1Cat-vLLM", timeout_s=5)
        deadline = time.monotonic() + 900
        while not adapter.health()["healthy"]:
            if server.poll() is not None:
                log_text = (runtime / "server-0.log").read_text(
                    errors="replace"
                ).lower()
                verdict = (
                    "FAIL_OOM"
                    if any(
                        x in log_text
                        for x in (
                            "out of memory",
                            "cuda error: out of memory",
                            "torch.outofmemoryerror",
                        )
                    )
                    else "FAIL_STARTUP"
                )
                raise RuntimeError("server exited during compatibility startup")
            if time.monotonic() >= deadline:
                verdict = "FAIL_TIMEOUT"
                raise TimeoutError("startup compatibility deadline expired")
            time.sleep(2)

        checkpoint(raw, "running", step="server_ready_compatibility_pass")
        with (runtime / "measurement.log").open("x") as log:
            child = subprocess.run(
                [sys.executable, __file__, "--worker", str(raw)],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600,
            )
        if child.returncode:
            raise RuntimeError("measurement worker failed; see measurement.log")

        verdict = json.loads((raw / "completion.json").read_text())["verdict"]
        exit_code = 0
    except subprocess.TimeoutExpired as exc:
        verdict = "FAIL_TIMEOUT"
        error = str(exc)
    except Exception as exc:
        error = str(exc)
    finally:
        if not (raw / "completion.json").exists():
            if not (raw / "config.json").exists():
                h.save(raw / "config.json", config)
                h.save(
                    raw / "identity.json",
                    dict(
                        config_sha256=h.sha(h.canon(config)),
                        created_at_utc=h.utc(),
                    ),
                )
            h.save(
                raw / "metrics.json",
                dict(verdict=verdict, c2_resident=False, c2_active=False, queue_only=False, error=error),
            )
            h.save(
                raw / "completion.json",
                dict(
                    experiment_id=args.experiment_id,
                    verdict=verdict,
                    completed_at_utc=h.utc(),
                    error=error,
                ),
            )

        cleanup = {"process_group_stopped": False}
        if server is not None:
            try:
                if server.poll() is None:
                    os.killpg(server.pid, signal.SIGTERM)
                    try:
                        server.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        os.killpg(server.pid, signal.SIGKILL)
                        server.wait(timeout=30)
                cleanup["process_group_stopped"] = True
                cleanup["server_exit_code"] = server.returncode
            except Exception as exc:
                cleanup["error"] = str(exc)

        stop.set()
        if collector:
            collector.join(timeout=10)

        h.save(runtime / "cleanup.json", cleanup)
        try:
            (runtime / "host-after.txt").write_text(command(["nvidia-smi"]))
        except Exception as exc:
            (runtime / "host-after.txt").write_text("inventory failed: " + str(exc))

        checkpoint(
            raw,
            "results_saved",
            step="finished",
            verdict=verdict,
            error=error,
            exit_code=exit_code,
        )
        h.save(
            runtime / "exit.json",
            dict(exit_code=exit_code, verdict=verdict, completed_at_utc=h.utc()),
        )
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id")
    parser.add_argument("--retry-of")
    parser.add_argument("--retry-evidence")
    parser.add_argument("--retry-reason", choices=sorted(RETRY_REASONS), default="configuration_fix")
    parser.add_argument("--model", choices=sorted(MODEL_WBS))
    parser.add_argument("--thinking", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "xhigh"], default=None)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()

    if args.worker:
        measure(args.worker)
    else:
        if args.retry_of and not args.retry_evidence:
            parser.error("--retry-of requires --retry-evidence")
        if not args.experiment_id or not args.model:
            parser.error("--experiment-id and --model are required")
        if not __import__("re").fullmatch(
            r"EXP-V100-[A-Z0-9][A-Z0-9-]*", args.experiment_id
        ):
            parser.error("invalid experiment ID")
        raise SystemExit(run(args))
