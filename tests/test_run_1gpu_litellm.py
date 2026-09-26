"""Lifecycle and plan tests for the Ornith 1.5 9B 1GPUx2 + LiteLLM runner."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_1gpu_litellm as runner
import runtime_launcher


class Ornith1GPUx2RunnerTests(unittest.TestCase):
    def test_llama_lanes_generate_valid_1gpu_plans(self):
        for lane in ("TARGET", "NGRAM", "MTP", "MTP_NGRAM"):
            for c in (1, 2):
                plan = runtime_launcher.build_plan(
                    ROOT, "ornith-1.5-9b", lane, c, "1gpu-x2-independent", 18080, 18079
                )
                self.assertTrue(plan["supported_for_planning"], f"failed for {lane} C{c}")
                self.assertEqual(plan["topology"], "1gpu-x2-independent")
                self.assertEqual(plan["concurrency"], c)
                self.assertEqual(len(plan["commands"]), 2)
                self.assertEqual(plan["endpoints"], ["http://127.0.0.1:18079"])
                self.assertEqual(
                    plan["backend_endpoints"],
                    ["http://127.0.0.1:18080", "http://127.0.0.1:18081"],
                )
                self.assertIsNotNone(plan.get("gateway"))
                self.assertEqual(plan["gateway"]["runtime"], "LiteLLM")
                self.assertEqual(plan["gateway"]["endpoint"], "http://127.0.0.1:18079")
                self.assertEqual(plan["gateway"]["routing_strategy"], "least-busy")

                # Verify GPU assignments
                cmd0 = plan["commands"][0]
                cmd1 = plan["commands"][1]
                self.assertIn("device=0", " ".join(cmd0))
                self.assertIn("device=1", " ".join(cmd1))
                self.assertIn("127.0.0.1:18080:8080", " ".join(cmd0))
                self.assertIn("127.0.0.1:18081:8080", " ".join(cmd1))

    def test_stock_onecat_lane_generates_valid_1gpu_plan(self):
        for c in (1, 2):
            plan = runtime_launcher.build_plan(
                ROOT, "ornith-1.5-9b", "STOCK", c, "1gpu-x2-independent", 18080, 18079
            )
            self.assertTrue(plan["supported_for_planning"], f"failed for STOCK C{c}")
            self.assertEqual(plan["topology"], "1gpu-x2-independent")
            self.assertEqual(plan["concurrency"], c)
            self.assertEqual(len(plan["commands"]), 2)
            self.assertEqual(
                [e["CUDA_VISIBLE_DEVICES"] for e in plan["command_environments"]],
                ["0", "1"],
            )
            self.assertEqual(plan["endpoints"], ["http://127.0.0.1:18079"])
            self.assertEqual(
                plan["backend_endpoints"],
                ["http://127.0.0.1:18080", "http://127.0.0.1:18081"],
            )

    def test_cli_requires_valid_experiment_id(self):
        with self.assertRaises(SystemExit):
            with patch("sys.argv", ["run_1gpu_litellm.py", "--lane", "TARGET", "--concurrency", "1"]):
                runner.main()

        with self.assertRaises(SystemExit):
            with patch("sys.argv", [
                "run_1gpu_litellm.py",
                "--experiment-id", "invalid_id_lowercase",
                "--lane", "TARGET",
                "--concurrency", "1",
            ]):
                runner.main()

    def test_measure_worker_c1_flow(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td)
            runtime = raw / "runtime"
            runtime.mkdir()
            config = {
                "experiment_id": "EXP-V100-ORN15-9B-LLAMA-F16-TARGET-1GPU2-C1-128K-20260926-001",
                "model": "Ornith-1.5-9B",
                "lane": "TARGET",
                "concurrency": 1,
                "topology": "1gpu-x2-independent",
                "runtime": "llama.cpp",
                "endpoints": ["http://127.0.0.1:18079"],
                "backend_endpoints": ["http://127.0.0.1:18080", "http://127.0.0.1:18081"],
                "gateway": {
                    "runtime": "LiteLLM",
                    "endpoint": "http://127.0.0.1:18079",
                },
            }
            (runtime / "planned-config.json").write_text(runtime_launcher.json.dumps(config))

            mock_adapter = Mock()
            mock_workload = {"requests": [{"request_id": "test"}]}

            with patch("bench_harness.make_plan_adapter", return_value=mock_adapter), \
                 patch("build_128k_workload.load_manifest", return_value={}), \
                 patch("build_128k_workload.build", return_value=mock_workload), \
                 patch("bench_harness.run_batch", return_value="PASS_C1_128K") as mock_run:
                runner.measure(raw)
                mock_run.assert_called_once_with(raw, config, mock_workload, mock_adapter)

            progress = runtime_launcher.json.loads((runtime / "progress.json").read_text())
            self.assertEqual(progress["phase"], "results_saved")
            self.assertEqual(progress["verdict"], "PASS_C1_128K")

    def test_preflight_saved_to_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td)
            runtime = raw / "runtime"
            runtime.mkdir()
            mock_adapter = Mock()
            mock_adapter.routing_preflight.return_value = {
                "pass": True,
                "distinct_bases": True,
                "distinct_ids": True,
                "bases": ["http://127.0.0.1:18080/v1", "http://127.0.0.1:18081/v1"],
                "deployment_ids": ["backend-0", "backend-1"],
            }
            res = mock_adapter.routing_preflight("ornith-1.5-9b", timeout_s=60)
            runner.h.save(runtime / "routing-preflight.json", res)
            self.assertTrue((runtime / "routing-preflight.json").exists())
            saved = runner.json.loads((runtime / "routing-preflight.json").read_text())
            self.assertTrue(saved["pass"])
            self.assertEqual(len(saved["bases"]), 2)


if __name__ == "__main__":
    unittest.main()
