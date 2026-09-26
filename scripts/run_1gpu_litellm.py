#!/usr/bin/env python3
"""Bounded Ornith 1.5 9B 1GPUx2 + LiteLLM runner for WBS 4.

Runs exactly one model/lane/concurrency combination for the independent topology:
two single-GPU servers (GPU0/GPU1) behind a mandatory LiteLLM gateway.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
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
from measurement_policy import future_config

ROOT = Path(__file__).resolve().parents[1]
C1_WORKLOAD_MANIFEST = ROOT / "workloads/capacity/v1.json"
C2_WORKLOAD_MANIFEST = ROOT / "workloads/concurrency/v2.json"
C2_SEMANTIC_ORACLE = ROOT / "workloads/concurrency/v2-ground-truth.json"

LANE_WBS = {
    ("TARGET", 1): "4.1.1",
    ("TARGET", 2): "4.1.2",
    ("NGRAM", 1): "4.1.3",
    ("NGRAM", 2): "4.1.4",
    ("MTP", 1): "4.1.5",
    ("MTP", 2): "4.1.6",
    ("MTP_NGRAM", 1): "4.1.7",
    ("MTP_NGRAM", 2): "4.1.8",
    ("STOCK", 1): "4.2.1",
    ("STOCK", 2): "4.2.2",
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


def measure(raw):
    config = json.loads((raw / "runtime/planned-config.json").read_text())
    timeout_s = 3600 if config.get("concurrency") == 2 else 1800
    adapter = h.make_plan_adapter(config, timeout_s=timeout_s)

    if config.get("concurrency") == 1:
        checkpoint(raw, "running", step="materializing_live_tokenizer_workload")
        manifest = w.load_manifest(C1_WORKLOAD_MANIFEST)
        workload = w.build(
            manifest,
            adapter,
            config["model"],
            thinking=config.get("thinking", False),
            chat_template_kwargs=config.get("chat_template_kwargs"),
            sampling=config.get("sampling"),
        )
    else:
        checkpoint(raw, "running", step="materializing_authoritative_workload_v2")
        manifest = w.load_manifest(C2_WORKLOAD_MANIFEST)
        workload = w.build(
            manifest,
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
    wbs = LANE_WBS.get((args.lane, args.concurrency), "4.x")
    raw = ROOT / "results/raw" / args.experiment_id
    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / "runtime"
    runtime.mkdir()

    plan = launcher.build_plan(
        ROOT,
        args.model,
        args.lane,
        args.concurrency,
        "1gpu-x2-independent",
        args.port,
        args.gateway_port,
    )
    if not plan.get("supported_for_planning"):
        raise RuntimeError("unsupported plan: " + plan.get("reason", "unknown reason"))

    # Prepare server commands and container labels/cids
    backend_cids = []
    backend_cmds = []
    is_docker_backends = plan["runtime"] == "llama.cpp"

    for i, cmd in enumerate(plan["commands"]):
        cmd_copy = list(cmd)
        if is_docker_backends:
            name_idx = cmd_copy.index("--name") + 1
            cmd_copy[name_idx] = f"{args.experiment_id.lower()}-backend-{i}"
            cidfile = runtime / f"container-{i}.cid"
            backend_cids.append(cidfile)
            cmd_copy[2:2] = [
                "--cidfile",
                str(cidfile),
                "--label",
                f"experiment={args.experiment_id}",
            ]
        backend_cmds.append(cmd_copy)

    # Prepare gateway command
    gateway_cid = runtime / "container-gateway.cid"
    gateway_config_path = runtime / "litellm-config.yaml"
    with gateway_config_path.open("w", encoding="utf-8") as stream:
        json.dump(plan["gateway"]["config"], stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    gateway_cmd = [
        x.replace("{LITELLM_CONFIG}", str(gateway_config_path))
        for x in plan["gateway"]["command"]
    ]
    gw_name_idx = gateway_cmd.index("--name") + 1
    gateway_cmd[gw_name_idx] = f"{args.experiment_id.lower()}-gateway"
    gateway_cmd[2:2] = [
        "--cidfile",
        str(gateway_cid),
        "--label",
        f"experiment={args.experiment_id}",
    ]

    config = future_config(
        plan
        | dict(
            experiment_id=args.experiment_id,
            launch_command="; ".join(shlex.join(c) for c in backend_cmds + [gateway_cmd]),
            backend_variant="stock",
            context_tokens=131072,
            context_test=True,
            min_context_utilization=0.99,
            prefix_cache_lane="cold-independent",
            chat_template=(
                "embedded GGUF Jinja; enable_thinking=false"
                if plan["runtime"] == "llama.cpp"
                else "default Jinja chat template; enable_thinking=false"
            ),
            tool_parser="none",
            thinking=False,
            notes=(
                f"WBS {wbs}; Ornith 1.5 9B 1GPUx2 + LiteLLM; concurrency C{args.concurrency}; "
                "one measured execution; no warmup."
            ),
        )
    )
    if args.retry_of:
        config.update(
            retry_of=args.retry_of,
            retry_reason="harness_bug",
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
        lane=args.lane,
        concurrency=args.concurrency,
        topology="1gpu-x2-independent",
        host=socket.gethostname(),
        remote_path=str(raw),
        started_at_utc=h.utc(),
        boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        pid=os.getpid(),
        process_start_ticks=Path("/proc/self/stat").read_text().split()[21],
        measurement_timeout_s=3600 if args.concurrency == 2 else 2400,
        startup_timeout_s=300 if plan["runtime"] == "llama.cpp" else 600,
        scope=f"WBS {wbs}: one C{args.concurrency} 128K batch for Ornith 9B 1GPUx2",
        cleanup_policy="only owned cidfiles/pids with matching experiment label",
        planned_config_sha256=h.sha(h.canon(config)),
        source_sha256={
            str(p.relative_to(ROOT)): h.sha(p.read_bytes())
            for p in sorted((ROOT / "scripts").glob("*.py"))
        },
    )

    server_processes: list[subprocess.Popen] = []
    gateway_process: subprocess.Popen | None = None
    stop = threading.Event()
    collector = None
    peak_probe = h.GPUPeakProbe(interval_s=0.5)
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

        # Probe port availability
        for p in [args.gateway_port, args.port, args.port + 1]:
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(("127.0.0.1", p))

        check = launcher.preflight(plan)
        h.save(runtime / "preflight.json", check)
        if not check["pass"]:
            raise RuntimeError("runtime preflight failed")

        # Verify artifact checksums
        artifact = plan["model_identity"]
        if artifact.get("path") and Path(artifact["path"]).is_file():
            checksum = command(["sha256sum", artifact["path"]], 300).split()[0]
            artifact_check = dict(
                path=artifact["path"],
                sha256=checksum,
                expected=artifact.get("sha256"),
            )
            if artifact.get("sha256") and checksum != artifact["sha256"]:
                raise RuntimeError("model SHA256 mismatch")
            h.save(runtime / "artifact-check.json", artifact_check)
        elif artifact.get("path") and Path(artifact["path"]).is_dir():
            h.save(runtime / "artifact-check.json", dict(path=artifact["path"], status="directory_verified"))

        # Version receipt
        if plan["runtime"] == "llama.cpp":
            img = plan["commands"][0][plan["commands"][0].index("--entrypoint") + 2]
            (runtime / "runtime-version.txt").write_text(
                command(
                    ["docker", "run", "--rm", "--pull=never", "--gpus", "all", "--entrypoint", "llama-server", img, "--version"],
                    60,
                )
            )
        else:
            py = os.environ.get("V100_1CAT_PYTHON", "python3")
            code = "import importlib.metadata as m; print('1cat-vllm:', m.version('1cat-vllm'))"
            (runtime / "runtime-version.txt").write_text(
                command([py, "-c", code], 30)
            )

        # Gateway version receipt
        gw_img = plan["gateway"]["image"]
        code = "import importlib.metadata as m; print('litellm:', m.version('litellm'))"
        (runtime / "gateway-version.txt").write_text(
            command(["docker", "run", "--rm", "--pull=never", "--entrypoint", "python", gw_img, "-c", code], 60)
        )

        collector = threading.Thread(target=telemetry)
        collector.start()
        peak_probe.start()
        checkpoint(raw, "running", step="servers_startup")

        # Launch backends
        envs = plan.get("command_environments") or [plan.get("environment", {}) for _ in backend_cmds]
        for i, (cmd, extra_env) in enumerate(zip(backend_cmds, envs)):
            env = os.environ.copy()
            env.update({k: str(v) for k, v in extra_env.items()})
            log_f = (runtime / f"server-{i}.log").open("x")
            server_processes.append(subprocess.Popen(cmd, env=env, stdout=log_f, stderr=subprocess.STDOUT))

        # Launch gateway
        gw_log_f = (runtime / "gateway.log").open("x")
        gateway_process = subprocess.Popen(gateway_cmd, env=os.environ.copy(), stdout=gw_log_f, stderr=subprocess.STDOUT)

        # Health polling
        adapter = h.make_plan_adapter(plan, timeout_s=5)
        startup_timeout_s = 300 if plan["runtime"] == "llama.cpp" else 600
        deadline = time.monotonic() + startup_timeout_s

        while True:
            # Check backend process health
            for i, p in enumerate(server_processes):
                if p.poll() is not None:
                    log_text = (runtime / f"server-{i}.log").read_text(errors="replace").lower()
                    verdict = (
                        "FAIL_OOM"
                        if any(x in log_text for x in ("out of memory", "cuda error: out of memory"))
                        else "FAIL_STARTUP"
                    )
                    raise RuntimeError(f"backend server {i} exited prematurely with code {p.returncode}")

            if gateway_process.poll() is not None:
                verdict = "FAIL_STARTUP"
                raise RuntimeError(f"gateway process exited prematurely with code {gateway_process.returncode}")

            health_status = adapter.health()
            if health_status["healthy"]:
                break

            if time.monotonic() >= deadline:
                verdict = "FAIL_TIMEOUT"
                raise TimeoutError("startup deadline expired waiting for backends and gateway")

            time.sleep(2)

        checkpoint(
            raw,
            "running",
            step="servers_ready",
            gateway_endpoint=plan["gateway"]["endpoint"],
            backend_endpoints=plan["backend_endpoints"],
        )

        with (runtime / "measurement.log").open("x") as log:
            child = subprocess.run(
                [sys.executable, __file__, "--worker", str(raw)],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600 if args.concurrency == 2 else 2400,
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
        peak_probe.stop()
        h.save(raw / "gpu-peak.json", peak_probe.summary())

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
                dict(
                    verdict=verdict,
                    c1_128k=args.concurrency == 1,
                    error=error,
                    peak_vram_gpu0_mib=peak_probe.peaks.get(0),
                    peak_vram_gpu1_mib=peak_probe.peaks.get(1),
                ),
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

        # Cleanup gateway
        cleanup_report = {"gateway_stopped": False, "backends_stopped": []}
        if gateway_cid.exists():
            cid = gateway_cid.read_text().strip()
            command(["docker", "rm", "-f", cid], timeout=30)
            cleanup_report["gateway_stopped"] = True
        elif gateway_process and gateway_process.poll() is None:
            gateway_process.terminate()
            try:
                gateway_process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                gateway_process.kill()
            cleanup_report["gateway_stopped"] = True

        # Cleanup backends
        if is_docker_backends:
            for cid_file in backend_cids:
                if cid_file.exists():
                    cid = cid_file.read_text().strip()
                    command(["docker", "rm", "-f", cid], timeout=30)
                    cleanup_report["backends_stopped"].append(cid)
        else:
            for i, p in enumerate(server_processes):
                if p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        p.kill()
                    cleanup_report["backends_stopped"].append(p.pid)

        # Wait on subprocess handles
        for p in server_processes:
            try:
                p.wait(timeout=10)
            except Exception:
                pass
        if gateway_process:
            try:
                gateway_process.wait(timeout=10)
            except Exception:
                pass

        stop.set()
        if collector:
            collector.join(timeout=10)

        h.save(runtime / "cleanup.json", cleanup_report)
        (runtime / "host-after.txt").write_text(command(["nvidia-smi"]))
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id")
    parser.add_argument("--retry-of")
    parser.add_argument("--retry-evidence")
    parser.add_argument("--model", default="ornith-1.5-9b", choices=["ornith-1.5-9b"])
    parser.add_argument(
        "--lane",
        choices=["TARGET", "NGRAM", "MTP", "MTP_NGRAM", "STOCK"],
        required=True,
    )
    parser.add_argument("--concurrency", type=int, choices=[1, 2], required=True)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--gateway-port", type=int, default=18079)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()

    if args.worker:
        measure(args.worker)
    else:
        if args.retry_of and not args.retry_evidence:
            parser.error("--retry-of requires --retry-evidence")
        if not args.experiment_id:
            parser.error("--experiment-id is required")
        if not re.fullmatch(r"EXP-V100-[A-Z0-9][A-Z0-9-]*", args.experiment_id):
            parser.error("invalid experiment ID")
        raise SystemExit(run(args))


if __name__ == "__main__":
    main()
