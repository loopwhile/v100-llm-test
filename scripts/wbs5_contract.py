"""Frozen WBS5 dispatch and admission. Pure planning: no subprocess or HTTP calls."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import shlex

import bench_harness as h
import runtime_launcher as launcher

ROOT = Path(__file__).resolve().parents[1]
WORKLOAD = "workloads/performance/v1.json"
WORKLOAD_SHA = "e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca"
INPUT_LOCK_SHA = "1a4f30d400c54b483cb01ec0e4fac7bfe6d3d90e325694a47eb11552706b4b6a"
PYTHON = "/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python"
# IDs are transcribed from the authoritative frozen documents, not generated recipes.
TRACKS = {
    "qwen-llama": ("qwen3.8-27b", "llama.cpp", [
        "Q38-LLAMA-WBS5-R0-TARGET-B512-UB128", "Q38-LLAMA-WBS5-R1-NGRAM-DEFAULT",
        "Q38-LLAMA-WBS5-R2-TARGET-UB256"]),
    "ornith9-llama": ("ornith-1.5-9b", "llama.cpp", [
        "TARGET_BASELINE", "TARGET_UB256", "NGRAM_DEFAULT"]),
    "ornith35-llama": ("ornith-1.5-35b-a3b", "llama.cpp", [
        "ORN35-LLAMA-WBS5-R0-TARGET", "ORN35-LLAMA-WBS5-R1-MTP1",
        "ORN35-LLAMA-WBS5-R2-UB256", "ORN35-LLAMA-WBS5-R3-QUEUE4X"]),
    "gemma-llama": ("gemma4-26b-a4b", "llama.cpp", [
        "G4-LCPP-WBS5-R0-TARGET-B512-UB128", "G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128",
        "G4-LCPP-WBS5-R2-TARGET-B1024-UB128", "G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF"]),
    "qwen-onecat": ("qwen3.8-27b", "1Cat-vLLM", [
        "R0-E4M3-128K-SEMANTIC-BASELINE", "R1-E4M3-128K-CUDAGRAPH-C1",
        "R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL", "R3-E5M2-128K-KV-ROUTE"]),
    "ornith9-onecat": ("ornith-1.5-9b", "1Cat-vLLM", [
        "ORN15-9B-1CAT-WBS5-R0-BASELINE", "ORN15-9B-1CAT-WBS5-R1-MBT8192",
        "ORN15-9B-1CAT-WBS5-R2-TARGET-GRAPH", "ORN15-9B-1CAT-WBS5-R3-MTP2"]),
    "ornith35-onecat": ("ornith-1.5-35b-a3b", "1Cat-vLLM", [
        "R0-BASELINE-EAGER-MBT4096", "R1-GRAPH-AUTO-MBT4096", "R2-EAGER-MBT8192"]),
}


def candidate_id(track, candidate):
    if track not in TRACKS or not re.fullmatch(r"R[0-3]", candidate):
        raise ValueError("unknown frozen track/candidate")
    ids = TRACKS[track][2]
    index = int(candidate[1:])
    if index >= len(ids):
        raise ValueError("unknown frozen candidate")
    return ids[index]


def verify_inputs(root=ROOT):
    lock_bytes = (root / "config/wbs5-input-lock.json").read_bytes()
    if h.sha(lock_bytes) != INPUT_LOCK_SHA:
        raise ValueError("FROZEN_DELTA_MISMATCH: input lock")
    lock = json.loads(lock_bytes)
    for relative, expected in lock["sha256"].items():
        if h.sha((root / relative).read_bytes()) != expected:
            raise ValueError("FROZEN_DELTA_MISMATCH: input " + relative)
    return lock


def experiment_id(track, candidate, date, sequence):
    candidate_id(track, candidate)
    if not re.fullmatch(r"\d{8}", date) or not 1 <= sequence <= 999:
        raise ValueError("invalid experiment date/sequence")
    if track == "ornith9-llama":
        import prepare_wbs5_plan as existing
        item = existing.frozen_candidates()[1][candidate]
        return existing.candidate_experiment_id(item, date, sequence)
    return f"EXP-V100-WBS5-{track.upper()}-{candidate}-PERF-{date}-{sequence:03d}"


def run_identity(track, candidate, label):
    candidate_id(track, candidate)
    allowed = {"screening-1"}
    if track == "qwen-llama" and candidate == "R0":
        allowed = {"repetition-1", "repetition-2"}
    if track == "qwen-llama" and candidate in ("R1", "R2"):
        allowed.add("confirm-1")
    if track == "ornith35-llama" and candidate == "R1":
        allowed.add("retry-1")
    if label not in allowed:
        raise ValueError("run label outside frozen repetition/confirm policy")
    return {"label": label, "kind": label.rsplit("-", 1)[0],
            "index": int(label.rsplit("-", 1)[1]), "automatic_retry": False,
            "automatic_confirm": False, "batches_in_this_invocation": 1}


def set_value(cmd, option, value):
    cmd[cmd.index(option) + 1] = str(value)


def launch_plan(track, candidate, root=ROOT, port=18080, gateway_port=18079):
    candidate_id(track, candidate)
    verify_inputs(root)
    model, runtime, _ = TRACKS[track]
    if track == "ornith9-llama":
        # Reuse the existing planner and its one-variable assertions.
        import prepare_wbs5_plan as existing
        exp = experiment_id(track, candidate, "20260928", 1)
        plan = existing.build_plan(candidate, exp, root)["launch_plan"]
        if port != 18080 or gateway_port != 18079:
            raise ValueError("frozen Ornith9 planner ports are 18080/18079")
        return copy.deepcopy(plan)
    plan = launcher.build_plan(root, model, "TARGET" if runtime == "llama.cpp" else "STOCK",
                               2, "tp2-shared", port, gateway_port)
    if not plan.get("supported_for_planning"):
        raise ValueError("BLOCKED_BY_CONFIG: " + plan.get("reason", "unsupported"))
    cmd = plan["commands"][0]
    if runtime == "llama.cpp":
        if candidate == "R1":
            if track == "ornith35-llama":
                set_value(cmd, "--spec-type", "draft-mtp")
                cmd[cmd.index("--jinja"):cmd.index("--jinja")] = ["--spec-draft-n-max", "1"]
                plan.update(lane="MTP", speculative="native-mtp")
            else:
                set_value(cmd, "--spec-type", "ngram-simple")
                plan.update(lane="NGRAM", speculative="ngram", ngram="ngram-simple")
        if candidate == "R2":
            set_value(cmd, "--batch-size" if track == "gemma-llama" else "--ubatch-size",
                      1024 if track == "gemma-llama" else 256)
        if candidate == "R3":
            key, value = ("GGML_CUDA_DISABLE_GRAPHS", "1") if track == "gemma-llama" else ("CUDA_SCALE_LAUNCH_QUEUES", "4x")
            # Docker host environment is insufficient: pass into the container explicitly.
            cmd[cmd.index("--entrypoint"):cmd.index("--entrypoint")] = ["--env", f"{key}={value}"]
            plan["container_environment"] = {key: value}
    else:
        cmd[0] = PYTHON
        # Deliberately exclude ambient PYTHONPATH and WBS3 Qwen forced overrides.
        plan["command_environments"][0]["PYTHONPATH"] = str(root / "scripts/runtime_hooks")
        if track == "qwen-onecat":
            # Reproduce the B200 128K serving route, not its diagnostic sampling.
            # Pinned 1Cat defaults/auto-sets this to 1; omission is not env=0.
            plan["command_environments"][0]["VLLM_SM70_GDN_DECODE_FLASHQLA"] = "0"
            set_value(cmd, "--max-num-seqs", 1)
            set_value(cmd, "--max-num-batched-tokens", 2048)
            if candidate == "R1":
                cmd.remove("--enforce-eager")
                cmd.extend(["--compilation-config", '{"cudagraph_capture_sizes":[1]}'])
            elif candidate == "R2":
                plan["command_environments"][0]["VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL"] = "1"
            elif candidate == "R3":
                set_value(cmd, "--kv-cache-dtype", "fp8_e5m2")
                plan["kv_cache"] = "fp8_e5m2"
        elif track == "ornith9-onecat":
            if candidate == "R1":
                set_value(cmd, "--max-num-batched-tokens", 8192)
            elif candidate == "R2":
                cmd.remove("--enforce-eager")
            elif candidate == "R3":
                spec = dict(plan["speculative_config"], num_speculative_tokens=2)
                set_value(cmd, "--speculative-config", json.dumps(spec, separators=(",", ":")))
                plan["speculative_config"] = spec
        else:
            if candidate == "R1":
                cmd.remove("--enforce-eager")
            elif candidate == "R2":
                set_value(cmd, "--max-num-batched-tokens", 8192)
    return plan


def options(argv):
    """Lossless option values including repeated flags; reject unexpected positionals."""
    result = {}
    i = 0
    while i < len(argv):
        key = argv[i]
        if not key.startswith("-"):
            raise ValueError("FROZEN_DELTA_MISMATCH: unexpected positional " + key)
        value = True
        if i + 1 < len(argv) and not argv[i + 1].startswith("-"):
            i += 1
            value = argv[i]
        result.setdefault(key, []).append(value)
        i += 1
    return result


def normalized(plan):
    rows = []
    for cmd, env in zip(plan["commands"], plan["command_environments"]):
        if cmd[0] == "docker":
            image_index = cmd.index("--entrypoint") + 2
            wrapper = cmd[:image_index + 1]
            env_flags = {}
            clean = []
            i = 0
            while i < len(wrapper):
                if wrapper[i] == "--env":
                    key, value = wrapper[i + 1].split("=", 1)
                    if key in env_flags:
                        raise ValueError("duplicate Docker env")
                    env_flags[key] = value
                    i += 2
                else:
                    clean.append(wrapper[i]); i += 1
            rows.append({"wrapper": clean, "argv": options(cmd[image_index + 1:]),
                         "environment": env, "container_environment": env_flags})
        else:
            rows.append({"wrapper": cmd[:3], "argv": options(cmd[3:]), "environment": env})
    return {"servers": rows, "gateway": plan.get("gateway"),
            "request_contract": {"workload": WORKLOAD, "sha256": WORKLOAD_SHA,
                                 "sampling": {"temperature": 0, "top_p": 1, "seed": 520},
                                 "thinking": False, "tool_parser": "none", "concurrency": 2}}


def differences(left, right, path=""):
    if isinstance(left, dict) and isinstance(right, dict):
        rows = []
        for key in sorted(left.keys() | right.keys()):
            rows.extend(differences(left.get(key), right.get(key), f"{path}/{key}"))
        return rows
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        rows = []
        for i, (a, b) in enumerate(zip(left, right)):
            rows.extend(differences(a, b, f"{path}/{i}"))
        return rows
    return [] if left == right else [{"path": path, "r0": left, "candidate": right}]


def assert_launch(track, candidate, actual, root=ROOT, port=18080, gateway_port=18079):
    expected = launch_plan(track, candidate, root, port, gateway_port)
    if actual != expected:
        raise ValueError("FROZEN_DELTA_MISMATCH: final launch plan drift")
    delta = differences(normalized(launch_plan(track, "R0", root, port, gateway_port)), normalized(actual))
    assert_delta(track, candidate, delta)
    return delta


def assert_delta(track, candidate, delta):
    """Independent frozen OFAT allowlist, applied to normalized argv AND env."""
    def arg(flag, before, after, server=0):
        return {"path": f"/servers/{server}/argv/{flag}/0", "r0": before, "candidate": after}
    def flag(name, before, after):
        return {"path": f"/servers/0/argv/{name}", "r0": before, "candidate": after}
    def env(name, before, after, container=False):
        kind = "container_environment" if container else "environment"
        return {"path": f"/servers/0/{kind}/{name}", "r0": before, "candidate": after}
    spec1 = '{"method":"mtp","num_speculative_tokens":1,"attention_backend":"TRITON_ATTN"}'
    spec2 = '{"method":"mtp","num_speculative_tokens":2,"attention_backend":"TRITON_ATTN"}'
    allowed = {
        "qwen-llama": {"R1": [arg("--spec-type", "none", "ngram-simple")], "R2": [arg("--ubatch-size", "128", "256")]},
        "ornith9-llama": {"R1": [arg("--ubatch-size", "128", "256", i) for i in (0, 1)],
                          "R2": [arg("--spec-type", "none", "ngram-simple", i) for i in (0, 1)]},
        "ornith35-llama": {"R1": [flag("--spec-draft-n-max", None, ["1"]), arg("--spec-type", "none", "draft-mtp")],
                           "R2": [arg("--ubatch-size", "128", "256")],
                           "R3": [env("CUDA_SCALE_LAUNCH_QUEUES", None, "4x", True)]},
        "gemma-llama": {"R1": [arg("--spec-type", "none", "ngram-simple")], "R2": [arg("--batch-size", "512", "1024")],
                        "R3": [env("GGML_CUDA_DISABLE_GRAPHS", None, "1", True)]},
        "qwen-onecat": {"R1": [flag("--compilation-config", None, ['{"cudagraph_capture_sizes":[1]}']), flag("--enforce-eager", [True], None)],
                        "R2": [env("VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL", "0", "1")],
                        "R3": [arg("--kv-cache-dtype", "fp8_e4m3", "fp8_e5m2")]},
        "ornith9-onecat": {"R1": [arg("--max-num-batched-tokens", "4096", "8192")],
                           "R2": [flag("--enforce-eager", [True], None)], "R3": [arg("--speculative-config", spec1, spec2)]},
        "ornith35-onecat": {"R1": [flag("--enforce-eager", [True], None)], "R2": [arg("--max-num-batched-tokens", "4096", "8192")]},
    }
    expected = [] if candidate == "R0" else allowed[track][candidate]
    if sorted(delta, key=lambda row: row["path"]) != sorted(expected, key=lambda row: row["path"]):
        raise ValueError("FROZEN_DELTA_MISMATCH: normalized argv/environment OFAT")


def effective_environments(plan, ambient=None):
    ambient = os.environ if ambient is None else ambient
    relevant = ("VLLM_", "GGML_", "CUDA_", "NCCL_", "FLASH_QLA_", "TORCH_", "TL_", "TILELANG_")
    expected = {k: str(v) for e in plan["command_environments"] for k, v in e.items()}
    for key, value in ambient.items():
        if key.startswith(relevant) and expected.get(key) != value:
            raise ValueError("FROZEN_DELTA_MISMATCH: ambient environment " + key)
    # Minimal, completely recorded child env; no secrets or arbitrary performance knobs inherited.
    base = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}
    for key in ("HOME", "TMPDIR"):
        if key in ambient:
            base[key] = ambient[key]
    return [base | e for e in plan["command_environments"]]


def build_plan(track, candidate, exp, label, root=ROOT, port=18080, gateway_port=18079):
    cid = candidate_id(track, candidate)
    identity = run_identity(track, candidate, label)
    match = re.search(r"-(\d{8})-(\d{3})$", exp)
    if not match or exp != experiment_id(track, candidate, match[1], int(match[2])):
        raise ValueError("experiment ID does not match frozen candidate")
    expected_sequence = {"repetition-1": 1, "repetition-2": 2, "screening-1": 1, "confirm-1": 2, "retry-1": 2}[label]
    if int(match[2]) != expected_sequence:
        raise ValueError("experiment sequence does not match frozen run label")
    launch = launch_plan(track, candidate, root, port, gateway_port)
    delta = assert_launch(track, candidate, launch, root, port, gateway_port)
    status = "STATIC_READY"
    gate = None
    if track == "gemma-llama" and candidate == "R3":
        status, gate = "CONDITIONAL_PENDING_GATE", "GEMMA_GATE_B"
    elif track == "ornith9-onecat":
        status, gate = "CONDITIONAL_PENDING_GATE", "ORNITH9_G0"
    elif track == "qwen-onecat" and candidate == "R2":
        status = "BLOCKED_BY_HOST_TOOLCHAIN"
    raw = root / "results/raw" / exp
    artifact_receipt = root / "state/wbs5-artifact-receipts" / (track + ".json")
    artifact_hashes = json.loads(artifact_receipt.read_text())["sha256"] if artifact_receipt.exists() else None
    return {"schema_version": 1, "phase": "WBS5", "plan_only": True, "track": track,
            "candidate_key": candidate, "candidate_id": cid, "experiment_id": exp,
            "run_identity": identity, "status": status, "admission_gate": gate,
            "workload": {"path": WORKLOAD, "sha256": WORKLOAD_SHA, "context_per_request": 131072,
                         "requests": ["project-a", "project-b"], "output_reserve": 4096, "min_output": 1024},
            "launch_plan": launch, "normalized_effective": normalized(launch), "normalized_delta_from_r0": delta,
            "configuration_sha256": h.sha(h.canon(normalized(launch))),
            "source_sha256": {str(p.relative_to(root)): h.sha(p.read_bytes())
                              for p in sorted((root / "scripts").rglob("*.py"))},
            "raw_destination": str(raw), "overwrite_refusal": True,
            "expected_artifact_hash": launch["model_identity"].get("sha256", artifact_hashes),
            "runtime_identity": json.loads((root / "config/runtime-lock.json").read_text())["runtimes"][launch["runtime"]],
            "evidence_plan": ["runtime/pre-run-receipt.json", "runtime/effective-environment.json",
                              "runtime/server-*.log", "runtime/gpu-telemetry.jsonl", "gpu-peak.json",
                              "requests.json", "metrics.json", "wbs5-evidence.json", "graph-evidence.json",
                              "slot-progress.json", "speculative-evidence.json", "health-after.json"],
            "hard_stops": ["FROZEN_DELTA_MISMATCH", "ARTIFACT_IDENTITY_MISMATCH", "RUNTIME_IDENTITY_MISMATCH",
                           "WORKLOAD_IDENTITY_MISMATCH", "RAW_OVERWRITE_REFUSAL", "ADMISSION_GATE_PENDING"],
            "runtime_unknown": {"startup": "VERIFY_AT_STARTUP: model load, VRAM fit, routes, resolved graph/cache/MTP config",
                                "measurement": "VERIFY_DURING_MEASURED_RUN: graph hits, spec acceptance, active overlap, output integrity, prefix behavior"}}


def assert_admission(plan, receipt=None, *, performance_diagnostic=False):
    if plan["status"] == "BLOCKED_BY_HOST_TOOLCHAIN":
        raise ValueError("BLOCKED_BY_HOST_TOOLCHAIN: nvcc and CUDA toolkit absent; explicit approved host change required")
    gate = plan["admission_gate"]
    if performance_diagnostic and (plan["track"] != "ornith9-onecat" or
                                   plan["candidate_key"] not in ("R0", "R1", "R2", "R3") or
                                   gate != "ORNITH9_G0"):
        raise ValueError("performance diagnostic is limited to Ornith9 1Cat R0-R3")
    if not gate:
        return
    expected_verdict = "FAIL" if performance_diagnostic else "PASS"
    if not isinstance(receipt, dict) or receipt.get("gate") != gate or receipt.get("verdict") != expected_verdict:
        raise ValueError("CONDITIONAL_PENDING_GATE: " + gate)
    baseline = normalized(launch_plan(plan["track"], "R0"))
    if performance_diagnostic and receipt.get("baseline_source_root") is not None:
        source_root = Path(receipt["baseline_source_root"])
        if not source_root.is_absolute() or ".." in source_root.parts:
            raise ValueError("diagnostic baseline source root invalid")
        # The hook path is snapshot-local. Compare the frozen serving plan after
        # rebasing only this path to the receipt's source checkout.
        hook_path = baseline["servers"][0]["environment"].get("PYTHONPATH")
        if not isinstance(hook_path, str) or not hook_path.endswith("/scripts/runtime_hooks"):
            raise ValueError("diagnostic baseline hook path invalid")
        baseline["servers"][0]["environment"]["PYTHONPATH"] = str(source_root / "scripts/runtime_hooks")
    if receipt.get("track") != plan["track"] or receipt.get("baseline_configuration_sha256") != h.sha(h.canon(baseline)):
        raise ValueError("gate identity mismatch")
    if not receipt.get("experiment_id") or receipt["experiment_id"] == plan["experiment_id"]:
        raise ValueError("gate needs separate measured evidence")
    required = ({"semantic_audit": "FAIL", "project_a": "PASS", "project_b": "FAIL",
                 "use": "PERFORMANCE_DIAGNOSTIC_ONLY"} if performance_diagnostic else
                {"semantic_audit": "PASS", "project_a": "PASS", "project_b": "PASS"} if gate == "ORNITH9_G0" else
                {"graph_support": "PASS"})
    if any(receipt.get(k) != v for k, v in required.items()):
        raise ValueError("gate evidence incomplete")
    if gate == "ORNITH9_G0":
        pins = verify_inputs()["sha256"]
        for key in ("workloads/concurrency/v2.json", "workloads/concurrency/v2-ground-truth.json"):
            if receipt.get("file_sha256", {}).get(key) != pins[key]:
                raise ValueError("G0 workload/oracle mismatch")
    elif receipt.get("trigger") not in ("R0_VRAM_UPWARD_DRIFT", "R0_GRAPH_INSTABILITY"):
        raise ValueError("Gate B trigger missing")
    evidence = receipt.get("evidence", [])
    if not evidence:
        raise ValueError("gate raw evidence missing")
    verified = {}
    for row in evidence:
        if not isinstance(row, dict) or not row.get("path") or not row.get("sha256"):
            raise ValueError("gate evidence row invalid")
        path = Path(row["path"])
        try:
            relative = path.resolve().relative_to((ROOT / "results/raw" / receipt["experiment_id"]).resolve())
        except ValueError as exc:
            raise ValueError("gate evidence outside separate experiment") from exc
        if ".." in relative.parts:
            raise ValueError("gate evidence path invalid")
        if not path.is_file() or h.sha(path.read_bytes()) != row["sha256"]:
            raise ValueError("gate raw evidence hash mismatch")
        verified[relative.as_posix()] = path
    if performance_diagnostic:
        required_paths = ("semantic-audit.json", "requests.json", "metrics.json", "completion.json", "runtime/progress.json")
        if any(name not in verified for name in required_paths):
            raise ValueError("diagnostic requires hash-bound G0 measured and semantic evidence")
        try:
            audit = json.loads(verified["semantic-audit.json"].read_text())
            requests = json.loads(verified["requests.json"].read_text())
            metrics = json.loads(verified["metrics.json"].read_text())
            completion = json.loads(verified["completion.json"].read_text())
            progress = json.loads(verified["runtime/progress.json"].read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("diagnostic G0 evidence invalid") from exc
        pins = verify_inputs()["sha256"]
        if (audit.get("experiment_id") != receipt["experiment_id"]
                or audit.get("semantic_audit") != "FAIL"
                or audit.get("project_a") != "PASS" or audit.get("project_b") != "FAIL"
                or audit.get("requests_sha256") != h.sha(verified["requests.json"].read_bytes())
                or audit.get("oracle_sha256") != pins["workloads/concurrency/v2-ground-truth.json"]
                or not isinstance(requests, list) or [row.get("project_id") for row in requests] != ["A", "B"]
                or metrics.get("verdict") != "PASS_C2_ACTIVE" or metrics.get("c2_active") is not True
                or metrics.get("queue_only") is not False
                or completion.get("experiment_id") != receipt["experiment_id"]
                or completion.get("verdict") != "PASS_C2_ACTIVE"
                or progress.get("workload_manifest_sha256") != pins["workloads/concurrency/v2.json"]
                or progress.get("semantic_oracle_sha256") != pins["workloads/concurrency/v2-ground-truth.json"]):
            raise ValueError("diagnostic G0 identity, semantic, or measured evidence mismatch")
    if gate == "GEMMA_GATE_B":
        required_paths = ("config.json", "identity.json", "metrics.json", "completion.json")
        if any(name not in verified for name in required_paths):
            raise ValueError("Gate B requires hash-bound R0 measured evidence")
        try:
            measured_config = json.loads(verified["config.json"].read_text())
            identity = json.loads(verified["identity.json"].read_text())
            metrics = json.loads(verified["metrics.json"].read_text())
            completion = json.loads(verified["completion.json"].read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Gate B measured evidence invalid") from exc
        measured_plan = measured_config.get("wbs5_plan") or {}
        expected_candidate = candidate_id(plan["track"], "R0")
        baseline = receipt["baseline_configuration_sha256"]
        if (measured_config.get("phase") != "WBS5" or measured_config.get("track") != plan["track"]
                or measured_config.get("candidate_key") != "R0" or measured_config.get("candidate_id") != expected_candidate
                or measured_config.get("configuration_sha256") != baseline
                or measured_config.get("experiment_id") != receipt["experiment_id"]
                or measured_plan.get("track") != plan["track"] or measured_plan.get("candidate_key") != "R0"
                or measured_plan.get("candidate_id") != expected_candidate
                or measured_plan.get("configuration_sha256") != baseline
                or measured_plan.get("experiment_id") != receipt["experiment_id"]
                or (measured_plan.get("run_identity") or {}).get("label") != "screening-1"):
            raise ValueError("Gate B evidence is not the frozen R0 measured run")
        if identity.get("config_sha256") != h.sha(h.canon(measured_config)):
            raise ValueError("Gate B config identity mismatch")
        if completion.get("experiment_id") != receipt["experiment_id"] or not isinstance(metrics.get("verdict"), str):
            raise ValueError("Gate B measured completion evidence invalid")

def materialize_commands(plan, raw):
    commands = copy.deepcopy(plan["launch_plan"]["commands"])
    for i, cmd in enumerate(commands):
        if cmd[0] == "docker":
            cmd[cmd.index("--name") + 1] = f"{plan['experiment_id'].lower()}-backend-{i}"
            cmd[2:2] = ["--cidfile", str(raw / f"runtime/container-{i}.cid"),
                        "--label", "experiment=" + plan["experiment_id"]]
    gateway = plan["launch_plan"].get("gateway")
    if gateway:
        cmd = [x.replace("{LITELLM_CONFIG}", str(raw / "runtime/litellm-config.yaml")) for x in gateway["command"]]
        cmd[cmd.index("--name") + 1] = f"{plan['experiment_id'].lower()}-gateway"
        cmd[2:2] = ["--cidfile", str(raw / "runtime/container-gateway.cid"),
                    "--label", "experiment=" + plan["experiment_id"]]
        commands.append(cmd)
    return commands


def dry_plan(plan, output_root=None):
    result = copy.deepcopy(plan)
    commands = materialize_commands(plan, Path(plan["raw_destination"]))
    result["exact_launch_commands"] = commands
    result["launch_command"] = [shlex.join(cmd) for cmd in commands]
    result["effective_environment"] = effective_environments(plan["launch_plan"], {})
    result["container_environment_overrides"] = [row.get("container_environment", {}) for row in plan["normalized_effective"]["servers"]]
    result["container_image_environment"] = "VERIFY_AT_STARTUP: pinned docker inspect before launch; no image/process started by dry-plan"
    if plan["launch_plan"].get("gateway"):
        result["effective_environment"].append(dict(result["effective_environment"][0]))
    result["measured_inference_executed"] = False
    if output_root is not None:
        destination = output_root / plan["experiment_id"]
        destination.mkdir(parents=True, exist_ok=False)
        h.save(destination / "candidate-plan.json", result)
    return result
