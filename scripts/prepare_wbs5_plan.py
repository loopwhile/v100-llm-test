#!/usr/bin/env python3
"""Prepare immutable WBS5 dry plans; this tool never starts servers or sends requests."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bench_harness as h
import build_128k_workload as workload_builder
import runtime_launcher as launcher

CANDIDATES_PATH = ROOT / "config/profiles/wbs5-candidates.json"
EXPECTED = {
    "R0": ("TARGET_BASELINE", "TARGET", 512, 128, "none"),
    "R1": ("TARGET_UB256", "TARGET", 512, 256, "none"),
    "R2": ("NGRAM_DEFAULT", "NGRAM", 512, 128, "ngram-simple"),
}
EXP_RE = re.compile(
    r"EXP-V100-ORN15-9B-LLAMA-(TARGET|NGRAM)-B512-UB(?:128|256)-"
    r"1GPU2-C2-PERF-\d{8}-\d{3}"
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def frozen_candidates() -> tuple[dict, dict[str, dict]]:
    profile = read_json(CANDIDATES_PATH)
    items = {item["id"]: item for item in profile["candidates"]}
    normalized = {
        key: (
            value["candidate_id"], value["lane"], value["batch_size"],
            value["ubatch_size"], value["spec_type"],
        )
        for key, value in items.items()
    }
    if normalized != EXPECTED:
        raise ValueError("WBS5 frozen candidate set or values have drifted")
    if set(items) != {"R0", "R1", "R2"}:
        raise ValueError("WBS5 candidate set must contain exactly R0/R1/R2")
    return profile, items


def candidate_experiment_id(candidate: dict, date: str, sequence: int) -> str:
    lane_part = candidate["lane"]
    return (
        f"EXP-V100-ORN15-9B-LLAMA-{lane_part}-B{candidate['batch_size']}-"
        f"UB{candidate['ubatch_size']}-1GPU2-C2-PERF-{date}-{sequence:03d}"
    )


def _replace_value(command: list[str], option: str, value: str) -> None:
    index = command.index(option)
    command[index + 1] = value


def _assert_one_variable_delta(r0: dict, candidate: dict, commands: list[list[str]]) -> None:
    baseline = r0["commands"]
    if len(baseline) != len(commands):
        raise ValueError("candidate changed the number of backend launch commands")
    expected_option = "--ubatch-size" if candidate["id"] == "R1" else "--spec-type"
    expected_value = str(candidate["ubatch_size"] if candidate["id"] == "R1" else candidate["spec_type"])
    for left, right in zip(baseline, commands):
        if len(left) != len(right):
            raise ValueError("candidate launch command shape differs from R0")
        differences = [i for i, pair in enumerate(zip(left, right)) if pair[0] != pair[1]]
        option_index = left.index(expected_option)
        value_index = option_index + 1
        if candidate["id"] == "R1":
            if differences != [value_index] or right[value_index] != expected_value:
                raise ValueError("R1 must differ from R0 only at --ubatch-size")
        elif candidate["id"] == "R2":
            if differences != [value_index] or right[value_index] != expected_value:
                raise ValueError("R2 must differ from R0 only at --spec-type")
        elif differences:
            raise ValueError("R0 must be the baseline launch command")


def build_plan(candidate_key: str, experiment_id: str, root: Path = ROOT) -> dict:
    profile, candidates = frozen_candidates()
    candidate = candidates[candidate_key]
    if not EXP_RE.fullmatch(experiment_id):
        raise ValueError("experiment ID does not match the WBS5 convention")
    expected_id = candidate_experiment_id(
        candidate, experiment_id.rsplit("-", 2)[1], int(experiment_id.rsplit("-", 1)[1])
    )
    if experiment_id != expected_id:
        raise ValueError(f"experiment ID does not match {candidate_key}: expected {expected_id}")

    manifest_path = root / profile["workload"]
    manifest = workload_builder.load_manifest(manifest_path)
    if (
        manifest.get("mode") != "performance"
        or manifest.get("context_tokens") != 131072
        or manifest.get("output_tokens") != 4096
        or manifest.get("min_output_tokens") != 1024
        or manifest.get("sampling") != {"temperature": 0, "top_p": 1, "seed": 520}
        or len(manifest.get("requests", [])) != 2
        or len({x.get("project_id") for x in manifest["requests"]}) != 2
        or not manifest.get("independent_projects_required")
        or not manifest.get("diversify_identifiers")
    ):
        raise ValueError("authoritative performance workload contract has drifted")

    base = launcher.build_plan(
        root, "ornith-1.5-9b", "TARGET", 2, profile["topology"], 18080, 18079
    )
    if not base.get("supported_for_planning"):
        raise ValueError("R0 runtime plan is unsupported: " + base.get("reason", "unknown"))
    commands = [list(cmd) for cmd in base["commands"]]
    if candidate_key == "R2":
        base = launcher.build_plan(
            root, "ornith-1.5-9b", candidate["lane"], 2, profile["topology"], 18080, 18079
        )
        commands = [list(cmd) for cmd in base["commands"]]
    else:
        for cmd in commands:
            _replace_value(cmd, "--batch-size", str(candidate["batch_size"]))
            _replace_value(cmd, "--ubatch-size", str(candidate["ubatch_size"]))

    for cmd in commands:
        if cmd[cmd.index("--batch-size") + 1] != str(candidate["batch_size"]):
            raise ValueError("batch-size differs from frozen candidate contract")
        if cmd[cmd.index("--ubatch-size") + 1] != str(candidate["ubatch_size"]):
            raise ValueError("ubatch-size differs from frozen candidate contract")
        if cmd[cmd.index("--spec-type") + 1] != candidate["spec_type"]:
            raise ValueError("spec-type differs from frozen candidate contract")
    r0_plan = launcher.build_plan(root, "ornith-1.5-9b", "TARGET", 2, profile["topology"], 18080, 18079)
    _assert_one_variable_delta(r0_plan, candidate, commands)
    base["commands"] = commands
    base["lane"] = candidate["lane"]
    base["speculative"] = "ngram" if candidate["id"] == "R2" else "target-only"
    base["ngram"] = candidate["spec_type"] if candidate["id"] == "R2" else "off"
    image = base["commands"][0][base["commands"][0].index("--entrypoint") + 2]

    return {
        "schema_version": 1,
        "plan_only": True,
        "wbs": "5.1",
        "candidate": candidate,
        "experiment_id": experiment_id,
        "workload": {
            "path": profile["workload"],
            "sha256": sha(manifest_path.read_bytes()),
            "workload_id": manifest["workload_id"],
            "mode": manifest["mode"],
        },
        "model": {
            "model_id": "Ornith-1.5-9B",
            "artifact": "/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf",
            "sha256": "79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480",
            "weight_quant": "Q6_K",
            "kv": "FP16",
        },
        "runtime_contract": {
            "runtime": "llama.cpp",
            "image": image,
            "build": 10775,
            "commit": "67a17c17caa95742186f8b1ecadd1b5abd6d5ebb",
            "backend_context": 131072,
            "backend_parallel": 1,
            "kv_unified": True,
            "kv_unified_per_slot": 131072,
            "flash_attention": "on",
            "jinja": True,
            "reasoning": "off",
            "no_warmup": True,
            "topology": "1gpu-x2-independent",
            "gpu_assignment": {"backend-0": 0, "backend-1": 1},
            "litellm_version": "1.101.0",
            "litellm_commit": "18243cd7af4c3325165ba68b21379e2719e051c7",
            "litellm_image": "ghcr.io/berriai/litellm:v1.101.0",
            "routing_strategy": "least-busy",
            "backend_max_parallel_requests": 1,
            "num_retries": 0,
            "routing_settled_admission": True,
        },
        "runtime_cli_evidence": {
            "source": "P520 pinned image llama-server --help and --version; upstream arg parser at the pinned commit",
            "version": "0.3.0-dev (build 10775, commit 67a17c17c)",
            "options": {
                "-m / --model": {"supported": True, "type": "path", "default": "required model argument"},
                "--host": {"supported": True, "type": "string", "default": "127.0.0.1"},
                "--port": {"supported": True, "type": "integer", "default": 8080},
                "-ngl / --gpu-layers": {"supported": True, "type": "integer or auto/all", "default": "auto"},
                "--ctx-size": {"supported": True, "type": "integer", "default": 0},
                "--parallel": {"supported": True, "type": "integer", "default": -1},
                "--kv-unified": {"supported": True, "type": "boolean switch", "default": "enabled when slots are auto"},
                "--kv-unified-per-slot": {"supported": True, "type": "integer", "default": "unset"},
                "--batch-size": {"supported": True, "type": "integer", "default": 2048},
                "--ubatch-size": {"supported": True, "type": "integer", "default": 512},
                "--cache-type-k / --cache-type-v": {"supported": True, "type": "KV type", "default": "f16"},
                "--spec-type": {"supported": True, "accepted": ["none", "ngram-simple"]},
                "--spec-ngram-simple-size-n": {"supported": True, "type": "integer", "default": 12},
                "--spec-ngram-simple-size-m": {"supported": True, "type": "integer", "default": 48},
                "--spec-ngram-simple-min-hits": {"supported": True, "type": "integer", "default": 1},
                "--flash-attn": {"supported": True, "accepted": ["on", "off", "auto"]},
                "--jinja": {"supported": True, "type": "boolean switch", "default": "enabled"},
                "--reasoning": {"supported": True, "accepted": ["on", "off", "auto"]},
                "--metrics": {"supported": True, "type": "boolean switch", "default": "disabled"},
                "--slots": {"supported": True, "type": "boolean switch", "default": "enabled"},
                "--no-warmup": {"supported": True, "default": "warmup enabled"},
                "cuda_graph_disable": {"supported": False, "note": "no graph switch appears in this pinned --help"},
            },
            "upstream_argument_source": "https://github.com/ggml-org/llama.cpp/blob/67a17c17caa95742186f8b1ecadd1b5abd6d5ebb/common/arg.cpp",
            "sm70_flash_attention_source": {
                "compute_capability": "V100 SM70 matches GGML_CUDA_CC_VOLTA=700",
                "dispatch": "pinned CUDA source selects the Volta tile/MMA Flash Attention path when the Volta arch is compiled",
                "files": [
                    "https://github.com/ggml-org/llama.cpp/blob/67a17c17caa95742186f8b1ecadd1b5abd6d5ebb/ggml/src/ggml-cuda/common.cuh",
                    "https://github.com/ggml-org/llama.cpp/blob/67a17c17caa95742186f8b1ecadd1b5abd6d5ebb/ggml/src/ggml-cuda/fattn.cu",
                ],
                "runtime_evidence": "WBS4 ran the same Flash Attention ON contract successfully on the two P520 V100s",
            },
        },
        "warmup_policy": profile["warmup"],
        "launch_plan": base,
        "candidate_profile_sha256": sha(CANDIDATES_PATH.read_bytes()),
        "configuration_sha256": {
            relative: sha((root / relative).read_bytes())
            for relative in (
                "config/models/ornith-1.5-9b.json",
                "config/runtime-lock.json",
                "config/profiles/runtime-lanes.json",
                "config/profiles/topologies.json",
            )
        },
        "source_sha256": {
            "scripts/runtime_launcher.py": sha((root / "scripts/runtime_launcher.py").read_bytes()),
            "scripts/bench_harness.py": sha((root / "scripts/bench_harness.py").read_bytes()),
            "scripts/run_1gpu_litellm.py": sha((root / "scripts/run_1gpu_litellm.py").read_bytes()),
        },
    }


def _materialize_launch_files(plan: dict, directory: Path) -> dict:
    runtime = directory / "runtime"
    runtime.mkdir(parents=True, exist_ok=False)
    gateway_path = runtime / "litellm-config.yaml"
    gateway_path.write_text(json.dumps(plan["launch_plan"]["gateway"]["config"], indent=2) + "\n")
    commands = []
    for i, source in enumerate(plan["launch_plan"]["commands"]):
        cmd = list(source)
        name_index = cmd.index("--name") + 1
        cmd[name_index] = f"{plan['experiment_id'].lower()}-backend-{i}"
        cmd[2:2] = ["--cidfile", str(runtime / f"container-{i}.cid"), "--label", f"experiment={plan['experiment_id']}"]
        commands.append(cmd)
    gateway_cmd = [
        item.replace("{LITELLM_CONFIG}", str(gateway_path))
        for item in plan["launch_plan"]["gateway"]["command"]
    ]
    name_index = gateway_cmd.index("--name") + 1
    gateway_cmd[name_index] = f"{plan['experiment_id'].lower()}-gateway"
    gateway_cmd[2:2] = ["--cidfile", str(runtime / "container-gateway.cid"), "--label", f"experiment={plan['experiment_id']}"]
    commands.append(gateway_cmd)
    plan["exact_launch_commands"] = [shlex.join(cmd) for cmd in commands]
    plan["raw_config"] = {
        "experiment_id": plan["experiment_id"],
        "candidate_id": plan["candidate"]["candidate_id"],
        "candidate_key": plan["candidate"]["id"],
        "wbs": plan["wbs"],
        "workload": plan["workload"],
        "runtime_contract": plan["runtime_contract"],
        "warmup_policy": plan["warmup_policy"],
        "effective_server_commands": plan["launch_plan"]["commands"],
        "exact_launch_commands": plan["exact_launch_commands"],
        "gateway_config_path": str(gateway_path),
        "launch_plan_sha256": sha(h.canon(plan["launch_plan"])),
    }
    plan["raw_config_sha256"] = sha(h.canon(plan["raw_config"]))
    (runtime / "plan.json").write_text(json.dumps(plan["launch_plan"], ensure_ascii=False, indent=2) + "\n")
    (runtime / "planned-config.json").write_text(json.dumps(plan["raw_config"], ensure_ascii=False, indent=2) + "\n")
    (runtime / "candidate-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    return plan


def prepare(candidate_key: str, experiment_id: str, output_root: Path) -> Path:
    plan = build_plan(candidate_key, experiment_id)
    destination = output_root / experiment_id
    destination.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_launch_files(plan, destination)
    except Exception:
        # The fresh plan directory is retained as evidence of an incomplete preparation.
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=tuple(EXPECTED), required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/plans/wbs5")
    parser.add_argument("--print-only", action="store_true", help="print plan without writing files")
    args = parser.parse_args()
    plan = build_plan(args.candidate, args.experiment_id)
    if args.print_only:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    output = args.output_root.resolve() / args.experiment_id
    output.parent.mkdir(parents=True, exist_ok=True)
    # Rebuild has already been validated; prepare() enforces exclusive fresh-directory creation.
    prepared = prepare(args.candidate, args.experiment_id, output.parent)
    print(json.dumps({"prepared_plan": str(prepared), "plan_only": True}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
