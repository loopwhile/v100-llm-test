"""Offline tests for WBS5 overlap evidence fallbacks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bench_harness as h
import wbs5_evidence as e


class WBS5OverlapTests(unittest.TestCase):
    def test_probe_calls_are_bounded(self):
        adapter = h.HTTPAdapter("http://127.0.0.1:1", "llama.cpp", timeout_s=3600)
        seen = []

        def fake_call(route, body=None, raw=False, timeout_s=None):
            seen.append((route, timeout_s))
            if route == "/metrics":
                return "llamacpp:requests_processing 2\nllamacpp:requests_deferred 0\n"
            if route == "/slots":
                return [
                    {"id": 0, "is_processing": True},
                    {"id": 1, "is_processing": True},
                ]
            raise AssertionError(route)

        adapter.call = fake_call
        sample = adapter._probe_once()
        self.assertEqual(sample["processing"], 2)
        self.assertEqual(seen, [("/metrics", 5.0), ("/slots", 5.0)])

    def test_llama_log_interleaving_proves_active_overlap(self):
        logs = {"runtime/server-0.log": "\n".join([
            "x slot print_timing: id  0 | task 8 | n_gen = 100, tg = 1.0 t/s",
            "x slot print_timing: id  1 | task 9 | n_gen = 80, tg = 8.0 t/s",
            "x slot print_timing: id  0 | task 8 | n_gen = 101, tg = 1.0 t/s",
            "x slot print_timing: id  1 | task 9 | n_gen = 81, tg = 8.0 t/s",
        ])}
        got = e.llama_log_overlap(logs)
        self.assertEqual(got["status"], "OBSERVED")
        self.assertIs(got["active_overlap"], True)
        self.assertIs(got["resident"], True)
        self.assertIs(got["queue_only"], False)

    def test_sequential_decode_remains_unknown(self):
        logs = {"runtime/server-0.log": "\n".join([
            "x slot print_timing: id  0 | task 8 | n_gen = 100",
            "x slot print_timing: id  0 | task 8 | n_gen = 101",
            "x slot print_timing: id  1 | task 9 | n_gen = 80",
            "x slot print_timing: id  1 | task 9 | n_gen = 81",
        ])}
        got = e.llama_log_overlap(logs)
        self.assertEqual(got["status"], e.UNKNOWN)
        self.assertIsNone(got["active_overlap"])

    def test_reconcile_promotes_only_inconclusive_passed_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            runtime = raw / "runtime"
            runtime.mkdir()
            (runtime / "planned-config.json").write_text(json.dumps({
                "runtime": "llama.cpp",
                "topology": "tp2-shared",
                "concurrency": 2,
            }))
            (runtime / "server-0.log").write_text("\n".join([
                "x slot print_timing: id  0 | task 8 | n_gen = 100",
                "x slot print_timing: id  1 | task 9 | n_gen = 80",
                "x slot print_timing: id  0 | task 8 | n_gen = 101",
            ]))
            (runtime / "exit.json").write_text(json.dumps({"exit_code": 0, "verdict": "INCONCLUSIVE"}))
            (raw / "overlap-evidence.json").write_text(json.dumps({
                "source": "sampler",
                "resident": None,
                "active_overlap": None,
                "queue_only": False,
                "sample_count": 2,
            }))
            (raw / "requests.json").write_text(json.dumps([
                {"verdict": "PASS"}, {"verdict": "PASS"}
            ]))
            (raw / "metrics.json").write_text(json.dumps({
                "verdict": "INCONCLUSIVE",
                "mechanical_output_verdict": "PASS",
                "c2_active": None,
                "c2_resident": None,
                "queue_only": False,
            }))
            (raw / "completion.json").write_text(json.dumps({"verdict": "INCONCLUSIVE"}))

            got = e.reconcile_overlap_from_logs(raw)
            self.assertIs(got["active_overlap"], True)
            metrics = json.loads((raw / "metrics.json").read_text())
            completion = json.loads((raw / "completion.json").read_text())
            exit_receipt = json.loads((runtime / "exit.json").read_text())
            self.assertEqual(metrics["verdict"], "PASS_C2_ACTIVE")
            self.assertIs(metrics["c2_active"], True)
            self.assertEqual(completion["verdict"], "PASS_C2_ACTIVE")
            self.assertEqual(exit_receipt["verdict"], "PASS_C2_ACTIVE")


if __name__ == "__main__":
    unittest.main()
