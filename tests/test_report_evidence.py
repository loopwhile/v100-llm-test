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
    def test_retry_provenance_is_visible_in_report_and_csv_note(self):
        with tempfile.TemporaryDirectory() as td:
            raw, config, metrics, completion = _make_raw(td, ["runtime/retry-receipt.json"])
            predecessor = "EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-001"
            (raw / "runtime/retry-receipt.json").write_text(json.dumps({
                "retry_of": predecessor, "reason": "infra_invalid_port_conflict"
            }))
            md = report._report(config, metrics, completion, raw)
            note = report._normalize_note(
                "no full-size warmup, fallback, retry or tuning.", config, "PASS_C2_ACTIVE", raw
            )
            self.assertIn(f"User-authorized retry of: {predecessor}", md)
            self.assertIn("runtime/retry-receipt.json", md)
            self.assertIn(f"User-authorized retry of {predecessor}", note)
            self.assertIn("automatic retry", note)

    def test_wbs5_report_preserves_candidate_workload_command_and_ngram_counters(self):
        with tempfile.TemporaryDirectory() as td:
            config = {
                "experiment_id": "EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260927-003",
                "model": "Ornith-1.5-9B", "runtime": "llama.cpp", "runtime_revision": "10775 / pinned",
                "weight_quant": "Q6_K", "kv_cache": "FP16", "speculative": "ngram", "ngram": "ngram-simple",
                "topology": "1gpu-x2-independent", "context_tokens": 131072, "concurrency": 2,
                "prefix_cache_lane": "cold-independent", "notes": "test", "wbs5_candidate": "NGRAM_DEFAULT",
                "wbs5_candidate_key": "R2", "workload_manifest_path": "workloads/performance/v1.json",
                "workload_manifest_sha256": "abc123", "launch_command": "docker run backend; docker run gateway",
                "gateway": {"runtime": "LiteLLM", "routing_strategy": "least-busy"},
            }
            raw, config, metrics, completion = _make_raw(
                td, ["speculative-evidence.json"], config=config,
                metrics={"verdict": "PASS_C2_ACTIVE", "c2_resident": True, "c2_active": True, "queue_only": False},
                completion={"experiment_id": config["experiment_id"], "verdict": "PASS_C2_ACTIVE", "completed_at_utc": "2026-09-27T00:00:00+00:00"},
            )
            (raw / "speculative-evidence.json").write_text(json.dumps({"aggregate": {
                "draft_tokens": 400, "accepted_tokens": 120, "acceptance_ratio": 0.3, "verification_steps": 58,
            }}))
            md = report._report(config, metrics, completion, raw)
            self.assertIn("NGRAM_DEFAULT (R2)", md)
            self.assertIn("workloads/performance/v1.json", md)
            self.assertIn("docker run backend; docker run gateway", md)
            self.assertIn("Draft tokens: 400", md)
            self.assertIn("Accepted tokens: 120", md)
            self.assertIn("Acceptance ratio: 0.3", md)

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

    def test_1gpu_startup_failed_does_not_claim_measured_batch(self):
        """A 1gpu-x2-independent FAIL_STARTUP experiment must not claim one measured 128K batch."""
        with tempfile.TemporaryDirectory() as td:
            raw, config, metrics, completion = _make_raw(
                td,
                ["runtime/plan.json", "runtime/server-0.log"],
                config={
                    "experiment_id": "EXP-V100-TEST-002",
                    "model": "test-model",
                    "runtime": "1Cat-vLLM",
                    "runtime_revision": "test",
                    "weight_quant": "NVFP4",
                    "kv_cache": "FP16",
                    "speculative": "MTP",
                    "ngram": "N/A",
                    "topology": "1gpu-x2-independent",
                    "context_tokens": 131072,
                    "concurrency": 2,
                    "prefix_cache_lane": "cold-independent",
                    "notes": "test",
                },
                metrics={"verdict": "FAIL_STARTUP", "error": "backend server 0 exited prematurely"},
                completion={
                    "experiment_id": "EXP-V100-TEST-002",
                    "verdict": "FAIL_STARTUP",
                    "completed_at_utc": "2026-09-26T00:00:00+00:00",
                    "error": "backend server 0 exited prematurely",
                },
            )
            md = report._report(config, metrics, completion, raw)
            self.assertIn("no measured 128K batch reached; startup failed before routing preflight and measurement", md)
            self.assertNotIn("one measured 128K batch", md)

    def test_normalize_note_startup_failure(self):
        """_normalize_note replaces 'one measured 128K batch' with startup failed phrase on FAIL_STARTUP."""
        config = {"topology": "1gpu-x2-independent", "concurrency": 2}
        raw_dir = Path("/tmp")
        note = "WBS 4.2.2; Ornith 1.5 9B 1GPUx2 + LiteLLM; concurrency C2; one measured 128K batch; no full-size benchmark warmup."
        normalized = report._normalize_note(note, config, "FAIL_STARTUP", raw_dir)
        self.assertIn("WBS 4.2.1", normalized)
        self.assertIn("no measured 128K batch reached; startup failed before routing preflight and measurement.", normalized)
        self.assertNotIn("one measured 128K batch", normalized)


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
