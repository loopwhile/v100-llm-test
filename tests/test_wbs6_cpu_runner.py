"""Tests for WBS 6 CPU runner configuration, memory telemetry, safety controls, and immutability."""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_wbs6_cpu as runner


class WBS6RunnerTests(unittest.TestCase):
    def test_experiment_ids_and_server_constants(self):
        self.assertEqual(runner.GEMMA_EXP_ID, "EXP-P520-CPU-GEMMA4-26B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001")
        self.assertEqual(runner.ORNITH_EXP_ID, "EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001")
        self.assertEqual(runner.DEFAULT_IMAGE, "p520-cpu-llama:b10775")
        self.assertEqual(runner.GEMMA_PORT, 8082)
        self.assertEqual(runner.ORNITH_PORT, 8083)

    def test_runner_safety_stop_when_no_action_flag(self):
        args = argparse.Namespace(
            preflight_only=False,
            gate_only=False,
            run_32k_measured=False,
            selected_image="",
        )
        with patch("socket.gethostname", return_value="p520-llm.local"):
            with patch("run_wbs6_cpu.run_locked") as mock_locked:
                runner.run(args)
                mock_locked.assert_not_called()

    def test_compute_summary_deltas(self):
        collector = runner.MemoryTelemetryCollector(output_csv=ROOT / "tmp_test.csv")
        collector.min_mem_available_kib = 25000000
        collector.gemma_rss_peak_kib = 2000000
        collector.ornith_rss_peak_kib = 18000000

        start_snap = {
            "system_memory_kib": {"SwapUsed": 4000000, "MemAvailable": 32000000},
            "system_vmstat": {"pswpin": 100, "pswpout": 200, "pgmajfault": 50000},
        }
        end_snap = {
            "system_memory_kib": {"SwapUsed": 4005000, "MemAvailable": 31000000},
            "system_vmstat": {"pswpin": 110, "pswpout": 250, "pgmajfault": 52000},
        }

        deltas = collector.compute_summary_deltas(start_snap, end_snap)
        self.assertEqual(deltas["swap_used_start_kib"], 4000000)
        self.assertEqual(deltas["swap_used_end_kib"], 4005000)
        self.assertEqual(deltas["swap_used_delta_kib"], 5000)
        self.assertEqual(deltas["pswpin_delta"], 10)
        self.assertEqual(deltas["pswpout_delta"], 50)
        self.assertEqual(deltas["pgmajfault_delta"], 2000)
        self.assertEqual(deltas["mem_available_minimum_kib"], 25000000)
        self.assertEqual(deltas["gemma_process_peaks_kib"]["rss"], 2000000)
        self.assertEqual(deltas["ornith_process_peaks_kib"]["rss"], 18000000)

    def test_compute_memory_deltas_standalone(self):
        start_snap = {
            "system_memory_kib": {"SwapUsed": 3000000, "MemAvailable": 35000000},
            "system_vmstat": {"pswpin": 50, "pswpout": 70, "pgmajfault": 10000},
            "gemma_process": {"smaps_rollup_kib": {"Rss": 1000, "Pss": 800, "Swap": 0}},
            "ornith_process": {"smaps_rollup_kib": {"Rss": 2000, "Pss": 1800, "Swap": 0}},
        }
        end_snap = {
            "system_memory_kib": {"SwapUsed": 3010000, "MemAvailable": 34000000},
            "system_vmstat": {"pswpin": 65, "pswpout": 90, "pgmajfault": 11500},
            "gemma_process": {"smaps_rollup_kib": {"Rss": 1200, "Pss": 900, "Swap": 10}},
            "ornith_process": {"smaps_rollup_kib": {"Rss": 2500, "Pss": 2000, "Swap": 20}},
        }

        deltas = runner.compute_memory_deltas(start_snap, end_snap)
        self.assertEqual(deltas["swap_used_delta_kib"], 10000)
        self.assertEqual(deltas["pswpin_delta"], 15)
        self.assertEqual(deltas["pswpout_delta"], 20)
        self.assertEqual(deltas["pgmajfault_delta"], 1500)
        self.assertEqual(deltas["mem_available_minimum_kib"], 34000000)
        self.assertEqual(deltas["gemma_process_peaks_kib"]["rss"], 1200)
        self.assertEqual(deltas["ornith_process_peaks_kib"]["rss"], 2500)

    def test_preflight_immutability_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            preflight_dir = tmp_root / "results/raw/WBS6-PREFLIGHT-AB"
            preflight_dir.mkdir(parents=True)
            (preflight_dir / "preflight_ab_result.json").write_text("{}")

            with self.assertRaises(RuntimeError) as ctx:
                runner.run_preflight_ab(tmp_root, {})
            self.assertIn("Immutable preflight raw evidence already exists", str(ctx.exception))

    def test_startup_gate_immutability_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_gate_dir = Path(tmpdir) / "WBS6-STARTUP-GATE"
            tmp_gate_dir.mkdir(parents=True)
            (tmp_gate_dir / "startup_gate.json").write_text("{}")

            with self.assertRaises(RuntimeError) as ctx:
                runner.record_startup_gate(tmp_gate_dir, "test-image")
            self.assertIn("Immutable startup gate raw evidence already exists", str(ctx.exception))

    def test_measured_experiment_immutability_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            exp_id = "EXP-TEST-CPU-001"
            (tmp_root / "results/raw" / exp_id).mkdir(parents=True)

            with self.assertRaises(RuntimeError) as ctx:
                runner.run_measured_experiment_32k(
                    root=tmp_root,
                    exp_id=exp_id,
                    model_name="mock.gguf",
                    model_key="mock",
                    model_path="/mock.gguf",
                    port=8082,
                    selected_image="mock:tag",
                    peer_name="peer.gguf",
                    peer_port=8083,
                    gemma_pid=None,
                    ornith_pid=None,
                    snap_a={},
                    snap_b={},
                    pre_snap_label="pre",
                    post_snap_label="post",
                )
            self.assertIn("Immutable raw experiment evidence directory already exists", str(ctx.exception))

    def test_failure_preserves_post_snap_and_deltas(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            exp_id = "EXP-TEST-CPU-FAIL"

            snap_a = {"system_memory_kib": {"SwapUsed": 100, "MemAvailable": 1000}, "system_vmstat": {"pswpin": 0, "pswpout": 0, "pgmajfault": 0}}
            snap_b = {"system_memory_kib": {"SwapUsed": 100, "MemAvailable": 1000}, "system_vmstat": {"pswpin": 0, "pswpout": 0, "pgmajfault": 0}}

            with patch("bench_harness.HTTPAdapter") as mock_adapter_cls, \
                 patch("build_128k_workload.load_manifest", return_value={"schema_version": 1}), \
                 patch("build_128k_workload.build", return_value={"requests": []}), \
                 patch("bench_harness.run_batch", side_effect=RuntimeError("Simulated inference batch crash")), \
                 patch("run_wbs6_cpu.capture_memory_checkpoint", return_value={"system_memory_kib": {"SwapUsed": 150, "MemAvailable": 900}, "system_vmstat": {"pswpin": 1, "pswpout": 1, "pgmajfault": 10}}):

                mock_adapter_instance = MagicMock()
                mock_adapter_instance.health.return_value = {"healthy": True}
                mock_adapter_cls.return_value = mock_adapter_instance

                with self.assertRaises(RuntimeError) as ctx:
                    runner.run_measured_experiment_32k(
                        root=tmp_root,
                        exp_id=exp_id,
                        model_name="mock.gguf",
                        model_key="mock",
                        model_path="/mock.gguf",
                        port=8082,
                        selected_image="mock:tag",
                        peer_name="peer.gguf",
                        peer_port=8083,
                        gemma_pid=None,
                        ornith_pid=None,
                        snap_a=snap_a,
                        snap_b=snap_b,
                        pre_snap_label="checkpoint_c_pre",
                        post_snap_label="checkpoint_d_post",
                    )
                self.assertIn("Simulated inference batch crash", str(ctx.exception))

            raw = tmp_root / "results/raw" / exp_id
            self.assertTrue((raw / "memory-baseline-before-startup.json").exists())
            self.assertTrue((raw / "runtime/checkpoint_a_baseline_before_startup.json").exists())
            self.assertTrue((raw / "runtime/checkpoint_b_startup_healthy.json").exists())
            self.assertTrue((raw / "runtime/checkpoint_c_pre.json").exists())
            self.assertTrue((raw / "runtime/checkpoint_d_post.json").exists())
            self.assertTrue((raw / "memory-deltas.json").exists())
            self.assertTrue((raw / "dual_resident_post_health.json").exists())

    def test_post_health_exception_does_not_mask_batch_error_and_records_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            exp_id = "EXP-TEST-CPU-HEALTH-FAIL"

            snap_a = {"system_memory_kib": {"SwapUsed": 100, "MemAvailable": 1000}, "system_vmstat": {"pswpin": 0, "pswpout": 0, "pgmajfault": 0}}
            snap_b = {"system_memory_kib": {"SwapUsed": 100, "MemAvailable": 1000}, "system_vmstat": {"pswpin": 0, "pswpout": 0, "pgmajfault": 0}}

            with patch("bench_harness.HTTPAdapter") as mock_adapter_cls, \
                 patch("build_128k_workload.load_manifest", return_value={"schema_version": 1}), \
                 patch("build_128k_workload.build", return_value={"requests": []}), \
                 patch("bench_harness.run_batch", side_effect=RuntimeError("Original batch OOM or process crash")), \
                 patch("run_wbs6_cpu.capture_memory_checkpoint", return_value={"system_memory_kib": {"SwapUsed": 150, "MemAvailable": 900}, "system_vmstat": {"pswpin": 1, "pswpout": 1, "pgmajfault": 10}}):

                mock_adapter = MagicMock()
                # 1st call (pre-measurement peer health): healthy
                # 2nd call (post-measurement active model health): connection reset / crash
                # 3rd call (post-measurement peer health): healthy
                mock_adapter.health.side_effect = [
                    {"healthy": True},
                    ConnectionResetError("Server connection reset / crashed"),
                    {"healthy": True},
                ]
                mock_adapter_cls.return_value = mock_adapter

                with self.assertRaises(RuntimeError) as ctx:
                    runner.run_measured_experiment_32k(
                        root=tmp_root,
                        exp_id=exp_id,
                        model_name="mock.gguf",
                        model_key="mock",
                        model_path="/mock.gguf",
                        port=8082,
                        selected_image="mock:tag",
                        peer_name="peer.gguf",
                        peer_port=8083,
                        gemma_pid=None,
                        ornith_pid=None,
                        snap_a=snap_a,
                        snap_b=snap_b,
                        pre_snap_label="checkpoint_c_pre",
                        post_snap_label="checkpoint_d_post",
                    )
                # Ensure the original batch error is raised, NOT the ConnectionResetError
                self.assertIn("Original batch OOM or process crash", str(ctx.exception))

            raw = tmp_root / "results/raw" / exp_id
            health_json = raw / "dual_resident_post_health.json"
            self.assertTrue(health_json.exists())
            import json
            data = json.loads(health_json.read_text())
            self.assertFalse(data["both_healthy"])
            self.assertFalse(data["active_model_health"]["healthy"])
            self.assertIn("ConnectionResetError", data["active_model_health"]["error"])

    def test_openblas_preflight_immutability_guard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            preflight_dir = tmp_root / "results/raw/WBS6-PREFLIGHT-OPENBLAS"
            preflight_dir.mkdir(parents=True)
            (preflight_dir / "openblas_preflight.json").write_text("{}")

            with self.assertRaises(RuntimeError) as ctx:
                runner.run_openblas_preflight(tmp_root)
            self.assertIn("Immutable OpenBLAS preflight raw evidence already exists", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
