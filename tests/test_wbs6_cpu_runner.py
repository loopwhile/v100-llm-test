"""Tests for WBS 6 CPU runner configuration, memory telemetry, and safety controls."""
import argparse
from pathlib import Path
import sys
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


if __name__ == "__main__":
    unittest.main()
