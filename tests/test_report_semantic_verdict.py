#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import report_experiment as report


class ReportSemanticVerdictTests(unittest.TestCase):
    def _write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    def test_semantic_audit_overrides_publication_without_mutating_raw_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "results/raw/EXP-SEMANTIC-OVERRIDE"
            raw.mkdir(parents=True)

            config = {
                "experiment_id": "EXP-SEMANTIC-OVERRIDE",
                "model": "Qwen3.8-27B",
                "runtime": "1Cat-vLLM",
                "runtime_revision": "1.5.0",
                "backend_variant": "stock",
                "weight_quant": "NVFP4",
                "kv_cache": "fp8_e4m3",
                "speculative": "target-only",
                "ngram": "N/A",
                "topology": "tp2-shared",
                "context_tokens": 131072,
                "concurrency": 1,
                "prefix_cache_lane": "cold-independent",
                "notes": "semantic override regression",
            }
            metrics = {
                "c1_128k": True,
                "ttft_ms": 739000.0,
                "prefill_tps": None,
                "mean_request_decode_tps": 9.75,
                "aggregate_decode_tps": 9.75,
                "end_to_end_output_tps": 2.15,
                "batch_wall_s": 950.0,
                "peak_vram_gpu0_mib": 15287.0,
                "peak_vram_gpu1_mib": 15287.0,
                "server_overlap": {},
                "verdict": "PASS_C1_128K",
            }
            completion = {
                "experiment_id": config["experiment_id"],
                "completed_at_utc": "2026-09-25T00:00:00+00:00",
                "verdict": "PASS_C1_128K",
            }
            audit = {
                "verdict": "FAIL_OUTPUT",
                "harness_verdict": "PASS_C1_128K",
                "capacity_verdict": "PASS_C1_128K",
                "integrity_verdict": "FAIL_OUTPUT",
                "key_note": "semantic audit overrode harness pass",
            }

            self._write_json(raw / "config.json", config)
            self._write_json(raw / "metrics.json", metrics)
            self._write_json(raw / "completion.json", completion)
            self._write_json(raw / "acceptance-review.json", audit)
            self._write_json(raw / "requests.json", [])

            raw_metrics_before = (raw / "metrics.json").read_bytes()
            report_rel = report.publish(root, raw)

            self.assertEqual((raw / "metrics.json").read_bytes(), raw_metrics_before)

            with (root / "results/summary.csv").open(newline="", encoding="utf-8") as stream:
                summary = next(csv.DictReader(stream))
            self.assertEqual(summary["verdict"], "FAIL_OUTPUT")

            with (root / "reports/comparison.csv").open(newline="", encoding="utf-8") as stream:
                comparison = next(csv.DictReader(stream))
            self.assertEqual(comparison["c1_128k"], "true")
            self.assertEqual(comparison["verdict"], "FAIL_OUTPUT")

            rendered = (root / report_rel).read_text()
            self.assertIn("판정: **FAIL_OUTPUT** (128K Capacity PASS, Output-Integrity FAIL)", rendered)
            self.assertIn("Harness verdict (raw): PASS_C1_128K", rendered)
            self.assertIn("Capacity verdict: PASS_C1_128K", rendered)
            self.assertIn("Output-integrity verdict: FAIL_OUTPUT", rendered)
            self.assertIn("Final verdict (semantic audit): FAIL_OUTPUT", rendered)


if __name__ == "__main__":
    unittest.main()
