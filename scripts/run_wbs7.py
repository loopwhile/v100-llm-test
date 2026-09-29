#!/usr/bin/env python3
"""Run one frozen WBS 7 Qwen C2 performance candidate on p520-llm.

The only accepted candidates are MTP1 and GQA2. Each invocation creates one
fresh experiment directory, makes one performance/v1 C2 request batch, and
stops only the container it started. No fallback, retry or warmup is built in.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time

import bench_harness as h
import build_128k_workload as workload_builder
from measurement_policy import future_config
import wbs5_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
BASE_ID = "EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001"
EXPERIMENTS = {
    "mtp1": "EXP-V100-WBS7-QWEN-LLAMA-MTP1-C2-128K-20260929-001",
    "gqa2": "EXP-V100-WBS7-QWEN-LLAMA-GQA2-Q80-C2-128K-20260929-001",
}
GQA_IMAGE = "wbs7-qwen-gqa2:b10775-20260929"
WORKLOAD = ROOT / "workloads/performance/v1.json"
BASE = ROOT / "results/raw" / BASE_ID / "config.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan(candidate: str, gqa_image_digest: str | None = None) -> dict:
    if candidate not in EXPERIMENTS:
        raise ValueError(candidate)
    base = json.loads(BASE.read_text())
    command = list(base["commands"][0])
    assert command[command.index("--spec-type") + 1] == "none"
    assert command[command.index("--ubatch-size") + 1] == "256"
    assert command[command.index("--cache-type-k") + 1] == "q8_0"
    assert command[command.index("--cache-type-v") + 1] == "q8_0"
    assert command[command.index("--ctx-size") + 1] == "262144"
    assert command[command.index("--parallel") + 1] == "2"
    assert command[command.index("--kv-unified-per-slot") + 1] == "131072"
    image_index = command.index("--entrypoint") + 2
    if candidate == "mtp1":
        command[command.index("--spec-type") + 1] = "draft-mtp"
        command[command.index("--spec-type") + 2:command.index("--spec-type") + 2] = ["--spec-draft-n-max", "1"]
    else:
        if not gqa_image_digest or not gqa_image_digest.startswith("sha256:"):
            raise ValueError("GQA candidate requires pinned local image digest")
        command[image_index] = GQA_IMAGE
    ident = EXPERIMENTS[candidate]
    command[command.index("--name") + 1] = ident.lower() + "-backend-0"
    command[command.index("--label") + 1] = "project=v100-llm-test"
    launch = [*command[:2], "--cidfile", f"{ROOT}/results/raw/{ident}/runtime/container-0.cid",
              "--label", "experiment=" + ident, *command[2:]]
    cfg = future_config({
        **{key: value for key, value in base.items() if key in (
            "runtime", "runtime_revision", "model", "model_identity", "weight_quant",
            "kv_cache", "topology", "concurrency", "context_tokens_per_agent",
            "chat_template", "chat_template_kwargs", "tool_parser", "thinking", "sampling",
            "endpoint", "prefix_cache_lane", "context_tokens", "context_test",
            "min_context_utilization", "backend_variant")},
        "phase": "WBS7", "candidate_id": "Q38-LLAMA-WBS7-" + candidate.upper(),
        "experiment_id": ident, "speculative": "native-mtp" if candidate == "mtp1" else "target-only",
        "ngram": "off", "launch_command": shlex.join(launch),
        "workload_manifest_sha256": sha(WORKLOAD),
        "notes": "WBS7 single measured C2 128K x2 performance/v1 batch; no warmup/fallback/retry.",
        "control_experiment_id": BASE_ID,
        "runtime_image_digest": gqa_image_digest if candidate == "gqa2" else (
            "sha256:" + base["wbs5_plan"]["runtime_identity"]["image"].split("@sha256:", 1)[1]),
    })
    h.validate(cfg)
    return {"candidate": candidate, "experiment_id": ident, "command": launch,
            "config": cfg, "source_config_sha256": sha(BASE), "workload_sha256": sha(WORKLOAD)}


def save_failure(raw: Path, cfg: dict, verdict: str, error: str) -> None:
    if not (raw / "config.json").exists():
        h.save(raw / "config.json", cfg)
        h.save(raw / "identity.json", {"config_sha256": h.sha(h.canon(cfg)), "created_at_utc": h.utc()})
    if not (raw / "metrics.json").exists():
        h.save(raw / "metrics.json", {"verdict": verdict, "error": error})
    if not (raw / "completion.json").exists():
        h.save(raw / "completion.json", {"experiment_id": cfg["experiment_id"], "verdict": verdict,
                                        "completed_at_utc": h.utc(), "error": error})


def execute(p: dict) -> int:
    if socket.gethostname().split(".")[0] != "p520-llm":
        raise RuntimeError("measured execution requires p520-llm")
    lock = ROOT / "results/experiment.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return execute_locked(p)


def execute_locked(p: dict) -> int:
    raw = ROOT / "results/raw" / p["experiment_id"]
    raw.mkdir(parents=True, exist_ok=False)
    runtime = raw / "runtime"
    runtime.mkdir()
    cfg, command = p["config"], p["command"]
    h.save(runtime / "planned-config.json", cfg)
    h.save(runtime / "frozen-plan.json", p)
    h.save(runtime / "progress.json", {"phase": "prepared", "at_utc": h.utc(),
                                       "generation_requests": 0, "warmup_requests": 0})
    container = None
    verdict, error = "INCONCLUSIVE", None
    try:
        if sha(WORKLOAD) != cfg["workload_manifest_sha256"] or sha(BASE) != p["source_config_sha256"]:
            raise ValueError("frozen input changed")
        h.save(runtime / "gpu-before.json", {"at_utc": h.utc(), "query": subprocess.run(
            ["nvidia-smi", "--query-gpu=index,uuid,memory.used,utilization.gpu,power.draw,clocks.sm,clocks.mem",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True).stdout})
        if subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
                          capture_output=True, text=True, check=True).stdout.strip():
            raise RuntimeError("GPU compute process already present")
        with socket.socket() as port:
            port.bind(("127.0.0.1", 18080))
        model = Path(cfg["model_identity"]["path"])
        actual_model_sha = sha(model)
        h.save(runtime / "artifact-check.json", {"path": str(model), "actual_sha256": actual_model_sha,
                                                 "expected_sha256": cfg["model_identity"]["sha256"]})
        if actual_model_sha != cfg["model_identity"]["sha256"]:
            raise ValueError("model SHA256 mismatch")
        image = command[command.index("--entrypoint") + 2]
        actual_image = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image],
                                      capture_output=True, text=True, check=True).stdout.strip()
        if actual_image != cfg["runtime_image_digest"]:
            raise ValueError("runtime image digest mismatch")
        h.save(runtime / "image-check.json", {"image": image, "actual": actual_image,
                                              "expected": cfg["runtime_image_digest"]})
        with (runtime / "server-0.log").open("x") as log:
            container = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        h.save(runtime / "progress.json", {"phase": "server_starting", "at_utc": h.utc(),
                                           "generation_requests": 0, "warmup_requests": 0})
        adapter = h.HTTPAdapter(cfg["endpoint"], "llama.cpp", timeout_s=7200)
        deadline = time.monotonic() + 600
        while not adapter.health()["healthy"]:
            if container.poll() is not None:
                raise RuntimeError("server exited during startup")
            if time.monotonic() > deadline:
                raise TimeoutError("server startup exceeded 600 s")
            time.sleep(2)
        h.save(runtime / "startup-snapshot.json", adapter.snapshot())
        manifest = workload_builder.load_manifest(WORKLOAD)
        built = workload_builder.build(manifest, adapter, cfg["model"], thinking=False,
                                       chat_template_kwargs=cfg["chat_template_kwargs"], sampling=cfg["sampling"])
        if built.get("source_manifest_sha256") != h.sha(h.canon(manifest)):
            raise ValueError("workload manifest identity mismatch")
        requests = built.get("requests", [])
        if len(requests) != 2 or [row.get("project_id") for row in requests] != ["A", "B"]:
            raise ValueError("wrong C2 workload")
        if any(row.get("max_tokens") != 4096 or row.get("min_output_tokens") != 1024 for row in requests):
            raise ValueError("wrong output contract")
        evidence.install_slot_sinks(adapter, raw)
        h.save(runtime / "progress.json", {"phase": "measured_batch", "at_utc": h.utc(),
                                           "generation_requests": 2, "warmup_requests": 0})
        verdict = h.run_batch(raw, cfg, built, adapter)
        h.save(raw / "slot-progress.json", evidence.slot_progress(adapter))
        before = json.loads((raw / "server-before.json").read_text())
        after = json.loads((raw / "server-after.json").read_text())
        spec = evidence.metric_delta(before, after, "llama.cpp")
        h.save(raw / "speculative-evidence.json", spec)
        metrics = json.loads((raw / "metrics.json").read_text())
        metrics["speculative_evidence"] = spec["aggregate"]
        metrics["candidate_id"] = cfg["candidate_id"]
        metrics["workload_manifest_sha256"] = cfg["workload_manifest_sha256"]
        h.save(raw / "metrics.json", metrics)
    except TimeoutError as exc:
        verdict, error = "FAIL_TIMEOUT", str(exc)
    except Exception as exc:
        error = str(exc)
        log = (runtime / "server-0.log").read_text(errors="replace").lower() if (runtime / "server-0.log").exists() else ""
        verdict = "FAIL_OOM" if "out of memory" in log else ("FAIL_STARTUP" if container and container.poll() is not None else "INCONCLUSIVE")
    finally:
        cidfile = runtime / "container-0.cid"
        if cidfile.exists():
            cid = cidfile.read_text().strip()
            inspect = subprocess.run(["docker", "inspect", cid], capture_output=True, text=True)
            if inspect.returncode == 0:
                info = json.loads(inspect.stdout)[0]
                if info["Config"]["Labels"].get("experiment") == cfg["experiment_id"]:
                    h.save(runtime / "container-inspect.json", info)
                    subprocess.run(["docker", "stop", "--time", "10", cid], capture_output=True, text=True)
        if container:
            try:
                container.wait(timeout=30)
            except subprocess.TimeoutExpired:
                container.kill()
                container.wait(timeout=10)
        gpu_after = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,uuid,memory.used,utilization.gpu,power.draw,clocks.sm,clocks.mem",
             "--format=csv,noheader,nounits"], capture_output=True, text=True)
        h.save(runtime / "gpu-after.json", {"at_utc": h.utc(), "query": gpu_after.stdout,
                                            "error": gpu_after.stderr if gpu_after.returncode else None})
        save_failure(raw, cfg, verdict, error or "")
        h.save(runtime / "exit.json", {"verdict": verdict, "error": error, "at_utc": h.utc(),
                                       "container_removed": not cidfile.exists() or container.poll() is not None if container else True})
        evidence.reconcile_overlap_from_logs(raw)
        if (raw / "completion.json").exists():
            verdict = json.loads((raw / "completion.json").read_text())["verdict"]
        spec_path = raw / "speculative-evidence.json"
        spec = json.loads(spec_path.read_text()) if spec_path.exists() else {}
        aggregate = spec.get("aggregate", {})
        native_draft = aggregate.get("draft_tokens")
        eligibility = verdict
        if p["candidate"] == "mtp1" and verdict == "PASS_C2_ACTIVE":
            eligibility = "PASS_C2_ACTIVE" if isinstance(native_draft, (int, float)) and native_draft > 0 else "FAIL_SPEC_ACTIVITY"
        post = json.loads((raw / "health-after.json").read_text()) if (raw / "health-after.json").exists() else {}
        if verdict == "PASS_C2_ACTIVE" and post.get("healthy") is not True:
            eligibility = "INCONCLUSIVE_POST_HEALTH"
        h.save(raw / "wbs7-verdict.json", {"candidate_id": cfg["candidate_id"],
                                            "harness_verdict": verdict, "candidate_verdict": eligibility,
                                            "native_mtp_draft_tokens": native_draft,
                                            "post_health": post.get("healthy"),
                                            "at_utc": h.utc()})
        h.save(runtime / "progress.json", {"phase": "complete", "at_utc": h.utc(),
                                           "verdict": verdict, "error": error})
    return 0 if (raw / "completion.json").exists() else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", choices=tuple(EXPERIMENTS))
    parser.add_argument("--gqa-image-digest")
    parser.add_argument("--execute-measured", action="store_true")
    args = parser.parse_args()
    p = plan(args.candidate, args.gqa_image_digest)
    if not args.execute_measured:
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return 0
    return execute(p)


if __name__ == "__main__":
    raise SystemExit(main())
