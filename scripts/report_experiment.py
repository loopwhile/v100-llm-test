#!/usr/bin/env python3
"""Publish one raw experiment into Markdown + normalized CSVs atomically enough to recover."""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
from pathlib import Path
import re

SUMMARY_FIELDS = [
    "experiment_id","date","model","runtime","runtime_revision","backend_variant",
    "weight_quant","kv_cache","speculative","ngram","context_tokens","concurrency",
    "topology","verdict","ttft_ms","prefill_tps","mean_request_decode_tps",
    "aggregate_decode_tps","end_to_end_output_tps","batch_wall_s",
    "peak_vram_gpu0_mib","peak_vram_gpu1_mib","notes",
]
COMPARISON_FIELDS = [
    "experiment_id","model","runtime","backend_variant","weight","kv","spec","ngram",
    "topology","context_per_agent","concurrency","c1_128k","c2_resident","c2_active",
    "queue_only","ttft_ms","request_decode_tps","aggregate_decode_tps",
    "peak_vram_gpu0_mib","peak_vram_gpu1_mib","verdict","key_note",
]


def _read(path):
    return json.loads(Path(path).read_text())


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def _csv_text(fields, rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _load_rows(path, fields):
    path = Path(path)
    if not path.exists() or not path.read_text().strip():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != fields:
            raise ValueError(f"CSV schema mismatch: {path}")
        return list(reader)


def recover(root):
    root = Path(root)
    journal = root / "results/.publication.json"
    if not journal.exists():
        return False
    payload = _read(journal)
    for relative, text in payload["writes"].items():
        atomic_text(root / relative, text)
    journal.unlink()
    return True


def _slug(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "model"


def _bool_text(value):
    if value is None:
        return ""
    return "true" if value else "false"


def _report(config, metrics, completion, raw_dir):
    verdict = completion["verdict"]
    overlap = metrics.get("server_overlap") or {}
    lines = [
        f"# {config['experiment_id']}",
        "",
        "## 실험 식별 정보",
        "",
        f"- 실행 일시: {completion.get('completed_at_utc','')}",
        f"- 판정: **{verdict}**",
        f"- 모델: {config['model']}",
        f"- 런타임: {config['runtime']}",
        f"- Runtime revision: {config['runtime_revision']}",
        "",
        "## 서빙 설정",
        "",
        f"- Weight: {config['weight_quant']}",
        f"- KV: {config['kv_cache']}",
        f"- Speculative: {config['speculative']}",
        f"- ngram: {config['ngram']}",
        f"- Topology: {config['topology']}",
        f"- Context per agent: {config['context_tokens']}",
        f"- Concurrency: C{config['concurrency']}",
        f"- Prefix cache: {config['prefix_cache_lane']}",
        f"- measured_repetitions: {config.get('measured_repetitions',1)}",
        "",
        "## Capacity / Concurrency",
        "",
        f"- C1 128K: {_bool_text(metrics.get('c1_128k'))}",
        f"- C2 resident: {_bool_text(metrics.get('c2_resident'))}",
        f"- C2 active: {_bool_text(metrics.get('c2_active'))}",
        f"- Queue only: {_bool_text(metrics.get('queue_only'))}",
        f"- Overlap source: {overlap.get('source','')}",
        "",
        "## 성능 결과",
        "",
        f"- TTFT: {metrics.get('ttft_ms')}",
        f"- Prefill tok/s: {metrics.get('prefill_tps')}",
        f"- Mean request decode tok/s: {metrics.get('mean_request_decode_tps')}",
        f"- Aggregate decode tok/s: {metrics.get('aggregate_decode_tps')}",
        f"- End-to-end output tok/s: {metrics.get('end_to_end_output_tps')}",
        f"- Batch wall: {metrics.get('batch_wall_s')}",
        "",
        "## 증거 경로",
        "",
        f"- Raw artifact: {raw_dir.as_posix()}",
        "- config.json, workload.json, payloads.json, tokenization.json",
        "- requests.json, overlap-evidence.json, metrics.json",
        "- health-before.json, health-after.json, server snapshots",
        "",
        "## 결론",
        "",
        "이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.",
        "",
    ]
    return "\n".join(lines)


def publish(root, raw_dir):
    root = Path(root)
    raw_dir = Path(raw_dir)
    recover(root)
    config = _read(raw_dir / "config.json")
    metrics = _read(raw_dir / "metrics.json")
    completion = _read(raw_dir / "completion.json")
    experiment_id = config["experiment_id"]
    if completion.get("experiment_id") != experiment_id:
        raise ValueError("completion experiment_id mismatch")

    summary_path = root / "results/summary.csv"
    comparison_path = root / "reports/comparison.csv"
    summary_rows = _load_rows(summary_path, SUMMARY_FIELDS)
    comparison_rows = _load_rows(comparison_path, COMPARISON_FIELDS)
    if any(row["experiment_id"] == experiment_id for row in summary_rows + comparison_rows):
        raise ValueError("experiment_id already published")

    peak0 = metrics.get("peak_vram_gpu0_mib")
    peak1 = metrics.get("peak_vram_gpu1_mib")
    summary_row = {
        "experiment_id": experiment_id,
        "date": completion.get("completed_at_utc", ""),
        "model": config["model"],
        "runtime": config["runtime"],
        "runtime_revision": config["runtime_revision"],
        "backend_variant": config.get("backend_variant", "stock"),
        "weight_quant": config["weight_quant"],
        "kv_cache": config["kv_cache"],
        "speculative": config["speculative"],
        "ngram": config["ngram"],
        "context_tokens": config["context_tokens"],
        "concurrency": config["concurrency"],
        "topology": config["topology"],
        "verdict": completion["verdict"],
        "ttft_ms": metrics.get("ttft_ms"),
        "prefill_tps": metrics.get("prefill_tps"),
        "mean_request_decode_tps": metrics.get("mean_request_decode_tps"),
        "aggregate_decode_tps": metrics.get("aggregate_decode_tps"),
        "end_to_end_output_tps": metrics.get("end_to_end_output_tps"),
        "batch_wall_s": metrics.get("batch_wall_s"),
        "peak_vram_gpu0_mib": peak0,
        "peak_vram_gpu1_mib": peak1,
        "notes": config.get("notes", ""),
    }
    comparison_row = {
        "experiment_id": experiment_id,
        "model": config["model"],
        "runtime": config["runtime"],
        "backend_variant": config.get("backend_variant", "stock"),
        "weight": config["weight_quant"],
        "kv": config["kv_cache"],
        "spec": config["speculative"],
        "ngram": config["ngram"],
        "topology": config["topology"],
        "context_per_agent": config["context_tokens"],
        "concurrency": config["concurrency"],
        "c1_128k": _bool_text(metrics.get("c1_128k")),
        "c2_resident": _bool_text(metrics.get("c2_resident")),
        "c2_active": _bool_text(metrics.get("c2_active")),
        "queue_only": _bool_text(metrics.get("queue_only")),
        "ttft_ms": metrics.get("ttft_ms"),
        "request_decode_tps": metrics.get("mean_request_decode_tps"),
        "aggregate_decode_tps": metrics.get("aggregate_decode_tps"),
        "peak_vram_gpu0_mib": peak0,
        "peak_vram_gpu1_mib": peak1,
        "verdict": completion["verdict"],
        "key_note": config.get("notes", ""),
    }

    report_rel = Path("reports") / _slug(config["model"]) / f"{experiment_id}.md"
    if (root / report_rel).exists():
        raise ValueError("report already exists")
    writes = {
        report_rel.as_posix(): _report(config, metrics, completion, raw_dir),
        "results/summary.csv": _csv_text(SUMMARY_FIELDS, summary_rows + [summary_row]),
        "reports/comparison.csv": _csv_text(COMPARISON_FIELDS, comparison_rows + [comparison_row]),
    }
    journal = root / "results/.publication.json"
    atomic_text(journal, json.dumps({"writes": writes}, ensure_ascii=False, indent=2))
    for relative, text in writes.items():
        atomic_text(root / relative, text)
    journal.unlink()
    return report_rel.as_posix()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(publish(args.root, args.raw_dir))


if __name__ == "__main__":
    main()
