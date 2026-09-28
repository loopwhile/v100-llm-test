"""New WBS5 evidence only. Missing/ambiguous observations remain UNKNOWN/null."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import time

import bench_harness as h

UNKNOWN = "UNKNOWN"
GPU_FIELDS = "index,uuid,name,memory.total,memory.free,memory.used,temperature.gpu,power.draw,clocks.sm,clocks.mem,utilization.gpu"


def environment_receipt(config, execute=None):
    execute = execute or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30).stdout)
    plan = config["wbs5_plan"]["launch_plan"]
    containers = []
    images = [config["wbs5_plan"]["runtime_identity"]["image"]] * len(plan["commands"]) if plan["runtime"] == "llama.cpp" else []
    if plan.get("gateway"):
        images.append(plan["gateway"]["image"])
    overrides = config["container_environment_overrides"]
    for index, image in enumerate(images):
        info = json.loads(execute(["docker", "image", "inspect", image]))[0]
        defaults = dict(item.split("=", 1) for item in info["Config"].get("Env", []) or [])
        extra = overrides[index] if index < len(overrides) else {}
        containers.append({"image": image, "image_id": info["Id"], "image_defaults": defaults,
                           "overrides": extra, "effective_environment": defaults | extra})
    return {"host_process_environments": config["effective_environment"], "containers": containers,
            "scope": "exact subprocess env plus pinned image defaults and Docker overrides before launch"}


def pre_run_receipt(plan, execute=None):
    execute = execute or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30).stdout)
    def capture(cmd):
        try:
            return {"status": "OBSERVED", "value": execute(cmd)}
        except Exception as exc:
            return {"status": UNKNOWN, "value": None, "error": str(exc)}
    return {"at_utc": h.utc(), "monotonic_s": time.monotonic(),
            "gpu_fields": GPU_FIELDS.split(","),
            "gpus": capture(["nvidia-smi", "--query-gpu=" + GPU_FIELDS, "--format=csv,noheader,nounits"]),
            "gpu_processes": capture(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory", "--format=csv,noheader,nounits"]),
            "host_ram_swap": capture(["cat", "/proc/meminfo"]),
            "runtime_identity": plan["runtime_identity"], "model_identity": plan["launch_plan"]["model_identity"],
            "expected_artifact_hash": plan["expected_artifact_hash"],
            "candidate_id": plan["candidate_id"], "workload": plan["workload"]}


def validate_pre_run(receipt):
    if any(receipt[k]["status"] != "OBSERVED" for k in ("gpus", "gpu_processes", "host_ram_swap")):
        raise ValueError("pre-run receipt incomplete")
    if receipt["gpu_processes"]["value"].strip():
        raise ValueError("GPU has existing compute processes")
    lines = receipt["gpus"]["value"].splitlines()
    if len(lines) != 2:
        raise ValueError("host requires exactly two V100 GPUs")
    for index, line in enumerate(lines):
        fields = [x.strip() for x in line.split(",")]
        if len(fields) != len(GPU_FIELDS.split(",")) or int(fields[0]) != index or fields[2] != "Tesla V100-SXM2-16GB" or int(fields[3]) != 16384:
            raise ValueError("host GPU identity mismatch")


def telemetry_summary(path):
    observations = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            sample = json.loads(line)
            fields = sample.get("fields", "index,uuid,memory.used,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu").split(",")
            for raw in sample.get("csv", "").splitlines():
                values = dict(zip(fields, (x.strip() for x in raw.split(","))))
                gpu = observations.setdefault(values.get("index", "UNKNOWN"), {})
                for key in ("power.draw", "temperature.gpu", "clocks.sm", "clocks.mem", "utilization.gpu"):
                    try:
                        number = float(values[key])
                    except (KeyError, ValueError):
                        continue
                    gpu.setdefault(key, []).append(number)
    keys = ("power.draw", "temperature.gpu", "clocks.sm", "clocks.mem", "utilization.gpu")
    return {str(i): {key: ({"status": "OBSERVED", "min": min(values), "max": max(values), "samples": len(values)}
                          if (values := observations.get(str(i), {}).get(key)) else
                          {"status": UNKNOWN, "min": None, "max": None, "samples": 0}) for key in keys} for i in (0, 1)}


def graph_evidence(logs):
    """Parse terminal slot/task counts; duplicates are not summed, conflicts unknown."""
    rows = {}
    unassigned = []
    pattern = re.compile(r"slot\s+(?:\w+\s*:\s*)?id\s+(\d+)\s*\|\s*task\s+(\d+).*graphs reused\s*=?\s*(\d+)", re.I)
    for name, text in logs.items():
        for number, line in enumerate(text.splitlines(), 1):
            if "graphs reused" not in line.lower():
                continue
            match = pattern.search(line)
            if not match:
                unassigned.append({"source": name, "line": number, "raw": line})
                continue
            slot, task, count = map(int, match.groups())
            key = (name, slot, task)
            row = rows.setdefault(key, {"source": name, "slot_id": slot, "task_id": task, "counts": [], "lines": []})
            row["counts"].append(count); row["lines"].append(number)
    items = []
    for row in rows.values():
        unique = set(row.pop("counts"))
        row["reuse_count"] = next(iter(unique)) if len(unique) == 1 else None
        row["status"] = "OBSERVED" if len(unique) == 1 else UNKNOWN
        items.append(row)
    known = bool(items) and not unassigned and all(x["reuse_count"] is not None for x in items)
    return {"status": "OBSERVED" if known else UNKNOWN,
            "reuse_count": sum(x["reuse_count"] for x in items) if known else None,
            "items": items, "ambiguous_lines": unassigned,
            "scope": "server lifetime, includes startup/routing preflight if present; not necessarily measured-window hits",
            "raw_logs_preserved": True}


def slot_rows(slots, monotonic_s, source="server-0"):
    if not isinstance(slots, list):
        return []
    rows = []
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        progress = slot.get("next_token") or {}
        rows.append({"monotonic_s": monotonic_s, "source": source,
                     "slot_id": slot.get("id", slot.get("slot_id")),
                     "task_id": slot.get("id_task", slot.get("task_id")),
                     **{key: slot.get(key, progress.get(key)) for key in (
                         "n_prompt_tokens_processed", "n_past", "n_decoded", "is_processing")}})
    return rows


def slot_progress(adapter):
    adapters = getattr(adapter, "backends", [adapter])
    rows = []
    for i, child in enumerate(adapters):
        for sample in getattr(child, "_probe_samples", []):
            rows.extend(slot_rows(sample.get("slots"), sample["monotonic_s"], f"server-{i}"))
    return {"status": "OBSERVED" if any(x["n_prompt_tokens_processed"] is not None for x in rows) else UNKNOWN,
            "samples": sorted(rows, key=lambda x: x["monotonic_s"]),
            "limitation": "Fields unavailable from /slots remain null; resident count does not replace prompt progress."}



def llama_log_overlap(logs):
    """Prove concurrent llama.cpp decode from interleaved slot n_gen log lines.

    This is intentionally a positive-evidence fallback: it can prove active
    overlap, but lack of interleaving remains UNKNOWN rather than QUEUE_ONLY.
    """
    pattern = re.compile(
        r"slot\s+print_timing:\s*id\s+(\d+)\s*\|\s*task\s+(\d+)"
        r"\s*\|\s*n_gen\s*=\s*(\d+)",
        re.I,
    )
    events = []
    for source, text in logs.items():
        for line_no, line in enumerate(text.splitlines(), 1):
            match = pattern.search(line)
            if match:
                slot_id, task_id, n_gen = map(int, match.groups())
                events.append({
                    "source": source,
                    "line": line_no,
                    "slot_id": slot_id,
                    "task_id": task_id,
                    "n_gen": n_gen,
                })

    by_source = {}
    for event in events:
        by_source.setdefault(event["source"], []).append(event)

    for source, rows in by_source.items():
        keys = []
        for row in rows:
            key = (row["slot_id"], row["task_id"])
            if key not in keys:
                keys.append(key)
        for left_index, left in enumerate(keys):
            left_rows = [x for x in rows if (x["slot_id"], x["task_id"]) == left]
            for right in keys[left_index + 1:]:
                right_rows = [x for x in rows if (x["slot_id"], x["task_id"]) == right]
                # Line-order proof: one request emits decode progress, the other
                # emits decode progress, then the first emits progress again.
                # Sequential non-overlapping decodes cannot produce this.
                left_first, left_last = left_rows[0]["line"], left_rows[-1]["line"]
                right_first, right_last = right_rows[0]["line"], right_rows[-1]["line"]
                interleaved = (
                    left_first < right_first < left_last
                    or right_first < left_first < right_last
                )
                if interleaved:
                    return {
                        "status": "OBSERVED",
                        "active_overlap": True,
                        "resident": True,
                        "queue_only": False,
                        "source": source,
                        "method": "interleaved llama.cpp slot print_timing n_gen events",
                        "tasks": [
                            {
                                "slot_id": left[0],
                                "task_id": left[1],
                                "first_line": left_first,
                                "last_line": left_last,
                                "event_count": len(left_rows),
                            },
                            {
                                "slot_id": right[0],
                                "task_id": right[1],
                                "first_line": right_first,
                                "last_line": right_last,
                                "event_count": len(right_rows),
                            },
                        ],
                        "event_count": len(rows),
                        "limitation": "Positive proof only; absence of interleaving is UNKNOWN, not QUEUE_ONLY.",
                    }

    return {
        "status": UNKNOWN,
        "active_overlap": None,
        "resident": None,
        "queue_only": None,
        "method": "interleaved llama.cpp slot print_timing n_gen events",
        "event_count": len(events),
        "limitation": "No positive decode-interleaving proof found.",
    }


def reconcile_overlap_from_logs(raw, logs=None):
    """Use preserved llama.cpp logs when live /metrics-/slots sampling was blind."""
    raw = Path(raw)
    config_path = raw / "runtime/planned-config.json"
    if not config_path.exists():
        return None
    config = json.loads(config_path.read_text())
    if not (
        config.get("runtime") == "llama.cpp"
        and config.get("topology") == "tp2-shared"
        and config.get("concurrency") == 2
    ):
        return None

    if logs is None:
        logs = {
            str(p.relative_to(raw)): p.read_text(errors="replace")
            for p in sorted((raw / "runtime").glob("server-*.log"))
        }
    log_evidence = llama_log_overlap(logs)
    h.save(raw / "log-overlap-evidence.json", log_evidence)
    if log_evidence.get("active_overlap") is not True:
        return log_evidence

    overlap_path = raw / "overlap-evidence.json"
    overlap = json.loads(overlap_path.read_text()) if overlap_path.exists() else {}
    if overlap.get("active_overlap") is not True:
        overlap["source"] = (
            str(overlap.get("source") or "live sampler")
            + " + llama.cpp server-log decode interleaving fallback"
        )
        overlap["active_overlap"] = True
        overlap["resident"] = True
        overlap["queue_only"] = False
        overlap["log_fallback"] = log_evidence
        h.save(overlap_path, overlap)

    metrics_path = raw / "metrics.json"
    requests_path = raw / "requests.json"
    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    records = json.loads(requests_path.read_text()) if requests_path.exists() else []
    request_pass = bool(records) and all(x.get("verdict") == h.PASS for x in records)
    mechanical_pass = metrics.get("mechanical_output_verdict") == h.PASS

    metrics["server_overlap"] = overlap
    metrics["c2_resident"] = True
    metrics["c2_active"] = True
    metrics["queue_only"] = False
    metrics["concurrency_verdict"] = "PASS_C2_ACTIVE"
    if metrics.get("verdict") == "INCONCLUSIVE" and request_pass and mechanical_pass:
        metrics["verdict"] = "PASS_C2_ACTIVE"
    if metrics:
        h.save(metrics_path, metrics)

    completion_path = raw / "completion.json"
    if completion_path.exists():
        completion = json.loads(completion_path.read_text())
        if completion.get("verdict") == "INCONCLUSIVE" and request_pass and mechanical_pass:
            completion["verdict"] = "PASS_C2_ACTIVE"
            completion["overlap_reconciled_from"] = "log-overlap-evidence.json"
            h.save(completion_path, completion)

    exit_path = raw / "runtime/exit.json"
    if exit_path.exists():
        exit_receipt = json.loads(exit_path.read_text())
        if exit_receipt.get("verdict") == "INCONCLUSIVE" and request_pass and mechanical_pass:
            exit_receipt["verdict"] = "PASS_C2_ACTIVE"
            exit_receipt["overlap_reconciled_from"] = "log-overlap-evidence.json"
            h.save(exit_path, exit_receipt)

    return log_evidence


def metric_delta(before, after, runtime):
    prefix = "llamacpp" if runtime == "llama.cpp" else "vllm"
    names = {"draft_tokens": prefix + ":spec_decode_num_draft_tokens_total",
             "accepted_tokens": prefix + ":spec_decode_num_accepted_tokens_total",
             "draft_count": prefix + ":spec_decode_num_drafts_total"}
    def collect(value, path="root"):
        found = {}
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "/metrics" and isinstance(item, str):
                    found[path] = item
                else:
                    found.update(collect(item, path + "/" + key))
        return found
    def counter(text, name):
        lines = [x for x in text.splitlines() if x.startswith(name + " ") or x.startswith(name + "{")]
        # Multiple label series have no guaranteed aggregation contract here.
        if len(lines) != 1:
            return None
        try:
            return float(lines[0].rsplit(None, 1)[1])
        except ValueError:
            return None
    left, right = collect(before), collect(after)
    rows = {}
    for path in left.keys() | right.keys():
        row = {}
        for key, name in names.items():
            a, b = counter(left.get(path, ""), name), counter(right.get(path, ""), name)
            row[key] = b - a if a is not None and b is not None and b >= a else None
        rows[path] = row
    totals = {key: sum(row[key] for row in rows.values()) if rows and all(row[key] is not None for row in rows.values()) else None for key in names}
    totals["acceptance_ratio"] = (totals["accepted_tokens"] / totals["draft_tokens"]
                                  if totals["draft_tokens"] and totals["accepted_tokens"] is not None else None)
    result = {"aggregate": totals, "backends": rows, "source": runtime + " /metrics before/after measured window"}
    aggregate = result["aggregate"]
    for key, value in list(aggregate.items()):
        if value is not None and value < 0:
            aggregate[key] = None
    if aggregate.get("draft_tokens") is None or aggregate.get("accepted_tokens") is None:
        aggregate["acceptance_ratio"] = None
    result["status"] = "OBSERVED" if all(aggregate.get(k) is not None for k in ("draft_tokens", "accepted_tokens", "draft_count")) else UNKNOWN
    return result


def install_slot_sinks(adapter, raw):
    (Path(raw) / "runtime").mkdir(parents=True, exist_ok=True)
    for i, child in enumerate(getattr(adapter, "backends", [adapter])):
        child._wbs5_slot_sink = Path(raw) / f"runtime/slot-progress-{i}.jsonl"


def persist_slot_sample(path, sample):
    rows = slot_rows(sample.get("slots"), sample["monotonic_s"], Path(path).stem)
    with Path(path).open("a") as stream:
        stream.write(json.dumps({"monotonic_s": sample["monotonic_s"], "rows": rows,
                                 "status": "OBSERVED" if rows else UNKNOWN}) + "\n")
        stream.flush()


def metric_receipt(config, metrics, records):
    counts = [r.get("actual_output_tokens") for r in records]
    total = sum(counts) if counts and all(type(x) is int for x in counts) else None
    keys = ("ttft_ms", "prefill_tps", "mean_request_decode_tps", "aggregate_decode_tps",
            "end_to_end_output_tps", "batch_wall_s", "peak_vram_gpu0_mib", "peak_vram_gpu1_mib",
            "c2_active", "queue_only", "mechanical_output_verdict")
    return {"schema_version": 1, "candidate_id": config["candidate_id"],
            "run_identity": config["run_identity"], "workload_sha256": config["workload_manifest_sha256"],
            "launch_command": config["launch_command"], "effective_environment": config["effective_environment"],
            "container_environment_overrides": config["container_environment_overrides"],
            "resolved_environment_receipt": "runtime/effective-environment.json",
            "normalized_delta_from_r0": config["normalized_delta_from_r0"],
            **{key: metrics.get(key) for key in keys}, "total_output_tokens": total,
            "metric_status": {key: "OBSERVED" if metrics.get(key) is not None else UNKNOWN for key in keys},
            "requests": [{key: r.get(key) for key in ("request_id", "actual_output_tokens", "ttft_ms", "prefill_tps", "decode_tps", "verdict")} for r in records],
            "post_health": None, "telemetry": "runtime/gpu-telemetry.jsonl",
            "telemetry_fields": ["power.draw", "temperature.gpu", "clocks.sm", "clocks.mem", "utilization.gpu"],
            "limitation": "VRAM peak sampled every 0.5s; power/temp/clocks sampled every 2s. TPS definitions unchanged."}


def finalize(raw):
    """Called after owned server cleanup; never modifies any other experiment."""
    raw = Path(raw)
    config_path = raw / "runtime/planned-config.json"
    config = json.loads(config_path.read_text())
    if config.get("phase") != "WBS5":
        return
    logs = {str(p.relative_to(raw)): p.read_text(errors="replace") for p in sorted((raw / "runtime").glob("server-*.log"))}
    h.save(raw / "graph-evidence.json", graph_evidence(logs))
    reconcile_overlap_from_logs(raw, logs)
    metrics = json.loads((raw / "metrics.json").read_text()) if (raw / "metrics.json").exists() else {}
    records = json.loads((raw / "requests.json").read_text()) if (raw / "requests.json").exists() else []
    receipt = metric_receipt(config, metrics, records)
    if (raw / "health-after.json").exists():
        receipt["post_health"] = json.loads((raw / "health-after.json").read_text())
    receipt["graph_evidence"] = "graph-evidence.json"
    if (raw / "log-overlap-evidence.json").exists():
        receipt["log_overlap_evidence"] = "log-overlap-evidence.json"
    receipt["slot_progress"] = "slot-progress.json"
    receipt["speculative_evidence"] = "speculative-evidence.json"
    receipt["gpu_telemetry_summary"] = telemetry_summary(raw / "runtime/gpu-telemetry.jsonl")
    h.save(raw / "wbs5-evidence.json", receipt)
    # Startup failures still get a complete schema, with UNKNOWN observations.
    if not (raw / "slot-progress.json").exists():
        h.save(raw / "slot-progress.json", {"status": UNKNOWN, "samples": []})
    if not (raw / "speculative-evidence.json").exists():
        h.save(raw / "speculative-evidence.json", {"status": UNKNOWN, "aggregate": {
            "draft_tokens": None, "accepted_tokens": None, "draft_count": None, "acceptance_ratio": None}})
