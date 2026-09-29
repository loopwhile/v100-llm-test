#!/usr/bin/env python3
"""Explicit frozen WBS5 dispatch. Default is dry-plan, never startup/inference.

One future measured invocation requires --execute-measured and applicable gate
receipts. There are no loops over candidates, repetitions, confirms or retries.
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
from measurement_policy import future_config
import runtime_launcher as launcher
import wbs5_contract as contract
import wbs5_evidence as evidence

ROOT = contract.ROOT


def build_config(plan, environments):
    raw = Path(plan["raw_destination"])
    commands = contract.materialize_commands(plan, raw)
    config = future_config(plan["launch_plan"] | {
        "phase": "WBS5", "track": plan["track"], "candidate_key": plan["candidate_key"],
        "candidate_id": plan["candidate_id"], "wbs5_candidate": plan["candidate_id"],
        "wbs5_candidate_key": plan["candidate_key"], "run_identity": plan["run_identity"],
        "experiment_id": plan["experiment_id"], "wbs5_plan": plan,
        "configuration_sha256": plan["configuration_sha256"],
        "normalized_delta_from_r0": plan["normalized_delta_from_r0"],
        "effective_server_commands": commands, "effective_environment": environments,
        "container_environment_overrides": [row.get("container_environment", {}) for row in plan["normalized_effective"]["servers"]],
        "launch_command": "\n".join(shlex.join(c) for c in commands),
        "workload_manifest_path": str(ROOT / contract.WORKLOAD),
        "workload_manifest_sha256": contract.WORKLOAD_SHA,
        "backend_variant": "stock", "context_tokens": 131072, "context_test": True,
        "min_context_utilization": .99, "prefix_cache_lane": "cold-independent",
        "chat_template": "embedded GGUF Jinja" if plan["launch_plan"]["runtime"] == "llama.cpp" else "HF tokenizer chat template",
        "chat_template_kwargs": {"enable_thinking": False}, "tool_parser": "none", "thinking": False,
        "sampling": {"temperature": 0, "top_p": 1, "seed": 520},
        "endpoint": plan["launch_plan"]["endpoints"][0],
        "notes": "Frozen WBS5; one independent A/B performance batch; no full-size warmup, fallback, retry or tuning.",
    })
    h.validate(config)
    return config


def validate_worker_config(config):
    plan = config["wbs5_plan"]
    expected = contract.build_plan(plan["track"], plan["candidate_key"], plan["experiment_id"],
                                   plan["run_identity"]["label"])
    if plan != expected:
        raise ValueError("FROZEN_DELTA_MISMATCH: saved candidate plan")
    envs = contract.effective_environments(plan["launch_plan"])
    if plan["launch_plan"].get("gateway"):
        envs.append(dict(envs[0]))
    canonical = build_config(expected, envs)
    if set(config) - set(canonical) - {"gate_receipt", "performance_diagnostic"}:
        raise ValueError("FROZEN_DELTA_MISMATCH: unexpected effective config keys")
    if config.get("performance_diagnostic") not in (None, True):
        raise ValueError("invalid performance diagnostic marker")
    # Gate receipts are external evidence; they do not change serving configuration.
    for key in canonical:
        if config.get(key) != canonical[key]:
            raise ValueError("FROZEN_DELTA_MISMATCH: worker config " + key)
    if "retry_of" in config or config.get("measured_repetitions") != 1:
        raise ValueError("WBS5 automatic retry/repetition forbidden")
    contract.assert_admission(plan, config.get("gate_receipt"),
                              performance_diagnostic=config.get("performance_diagnostic") is True)


def validate_workload(workload):
    manifest = w.load_manifest(ROOT / contract.WORKLOAD)
    if (workload.get("version") != manifest["workload_id"] or workload.get("mode") != "performance"
            or workload.get("source_manifest_sha256") != h.sha(h.canon(manifest))
            or workload.get("context_tokens") != 131072 or workload.get("sampling") != manifest["sampling"]):
        raise ValueError("WORKLOAD_IDENTITY_MISMATCH")
    cases = workload.get("requests", [])
    if len(cases) != 2 or [x.get("project_id") for x in cases] != ["A", "B"]:
        raise ValueError("WORKLOAD_IDENTITY_MISMATCH: independent A/B")
    for case in cases:
        if case.get("max_tokens") != 4096 or case.get("min_output_tokens") != 1024 or case.get("check") != "nonempty" or any(k in case for k in ("tools", "tool_choice")):
            raise ValueError("WORKLOAD_IDENTITY_MISMATCH: request contract")


def measure(raw):
    config = json.loads((raw / "runtime/planned-config.json").read_text())
    if raw.resolve() != Path(config["wbs5_plan"]["raw_destination"]).resolve():
        raise ValueError("FROZEN_DELTA_MISMATCH: worker raw destination")
    validate_worker_config(config)
    if h.sha((ROOT / contract.WORKLOAD).read_bytes()) != config["workload_manifest_sha256"]:
        raise ValueError("WORKLOAD_IDENTITY_MISMATCH")
    adapter = h.make_plan_adapter(config, timeout_s=3600)
    workload = w.build(w.load_manifest(ROOT / contract.WORKLOAD), adapter, config["model"],
                       thinking=False, chat_template_kwargs=config["chat_template_kwargs"], sampling=config["sampling"])
    validate_worker_config(config)
    validate_workload(workload)
    return h.run_batch(raw, config, workload, adapter)


def command(cmd, timeout=30):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True).stdout


def identity_check(plan, runtime):
    launch = plan["launch_plan"]
    model = launch["model_identity"]
    path = Path(model["path"])
    if launch["runtime"] == "llama.cpp":
        actual = command(["sha256sum", str(path)], 600).split()[0]
        h.save(runtime / "artifact-check.json", {"path": str(path), "expected": model["sha256"], "actual": actual})
        if actual != model["sha256"]:
            raise ValueError("ARTIFACT_IDENTITY_MISMATCH")
        image = plan["runtime_identity"]["image"]
        version_proc = subprocess.run(
            ["docker", "run", "--rm", "--pull=never", "--gpus", "all",
             "--entrypoint", "llama-server", image, "--version"],
            capture_output=True, text=True, timeout=60, check=True,
        )
        # llama-server writes --version to stderr in the pinned V100 image.
        version = version_proc.stdout + version_proc.stderr
        if "10775" not in version or "67a17c17" not in version:
            raise ValueError("RUNTIME_IDENTITY_MISMATCH")
    else:
        wheel = Path("/home/loopwhile/1cat-vllm-wheel") / plan["runtime_identity"]["wheel"]
        wheel_hash = command(["sha256sum", str(wheel)], 120).split()[0]
        if wheel_hash != plan["runtime_identity"]["sha256"]:
            raise ValueError("RUNTIME_IDENTITY_MISMATCH: wheel")
        version = command([contract.PYTHON, "-c", "import importlib.metadata as m; print(m.version('1cat-vllm'))"])
        if version.strip() != "1.5.0":
            raise ValueError("RUNTIME_IDENTITY_MISMATCH: installed distribution")
        receipt = {"path": str(path), "repository": model["repository"], "revision": model["revision"], "files": {}}
        # Bind installed bytes to the checked-in pinned-revision HF hash manifest.
        # Local download receipts are supplementary; observed hashes alone never
        # establish the intended upstream revision.
        index = path / "model.safetensors.index.json"
        names = {"config.json", "tokenizer_config.json", "tokenizer.json"}
        if index.exists():
            names.add("model.safetensors.index.json")
        names |= set(json.loads(index.read_text())["weight_map"].values()) if index.exists() else {"model.safetensors"}
        trusted_path = ROOT / "state/wbs5-artifact-receipts" / (plan["track"] + ".json")
        trusted = json.loads(trusted_path.read_text()) if trusted_path.exists() else {}
        if trusted.get("repository") != model["repository"]:
            raise ValueError("ARTIFACT_IDENTITY_MISMATCH: repository")
        for name in sorted(names):
            metadata = path / ".cache/huggingface/download" / (name + ".metadata")
            lines = metadata.read_text().splitlines() if metadata.exists() else []
            expected = trusted.get("sha256", {}).get(name)
            revision = trusted.get("revision")
            if lines and not expected:
                revision = lines[0]
                if len(lines) > 1 and len(lines[1]) == 64:
                    expected = lines[1]
            if revision != model["revision"] or not expected:
                raise ValueError("ARTIFACT_IDENTITY_MISMATCH: revision-bound hash receipt required for " + name)
            actual = command(["sha256sum", str(path / name)], 600).split()[0]
            receipt["files"][name] = {"expected": expected, "actual": actual, "revision": revision}
            if actual != expected:
                raise ValueError("ARTIFACT_IDENTITY_MISMATCH: " + name)
        config = json.loads((path / "config.json").read_text())
        if plan["track"] != "ornith9-onecat" and config.get("speculators_config"):
            raise ValueError("FROZEN_DELTA_MISMATCH: speculative auto-enable")
        h.save(runtime / "artifact-check.json", receipt)
    (runtime / "runtime-version.txt").write_text(version)


def execute_shared(plan, gate_receipt, retry_evidence=None, *, performance_diagnostic=False):
    raw = Path(plan["raw_destination"])
    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / "runtime"
    runtime.mkdir()
    if retry_evidence is not None:
        h.save(runtime / "retry-receipt.json", retry_evidence)
    envs = contract.effective_environments(plan["launch_plan"])
    config = build_config(plan, envs) | {"gate_receipt": gate_receipt}
    if performance_diagnostic:
        config["performance_diagnostic"] = True
    validate_worker_config(config)
    h.save(runtime / "planned-config.json", config)
    h.save(runtime / "candidate-plan.json", plan)
    h.save(runtime / "effective-environment.json", envs)
    cmd = config["effective_server_commands"][0]
    server = None
    stop = threading.Event()
    collector = None
    error = None
    verdict = "INCONCLUSIVE"
    rc = 1

    def telemetry():
        with (runtime / "gpu-telemetry.jsonl").open("x") as stream:
            while not stop.is_set():
                try:
                    value = command(["nvidia-smi", "--query-gpu=" + evidence.GPU_FIELDS, "--format=csv,noheader,nounits"], 5)
                    row = {"at_utc": h.utc(), "monotonic_s": time.monotonic(), "csv": value, "fields": evidence.GPU_FIELDS}
                except Exception as exc:
                    row = {"at_utc": h.utc(), "monotonic_s": time.monotonic(), "status": "UNKNOWN", "error": str(exc)}
                stream.write(json.dumps(row) + "\n"); stream.flush()
                stop.wait(2)
    try:
        receipt = evidence.pre_run_receipt(plan)
        h.save(runtime / "pre-run-receipt.json", receipt)
        evidence.validate_pre_run(receipt)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 18080))
        check = launcher.preflight(plan["launch_plan"])
        h.save(runtime / "preflight.json", check)
        if not check["pass"]:
            raise ValueError("runtime preflight failed")
        identity_check(plan, runtime)
        h.save(runtime / "effective-environment.json", evidence.environment_receipt(config))
        validate_worker_config(config)
        collector = threading.Thread(target=telemetry)
        collector.start()
        with (runtime / "server-0.log").open("x") as log:
            server = subprocess.Popen(cmd, env=envs[0], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        h.save(runtime / "server-process.json", {"pid": server.pid, "start_ticks": Path(f"/proc/{server.pid}/stat").read_text().split()[21], "launch_command": cmd, "environment": envs[0]})
        adapter = h.make_plan_adapter(plan["launch_plan"], timeout_s=5)
        deadline = time.monotonic() + (300 if plan["launch_plan"]["runtime"] == "llama.cpp" else 900)
        while not adapter.health()["healthy"]:
            if server.poll() is not None:
                verdict = "FAIL_STARTUP"
                raise RuntimeError("server exited during startup")
            if time.monotonic() >= deadline:
                verdict = "FAIL_TIMEOUT"
                raise TimeoutError("startup deadline expired")
            time.sleep(2)
        # Resolved config/route/graph evidence stays raw; it is not a static PASS.
        h.save(runtime / "startup-snapshot.json", adapter.snapshot())
        validate_worker_config(config)
        with (runtime / "measurement.log").open("x") as log:
            child = subprocess.run([sys.executable, __file__, "--worker", str(raw)], stdout=log,
                                   stderr=subprocess.STDOUT, timeout=7200)
        if child.returncode:
            raise RuntimeError("measurement worker failed")
        verdict = json.loads((raw / "completion.json").read_text())["verdict"]
        rc = 0
    except (TimeoutError, subprocess.TimeoutExpired) as exc:
        verdict = "FAIL_TIMEOUT"; error = str(exc)
    except Exception as exc:
        error = str(exc)
    finally:
        cleanup = {}
        try:
            if server:
                if cmd[0] == "docker":
                    cidfile = runtime / "container-0.cid"
                    if cidfile.exists():
                        cid = cidfile.read_text().strip()
                        info = json.loads(command(["docker", "inspect", cid]))[0]
                        if info["Config"]["Labels"].get("experiment") != plan["experiment_id"]:
                            raise ValueError("container ownership mismatch")
                        h.save(runtime / "container-inspect.json", info)
                        command(["docker", "stop", "--time", "10", cid])
                elif server.poll() is None:
                    os.killpg(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL); server.wait(timeout=30)
                cleanup["server_exit_code"] = server.returncode
        except Exception as exc:
            cleanup["error"] = str(exc)
        stop.set()
        if collector:
            collector.join(timeout=10)
        h.save(runtime / "cleanup.json", cleanup)
        if not (raw / "completion.json").exists():
            h.save(raw / "config.json", config)
            h.save(raw / "identity.json", {"config_sha256": h.sha(h.canon(config)), "created_at_utc": h.utc()})
            h.save(raw / "metrics.json", {"verdict": verdict, "error": error})
            h.save(raw / "completion.json", {"experiment_id": plan["experiment_id"], "verdict": verdict, "error": error})
        h.save(runtime / "exit.json", {"exit_code": rc, "verdict": verdict, "error": error})
        evidence.finalize(raw)
    return rc


def dispatch(plan, *, execute_measured=False, gate_receipt=None, retry_evidence=None,
             performance_diagnostic=False, output_root=None):
    if not execute_measured:
        return contract.dry_plan(plan, output_root)
    contract.assert_admission(plan, gate_receipt, performance_diagnostic=performance_diagnostic)
    if socket.gethostname().split(".")[0] != "p520-llm":
        raise RuntimeError("requires p520-llm")
    contract.assert_launch(plan["track"], plan["candidate_key"], plan["launch_plan"])
    lock_path = ROOT / "results/experiment.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if plan["track"] == "ornith9-llama":
            # Preserve the existing routing-settled + gateway lifecycle rather than replacing it.
            import run_1gpu_litellm as existing
            args = argparse.Namespace(model="ornith-1.5-9b", lane=plan["launch_plan"]["lane"], concurrency=2,
                                      experiment_id=plan["experiment_id"], wbs5_candidate=plan["candidate_key"],
                                      port=18080, gateway_port=18079, retry_of=None, retry_evidence=None,
                                      wbs5_plan=plan)
            return existing.run_locked(args)
        # Preflight currently expects this pinned Python env; restore caller env after invocation.
        old = os.environ.get("V100_1CAT_PYTHON")
        os.environ["V100_1CAT_PYTHON"] = contract.PYTHON
        try:
            return execute_shared(plan, gate_receipt, retry_evidence,
                                  performance_diagnostic=performance_diagnostic)
        finally:
            if old is None:
                os.environ.pop("V100_1CAT_PYTHON", None)
            else:
                os.environ["V100_1CAT_PYTHON"] = old


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", choices=tuple(contract.TRACKS))
    parser.add_argument("--candidate")
    parser.add_argument("--experiment-id")
    parser.add_argument("--run-label")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--gate-receipt", type=Path)
    parser.add_argument("--performance-diagnostic", action="store_true")
    parser.add_argument("--retry-evidence", type=Path)
    parser.add_argument("--execute-measured", action="store_true")
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.worker:
        measure(args.worker)
        return 0
    if not all((args.track, args.candidate, args.experiment_id, args.run_label)):
        parser.error("--track, --candidate, --experiment-id and --run-label are required")
    if args.performance_diagnostic and (not args.execute_measured or args.gate_receipt is None):
        parser.error("--performance-diagnostic requires --execute-measured and --gate-receipt")
    plan = contract.build_plan(args.track, args.candidate, args.experiment_id, args.run_label)
    retry_evidence = None
    if args.run_label == "retry-1":
        if not args.execute_measured or args.retry_evidence is None:
            parser.error("retry-1 requires --execute-measured and --retry-evidence")
        predecessor = args.experiment_id[:-3] + "001"
        previous = json.loads(args.retry_evidence.read_text())
        if (previous.get("experiment_id") != predecessor
                or previous.get("verdict") != "INCONCLUSIVE"
                or previous.get("error") != "[Errno 98] Address already in use"):
            parser.error("retry evidence does not match the R1 port-conflict failure")
        retry_evidence = {"retry_of": predecessor, "reason": "infra_invalid_port_conflict",
                          "user_authorized": True, "predecessor_completion": previous}
    elif args.retry_evidence:
        parser.error("--retry-evidence requires --run-label retry-1")
    receipt = json.loads(args.gate_receipt.read_text()) if args.gate_receipt else None
    result = dispatch(plan, execute_measured=args.execute_measured, gate_receipt=receipt,
                      retry_evidence=retry_evidence, performance_diagnostic=args.performance_diagnostic,
                      output_root=args.output_root)
    if isinstance(result, int):
        return result
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
