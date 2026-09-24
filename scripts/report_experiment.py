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
    "peak_vram_gpu0_mib","peak_vram_gpu1_mib","gateway_runtime","gateway_revision",
    "gateway_routing","notes",
]
COMPARISON_FIELDS = [
    "experiment_id","model","runtime","backend_variant","weight","kv","spec","ngram",
    "topology","context_per_agent","concurrency","c1_128k","c2_resident","c2_active",
    "queue_only","ttft_ms","request_decode_tps","aggregate_decode_tps",
    "peak_vram_gpu0_mib","peak_vram_gpu1_mib","gateway_runtime","gateway_revision",
    "gateway_routing","verdict","key_note",
]

MODEL_SLUG_MAP = {
    "qwen3.8-27b": "qwen3-8-27b",
    "qwen3-8-27b": "qwen3-8-27b",
    "ornith-1.5-9b": "ornith-1.5-9b",
    "ornith-1-5-9b": "ornith-1.5-9b",
    "ornith-1.5-35b-a3b": "ornith-1.5-35b-a3b",
    "ornith-1-5-35b-a3b": "ornith-1.5-35b-a3b",
    "gemma4-26b-a4b": "gemma4-26b-a4b",
    "gemma4-26b-a4b-it-qat": "gemma4-26b-a4b",
    "gemma-4-26b-a4b-nvfp4": "gemma4-26b-a4b",
}


def _read(path):
    return json.loads(Path(path).read_text())


def _resolve_verdicts(raw_dir, metrics, completion):
    """Resolve raw harness, capacity, integrity, and final semantic verdicts.

    Raw metrics/completion remain immutable execution evidence. When an
    acceptance-review exists, its semantic verdict is authoritative for
    publication while the raw harness verdict is preserved separately.
    """
    raw_dir = Path(raw_dir)
    audit_path = raw_dir / "acceptance-review.json"
    audit = _read(audit_path) if audit_path.exists() else None

    harness_verdict = completion.get("verdict") or metrics.get("verdict")
    final_verdict = (audit.get("verdict") if audit else None) or harness_verdict
    capacity_verdict = audit.get("capacity_verdict") if audit else None
    integrity_verdict = audit.get("integrity_verdict") if audit else None

    if capacity_verdict is None and harness_verdict == "PASS_C1_128K":
        capacity_verdict = "PASS_C1_128K"
    if integrity_verdict is None:
        if final_verdict == "FAIL_OUTPUT":
            integrity_verdict = "FAIL_OUTPUT"
        elif final_verdict == "PASS_C1_128K":
            integrity_verdict = "PASS"

    return {
        "harness_verdict": harness_verdict,
        "capacity_verdict": capacity_verdict,
        "integrity_verdict": integrity_verdict,
        "final_verdict": final_verdict,
    }


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
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
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
    normalized = value.strip().lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    if normalized in MODEL_SLUG_MAP:
        return MODEL_SLUG_MAP[normalized]
    if hyphenated in MODEL_SLUG_MAP:
        return MODEL_SLUG_MAP[hyphenated]
    if "qwen3" in hyphenated or "q38" in hyphenated:
        return "qwen3-8-27b"
    if "ornith-1-5-9b" in hyphenated or "ornith-1.5-9b" in normalized or "orn15-9b" in hyphenated:
        return "ornith-1.5-9b"
    if "ornith-1-5-35b" in hyphenated or "ornith-1.5-35b" in normalized or "orn15-35b" in hyphenated:
        return "ornith-1.5-35b-a3b"
    if "gemma" in hyphenated:
        return "gemma4-26b-a4b"
    return hyphenated or "model"


def _bool_text(value):
    if value is None:
        return ""
    return "true" if value else "false"


def _format_vram(peak0, peak1):
    def _val(v):
        if v is None:
            return "None"
        if isinstance(v, (int, float)):
            if float(v).is_integer():
                return f"{int(v):,} MiB"
            return f"{v:,.1f} MiB"
        return f"{v} MiB"

    if peak0 is not None and peak1 is not None:
        return f"GPU0 {_val(peak0)} / GPU1 {_val(peak1)}"
    elif peak0 is not None:
        return f"GPU0 {_val(peak0)}"
    return "None"


def _extract_metrics(raw_dir, config, metrics, completion, final_verdict=None):
    metrics = dict(metrics)
    requests_path = raw_dir / "requests.json"
    requests = _read(requests_path) if requests_path.exists() else []

    reqs_with_ttft = [r for r in requests if r.get("ttft_ms") is not None]
    reqs_with_dec = [r for r in requests if r.get("decode_tps") is not None]
    reqs_with_pref = [r for r in requests if r.get("prefill_tps") is not None]

    verdict = final_verdict or completion.get("verdict")
    if verdict == "FAIL_OUTPUT":
        if metrics.get("ttft_ms") is None and reqs_with_ttft:
            metrics["ttft_ms"] = sum(r["ttft_ms"] for r in reqs_with_ttft) / len(reqs_with_ttft)

        if metrics.get("mean_request_decode_tps") is None and reqs_with_dec:
            metrics["mean_request_decode_tps"] = sum(r["decode_tps"] for r in reqs_with_dec) / len(reqs_with_dec)

        if metrics.get("prefill_tps") is None and reqs_with_pref:
            metrics["prefill_tps"] = sum(r["prefill_tps"] for r in reqs_with_pref) / len(reqs_with_pref)

        if metrics.get("aggregate_decode_tps") is None:
            firsts = [r["first_abs"] for r in requests if r.get("first_abs")]
            ends = [r["end_abs"] for r in requests if r.get("end_abs")]
            tokens = sum(r.get("actual_output_tokens") or 0 for r in requests)
            window = max(ends) - min(firsts) if firsts and ends else None
            if window and window > 0:
                metrics["aggregate_decode_tps"] = tokens / window
            elif config.get("concurrency") == 1 and metrics.get("mean_request_decode_tps") is not None:
                metrics["aggregate_decode_tps"] = metrics["mean_request_decode_tps"]

        if metrics.get("end_to_end_output_tps") in (None, 0.0):
            batch_wall = metrics.get("batch_wall_s")
            tokens = sum(r.get("actual_output_tokens") or 0 for r in requests)
            if batch_wall and batch_wall > 0 and tokens > 0:
                metrics["end_to_end_output_tps"] = tokens / batch_wall

        if config.get("concurrency") == 1 and config.get("context_tokens") == 131072:
            metrics["c1_128k"] = True

    return metrics


def _report(config, metrics, completion, raw_dir, verdicts=None):
    audit_path = raw_dir / "acceptance-review.json"
    audit = _read(audit_path) if audit_path.exists() else None

    verdicts = verdicts or _resolve_verdicts(raw_dir, metrics, completion)
    verdict = verdicts["final_verdict"]
    overlap = metrics.get("server_overlap") or {}
    gateway = config.get("gateway") or {}
    concurrency = config.get("concurrency", 1)
    peak0 = metrics.get("peak_vram_gpu0_mib")
    peak1 = metrics.get("peak_vram_gpu1_mib")

    verdict_display = f"**{verdict}**"
    if audit and audit.get("verdict_display"):
        verdict_display = audit["verdict_display"]
    elif audit and audit.get("capacity_verdict") == "PASS_C1_128K" and verdict == "FAIL_OUTPUT":
        verdict_display = f"**{verdict}** (128K Capacity PASS, Output-Integrity FAIL)"

    lines = [
        f"# {config['experiment_id']}",
        "",
        "## 실험 식별 정보",
        "",
        f"- 실행 일시: {completion.get('completed_at_utc','')}",
        f"- 판정: {verdict_display}",
        f"- 모델: {config['model']}",
        f"- 런타임: {config['runtime']}",
        f"- Runtime revision: {config['runtime_revision']}",
    ]

    if verdicts["harness_verdict"] != verdict:
        lines.extend([
            f"- Harness verdict (raw): {verdicts['harness_verdict']}",
            f"- Capacity verdict: {verdicts['capacity_verdict'] or ''}",
            f"- Output-integrity verdict: {verdicts['integrity_verdict'] or ''}",
            f"- Final verdict (semantic audit): {verdict}",
        ])

    if gateway.get("runtime") or gateway.get("endpoint"):
        lines.extend([
            f"- Gateway runtime: {gateway.get('runtime','')}",
            f"- Gateway revision: {gateway.get('runtime_revision','')}",
            f"- Gateway image: {gateway.get('image','')}",
            f"- Gateway endpoint: {gateway.get('endpoint','')}",
            f"- Gateway routing: {gateway.get('routing_strategy','')}",
            f"- Gateway backend max parallel: {gateway.get('backend_max_parallel_requests','')}",
        ])

    lines.extend([
        "",
        "## 서빙 설정",
        "",
        f"- Weight: {config['weight_quant']}",
        f"- KV: {config['kv_cache']}",
        f"- Speculative: {config['speculative']}",
        f"- ngram: {config['ngram']}",
        f"- Topology: {config['topology']}",
        f"- Context per agent: {config['context_tokens']}",
        f"- Concurrency: C{concurrency}",
        f"- Prefix cache: {config['prefix_cache_lane']}",
        f"- measured_repetitions: {config.get('measured_repetitions',1)}",
        "",
        "## Capacity / Concurrency",
        "",
    ])

    if concurrency == 1:
        lines.append(f"- C1 128K: {_bool_text(metrics.get('c1_128k'))}")
        if overlap.get("source"):
            lines.append(f"- Overlap source: {overlap.get('source','')}")
    else:
        lines.extend([
            f"- C2 resident: {_bool_text(metrics.get('c2_resident'))}",
            f"- C2 active: {_bool_text(metrics.get('c2_active'))}",
            f"- Queue only: {_bool_text(metrics.get('queue_only'))}",
        ])
        if overlap.get("source"):
            lines.append(f"- Overlap source: {overlap.get('source','')}")

    lines.extend([
        "",
        "## 성능 결과",
        "",
        f"- TTFT: {metrics.get('ttft_ms')}",
        f"- Prefill tok/s: {metrics.get('prefill_tps')}",
        f"- Mean request decode tok/s: {metrics.get('mean_request_decode_tps')}",
        f"- Aggregate decode tok/s: {metrics.get('aggregate_decode_tps')}",
        f"- End-to-end output tok/s: {metrics.get('end_to_end_output_tps')}",
        f"- Batch wall: {metrics.get('batch_wall_s')}",
        f"- Peak VRAM: {_format_vram(peak0, peak1)}",
        "",
        "## 증거 경로",
        "",
        f"- Raw artifact: {raw_dir.as_posix()}",
        "- config.json, workload.json, payloads.json, tokenization.json",
        "- requests.json, overlap-evidence.json, metrics.json",
        "- health-before.json, health-after.json, server snapshots",
        "",
    ])

    if audit:
        lines.append("## 결론 및 Semantic Audit")
        lines.append("")
        if audit.get("capacity_summary"):
            lines.append(f"- **128K Capacity**: {audit['capacity_summary']}")
        elif audit.get("capacity_verdict") == "PASS_C1_128K":
            lines.append(f"- **128K Capacity**: PASS (128K prefill/decode 성공, Peak VRAM {_format_vram(peak0, peak1)}로 OOM 없음, post-health 정상).")

        if audit.get("integrity_summary"):
            lines.append(f"- **Output Integrity**: {audit['integrity_summary']}")
        elif audit.get("content_review"):
            lines.append(f"- **Output Integrity**: {audit['content_review']}")

        if audit.get("diagnostic_summary"):
            lines.append(f"- **실패 원인 및 진단 요약**: {audit['diagnostic_summary']}")

        lines.extend([
            f"- 상세 감사 기록: `{audit_path.as_posix()}`",
            "- 이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.",
            "",
        ])
    else:
        lines.extend([
            "## 결론",
            "",
            "이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.",
            "",
        ])

    return "\n".join(lines)


def _update_or_append(rows, new_row, key="experiment_id"):
    found = False
    new_rows = []
    for r in rows:
        if r.get(key) == new_row.get(key):
            new_rows.append(new_row)
            found = True
        else:
            new_rows.append(r)
    if not found:
        new_rows.append(new_row)
    return new_rows


def publish(root, raw_dir, overwrite=False):
    root = Path(root)
    raw_dir = Path(raw_dir)
    recover(root)
    config = _read(raw_dir / "config.json")
    raw_metrics = _read(raw_dir / "metrics.json")
    completion = _read(raw_dir / "completion.json")
    experiment_id = config["experiment_id"]
    if completion.get("experiment_id") != experiment_id:
        raise ValueError("completion experiment_id mismatch")

    verdicts = _resolve_verdicts(raw_dir, raw_metrics, completion)
    metrics = _extract_metrics(
        raw_dir,
        config,
        raw_metrics,
        completion,
        final_verdict=verdicts["final_verdict"],
    )

    summary_path = root / "results/summary.csv"
    comparison_path = root / "reports/comparison.csv"
    summary_rows = _load_rows(summary_path, SUMMARY_FIELDS)
    comparison_rows = _load_rows(comparison_path, COMPARISON_FIELDS)

    already_published = any(row["experiment_id"] == experiment_id for row in summary_rows + comparison_rows)
    if not overwrite and already_published:
        raise ValueError("experiment_id already published")

    report_rel = Path("reports") / _slug(config["model"]) / f"{experiment_id}.md"
    if not overwrite and (root / report_rel).exists():
        raise ValueError("report already exists")

    peak0 = metrics.get("peak_vram_gpu0_mib")
    peak1 = metrics.get("peak_vram_gpu1_mib")
    gateway = config.get("gateway") or {}

    audit_path = raw_dir / "acceptance-review.json"
    audit = _read(audit_path) if audit_path.exists() else None
    verdict = verdicts["final_verdict"]
    note_text = (audit.get("key_note") or audit.get("note") if audit else None) or config.get("notes", "")

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
        "verdict": verdict,
        "ttft_ms": metrics.get("ttft_ms"),
        "prefill_tps": metrics.get("prefill_tps"),
        "mean_request_decode_tps": metrics.get("mean_request_decode_tps"),
        "aggregate_decode_tps": metrics.get("aggregate_decode_tps"),
        "end_to_end_output_tps": metrics.get("end_to_end_output_tps"),
        "batch_wall_s": metrics.get("batch_wall_s"),
        "peak_vram_gpu0_mib": peak0,
        "peak_vram_gpu1_mib": peak1,
        "gateway_runtime": gateway.get("runtime", ""),
        "gateway_revision": gateway.get("runtime_revision", ""),
        "gateway_routing": gateway.get("routing_strategy", ""),
        "notes": note_text,
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
        "gateway_runtime": gateway.get("runtime", ""),
        "gateway_revision": gateway.get("runtime_revision", ""),
        "gateway_routing": gateway.get("routing_strategy", ""),
        "verdict": verdict,
        "key_note": note_text,
    }

    if overwrite:
        summary_rows = _update_or_append(summary_rows, summary_row)
        comparison_rows = _update_or_append(comparison_rows, comparison_row)
    else:
        summary_rows = summary_rows + [summary_row]
        comparison_rows = comparison_rows + [comparison_row]

    writes = {
        report_rel.as_posix(): _report(config, metrics, completion, raw_dir, verdicts=verdicts),
        "results/summary.csv": _csv_text(SUMMARY_FIELDS, summary_rows),
        "reports/comparison.csv": _csv_text(COMPARISON_FIELDS, comparison_rows),
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
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing report and update CSV entries")
    args = parser.parse_args()
    print(publish(args.root, args.raw_dir, overwrite=args.overwrite))


if __name__ == "__main__":
    main()
