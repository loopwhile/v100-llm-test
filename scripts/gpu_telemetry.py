#!/usr/bin/env python3
"""Bounded, read-only GPU telemetry collector for v100-llm-test."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import time
from typing import Any

QUERY_FIELDS = (
    "uuid",
    "index",
    "memory.used",
    "memory.total",
    "power.draw",
    "power.limit",
    "temperature.gpu",
    "clocks.sm",
    "clocks.mem",
    "utilization.gpu",
    "persistence_mode",
)

NUMERIC_NAMES = (
    "memory_used_mib",
    "memory_total_mib",
    "power_w",
    "power_limit_w",
    "temperature_c",
    "sm_clock_mhz",
    "memory_clock_mhz",
    "utilization_pct",
)

COMMAND = [
    "nvidia-smi",
    "--query-gpu=" + ",".join(QUERY_FIELDS),
    "--format=csv,noheader,nounits",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def short_hostname() -> str:
    return socket.gethostname().split(".", 1)[0]


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    with tmp.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def parse_number(raw: str, *, maximum: float | None = None) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    if maximum is not None and value > maximum:
        return None
    return value


def parse_gpu_csv(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw_row in csv.reader(io.StringIO(text)):
        row = [item.strip() for item in raw_row]
        if len(row) != len(QUERY_FIELDS):
            raise ValueError(
                f"unexpected nvidia-smi column count: {len(row)} != {len(QUERY_FIELDS)}"
            )

        uuid, index_raw = row[0], row[1]
        if not uuid.startswith("GPU-") or uuid in seen:
            raise ValueError("invalid or duplicate GPU UUID")
        if not index_raw.isdigit():
            raise ValueError("invalid GPU index")
        seen.add(uuid)

        numeric_raw = row[2:10]
        metrics: dict[str, float | bool | None] = {}
        for name, value in zip(NUMERIC_NAMES, numeric_raw):
            metrics[name] = parse_number(
                value, maximum=100.0 if name == "utilization_pct" else None
            )

        persistence_raw = row[10]
        if persistence_raw == "Enabled":
            persistence: bool | None = True
        elif persistence_raw == "Disabled":
            persistence = False
        else:
            persistence = None

        rows.append(
            {
                "uuid": uuid,
                "index": int(index_raw),
                "metrics": {**metrics, "persistence_enabled": persistence},
            }
        )

    if len(rows) != 2 or len({row["index"] for row in rows}) != 2:
        raise ValueError("expected exactly two distinct GPUs")

    return sorted(rows, key=lambda item: item["index"])


def read_gpus(timeout_s: float) -> list[dict[str, Any]]:
    result = subprocess.run(
        COMMAND,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=True,
    )
    return parse_gpu_csv(result.stdout)


def summarize(samples: list[dict[str, Any]], *, duration_s: float, interval_s: float) -> dict[str, Any]:
    by_gpu: dict[str, dict[str, list[float]]] = {}

    for sample in samples:
        for gpu in sample["gpus"]:
            bucket = by_gpu.setdefault(gpu["uuid"], {name: [] for name in NUMERIC_NAMES})
            for name in NUMERIC_NAMES:
                value = gpu["metrics"].get(name)
                if isinstance(value, (int, float)):
                    bucket[name].append(float(value))

    gpu_summary: dict[str, Any] = {}
    for uuid, metrics in by_gpu.items():
        gpu_summary[uuid] = {
            name: {
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "valid_samples": len(values),
            }
            for name, values in metrics.items()
        }

    scheduled = math.ceil(duration_s / interval_s)
    return {
        "attempted_samples": len(samples),
        "scheduled_samples": scheduled,
        "skipped_slots": max(0, scheduled - len(samples)),
        "gpu_query_failures": sum(1 for sample in samples if sample.get("gpu_error") is not None),
        "gpu_summary": gpu_summary,
        "limitation": (
            "sampled minima/maxima can miss between-sample peaks; "
            "this collector does not prove scheduler-side request overlap or prefix-cache hits"
        ),
    }


def collect(
    output: Path,
    *,
    target_host: str,
    phase: str,
    duration_s: float,
    interval_s: float,
    query_timeout_s: float,
) -> dict[str, Any]:
    actual_host = short_hostname()
    if target_host != "p520-llm" or actual_host != target_host:
        raise ValueError(
            f"collector refused: target={target_host!r}, actual_host={actual_host!r}"
        )

    for name, value in (
        ("duration_s", duration_s),
        ("interval_s", interval_s),
        ("query_timeout_s", query_timeout_s),
    ):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")

    if duration_s > 3600:
        raise ValueError("duration_s may not exceed 3600 seconds")
    if interval_s < 0.1:
        raise ValueError("interval_s may not be lower than 0.1 seconds")
    if duration_s / interval_s > 36000:
        raise ValueError("collection may not exceed 36000 scheduled samples")

    allowed_phases = {"idle", "warmup", "measurement", "after", "stability"}
    if phase not in allowed_phases:
        raise ValueError(f"phase must be one of {sorted(allowed_phases)}")

    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()

    manifest = {
        "schema_version": "1.0",
        "collector": "scripts/gpu_telemetry.py",
        "target_host": target_host,
        "actual_host": actual_host,
        "phase": phase,
        "started_at_utc": utc_now(),
        "python": platform.python_version(),
        "duration_s": duration_s,
        "interval_s": interval_s,
        "query_timeout_s": query_timeout_s,
        "nvidia_smi_command": COMMAND,
        "policy": "read-only observation; this script never sets power, clocks or persistence",
    }
    atomic_json(output / "manifest.json", manifest)

    samples: list[dict[str, Any]] = []
    status = "completed"
    slot = 0

    try:
        with (output / "samples.jsonl").open("xb") as stream:
            while slot * interval_s < duration_s:
                scheduled_at = start + slot * interval_s
                time.sleep(max(0.0, scheduled_at - time.monotonic()))
                offset = time.monotonic() - start
                if offset >= duration_s:
                    break

                sample: dict[str, Any] = {
                    "slot": slot,
                    "phase": phase,
                    "scheduled_offset_s": slot * interval_s,
                    "observed_offset_s": offset,
                    "observed_at_utc": utc_now(),
                    "gpus": [],
                    "gpu_error": None,
                }

                remaining = max(0.05, duration_s - offset)
                try:
                    sample["gpus"] = read_gpus(min(query_timeout_s, remaining))
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    sample["gpu_error"] = f"{type(exc).__name__}: {str(exc)[:500]}"

                sample["finished_offset_s"] = time.monotonic() - start
                stream.write(
                    (json.dumps(sample, sort_keys=True, separators=(",", ":")) + "\n").encode()
                )
                stream.flush()
                os.fsync(stream.fileno())
                samples.append(sample)

                slot = max(
                    slot + 1,
                    math.ceil((time.monotonic() - start) / interval_s),
                )
    except KeyboardInterrupt:
        status = "interrupted"

    summary = summarize(samples, duration_s=duration_s, interval_s=interval_s)
    summary.update(
        {
            "schema_version": "1.0",
            "status": status,
            "ended_at_utc": utc_now(),
            "elapsed_s": time.monotonic() - start,
        }
    )
    atomic_json(output / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-host", default="p520-llm", choices=["p520-llm"])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--phase",
        required=True,
        choices=["idle", "warmup", "measurement", "after", "stability"],
    )
    parser.add_argument("--duration-s", required=True, type=float)
    parser.add_argument("--interval-s", default=1.0, type=float)
    parser.add_argument("--query-timeout-s", default=2.0, type=float)
    args = parser.parse_args()

    try:
        result = collect(
            args.output,
            target_host=args.target_host,
            phase=args.phase,
            duration_s=args.duration_s,
            interval_s=args.interval_s,
            query_timeout_s=args.query_timeout_s,
        )
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")

    print(json.dumps(result, sort_keys=True, indent=2))
    return 130 if result["status"] == "interrupted" else 0


if __name__ == "__main__":
    raise SystemExit(main())
