"""Tests for report_experiment.py evidence listing and FAIL verdict display."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import report_experiment as report


def _make_raw(td, files, config=None, metrics=None, completion=None):
    raw = Path(td)
    config = config or {
        "experiment_id": "EXP-V100-TEST-001",
        "model": "test-model",
        "runtime": "llama.cpp",
        "runtime_revision": "test",
        "weight_quant": "Q6_K",
        "kv_cache": "FP16",
        "speculative": "target-only",
        "ngram": "off",
        "topology": "tp2-shared",
        "context_tokens": 131072,
        "concurrency": 1,
        "prefix_cache_lane": "cold",
        "notes": "test",
    }
    metrics = metrics or {"verdict": "PASS_C1_128K", "c1_128k": True}
    completion = completion or {
        "experiment_id": "EXP-V100-TEST-001",
        "verdict": "PASS_C1_128K",
        "completed_at_utc": "2026-09-26T00:00:00+00:00",
    }
    (raw / "config.json").write_text(json.dumps(config))
    (raw / "metrics.json").write_text(json.dumps(metrics))
    (raw / "completion.json").write_text(json.dumps(completion))
    for f in files:
        p = raw / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
    return raw, config, metrics, completion


class TestEvidenceListing(unittest.TestCase):
    def test_completed_experiment_lists_actual_files(self):
        """A completed experiment should list only files that exist."""
        with tempfile.TemporaryDirectory() as td:
            raw, config, metrics, completion = _make_raw(td, [
                "workload.json", "payloads.json", "tokenization.json",
                "requests.json", "overlap-evidence.json",
                "health-before.json", "health-after.json",
                "server-before.json", "server-after.json",
                "gpu-peak.json", "identity.json",
                "runtime/routing-preflight.json",
                "runtime/plan.json",
                "runtime/server-0.log",
                "runtime/server-1.log",
                "runtime/gateway.log",
            ])
            md = report._report(config, metrics, completion, raw)
            self.assertIn("workload.json", md)
            self.assertIn("payloads.json", md)
            self.assertIn("tokenization.json", md)
            self.assertIn("requests.json", md)
            self.assertIn("overlap-evidence.json", md)
            self.assertIn("health-before.json", md)
            self.assertIn("runtime/routing-preflight.json", md)

    def test_startup_failed_experiment_omits_missing_files(self):
        """A FAIL_STARTUP experiment should NOT claim files that don't exist."""
        with tempfile.TemporaryDirectory() as td:
            raw, config, metrics, completion = _make_raw(
                td,
                ["runtime/plan.json", "runtime/server-0.log"],
                metrics={"verdict": "FAIL_STARTUP", "error": "backend server 0 exited prematurely"},
                completion={
                    "experiment_id": "EXP-V100-TEST-001",
                    "verdict": "FAIL_STARTUP",
                    "completed_at_utc": "2026-09-26T00:00:00+00:00",
                    "error": "backend server 0 exited prematurely",
                },
            )
            md = report._report(config, metrics, completion, raw)
            # These should NOT appear because they don't exist
            self.assertNotIn("workload.json", md)
            self.assertNotIn("payloads.json", md)
            self.assertNotIn("tokenization.json", md)
            self.assertNotIn("requests.json", md)
            self.assertNotIn("overlap-evidence.json", md)
            self.assertNotIn("health-before.json", md)
            # These SHOULD appear because they exist
            self.assertIn("config.json", md)
            self.assertIn("runtime/plan.json", md)
            self.assertIn("runtime/server-0.log", md)
            # Failure reason should be shown
            self.assertIn("Failure reason", md)
            self.assertIn("backend server 0 exited prematurely", md)


class TestRuntimeLauncherContract(unittest.TestCase):
    """Verify gateway and backend configuration contract."""
    def test_gateway_routing_is_least_busy(self):
        import runtime_launcher
        plan = runtime_launcher.build_plan(
            ROOT, "ornith-1.5-9b", "TARGET", 2, "1gpu-x2-independent", 18080, 18079
        )
        self.assertEqual(plan["gateway"]["routing_strategy"], "least-busy")

    def test_backend_model_info_ids(self):
        import runtime_launcher
        plan = runtime_launcher.build_plan(
            ROOT, "ornith-1.5-9b", "TARGET", 2, "1gpu-x2-independent", 18080, 18079
        )
        cfg = plan["gateway"]["config"]
        if isinstance(cfg, dict) and "model_list" in cfg:
            model_ids = [m.get("model_info", {}).get("id") for m in cfg["model_list"]]
            self.assertIn("backend-0", model_ids)
            self.assertIn("backend-1", model_ids)

    def test_gateway_not_round_robin(self):
        import runtime_launcher
        plan = runtime_launcher.build_plan(
            ROOT, "ornith-1.5-9b", "TARGET", 2, "1gpu-x2-independent", 18080, 18079
        )
        self.assertNotEqual(plan["gateway"]["routing_strategy"], "round-robin")

    def test_backend_max_parallel_requests_is_1(self):
        import runtime_launcher
        plan = runtime_launcher.build_plan(
            ROOT, "ornith-1.5-9b", "TARGET", 2, "1gpu-x2-independent", 18080, 18079
        )
        cfg = plan["gateway"]["config"]
        if isinstance(cfg, dict) and "model_list" in cfg:
            for m in cfg["model_list"]:
                lp = m.get("litellm_params", {})
                self.assertEqual(lp.get("max_parallel_requests"), 1)

    def test_backend_num_retries_is_0(self):
        import runtime_launcher
        plan = runtime_launcher.build_plan(
            ROOT, "ornith-1.5-9b", "TARGET", 2, "1gpu-x2-independent", 18080, 18079
        )
        cfg = plan["gateway"]["config"]
        if isinstance(cfg, dict) and "model_list" in cfg:
            for m in cfg["model_list"]:
                lp = m.get("litellm_params", {})
                self.assertEqual(lp.get("max_retries"), 0)
        if isinstance(cfg, dict) and "router_settings" in cfg:
            self.assertEqual(cfg["router_settings"].get("num_retries"), 0)


if __name__ == "__main__":
    unittest.main()
