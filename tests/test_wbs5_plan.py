from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_wbs5_plan as wbs5
import bench_harness as harness


class WBS5DryPlanTests(unittest.TestCase):
    def setUp(self):
        self.ids = {
            key: wbs5.candidate_experiment_id(candidate, "20260927", n)
            for n, (key, candidate) in enumerate(wbs5.frozen_candidates()[1].items(), 1)
        }

    def test_exact_frozen_candidate_set(self):
        profile, candidates = wbs5.frozen_candidates()
        self.assertEqual(set(candidates), {"R0", "R1", "R2"})
        self.assertEqual(len(profile["candidates"]), 3)
        self.assertNotIn("R3", candidates)

    def test_plans_preserve_single_variable_candidate_deltas(self):
        plans = {key: wbs5.build_plan(key, exp_id) for key, exp_id in self.ids.items()}
        r0 = plans["R0"]["launch_plan"]["commands"]
        for r1 in plans["R1"]["launch_plan"]["commands"]:
            self.assertEqual(r1[r1.index("--ubatch-size") + 1], "256")
            self.assertEqual(r1[r1.index("--batch-size") + 1], "512")
        for r2 in plans["R2"]["launch_plan"]["commands"]:
            self.assertEqual(r2[r2.index("--spec-type") + 1], "ngram-simple")
            self.assertEqual(r2[r2.index("--batch-size") + 1], "512")
            self.assertEqual(r2[r2.index("--ubatch-size") + 1], "128")
        for i, base in enumerate(r0):
            for key, option, value in (("R1", "--ubatch-size", "256"), ("R2", "--spec-type", "ngram-simple")):
                compared = plans[key]["launch_plan"]["commands"][i]
                differences = [j for j, pair in enumerate(zip(base, compared)) if pair[0] != pair[1]]
                self.assertEqual(differences, [base.index(option) + 1])
                self.assertEqual(compared[differences[0]], value)

    def test_performance_manifest_and_invariants_are_pinned(self):
        plan = wbs5.build_plan("R0", self.ids["R0"])
        self.assertEqual(plan["workload"]["path"], "workloads/performance/v1.json")
        self.assertEqual(plan["workload"]["mode"], "performance")
        self.assertEqual(plan["runtime_contract"]["backend_context"], 131072)
        self.assertEqual(plan["runtime_contract"]["backend_parallel"], 1)
        self.assertTrue(plan["runtime_contract"]["routing_settled_admission"])
        self.assertTrue(plan["runtime_contract"]["no_warmup"])
        self.assertTrue(plan["warmup_policy"]["cold_independent"])
        runtime_image = json.loads((ROOT / "config/runtime-lock.json").read_text())["runtimes"]["llama.cpp"]["image"]
        self.assertEqual(plan["runtime_contract"]["image"], runtime_image)
        self.assertEqual(plan["runtime_cli_evidence"]["options"]["--ubatch-size"]["type"], "integer")
        self.assertEqual(plan["runtime_cli_evidence"]["options"]["--spec-ngram-simple-size-n"]["default"], 12)
        self.assertEqual(plan["runtime_cli_evidence"]["options"]["--spec-ngram-simple-size-m"]["default"], 48)
        self.assertFalse(plan["runtime_cli_evidence"]["options"]["cuda_graph_disable"]["supported"])
        self.assertIn("Volta", plan["runtime_cli_evidence"]["sm70_flash_attention_source"]["dispatch"])
        r2 = wbs5.build_plan("R2", self.ids["R2"])
        self.assertEqual(r2["candidate"]["ngram_size_n"], 12)
        self.assertEqual(r2["candidate"]["ngram_size_m"], 48)

    def test_prepare_writes_exclusive_plan_without_touching_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            output_root = Path(temp) / "plans"
            output_root.mkdir()
            raw = Path(temp) / "raw"
            raw.mkdir()
            marker = raw / "existing.json"
            marker.write_text('{"immutable":true}\n')
            prepared = wbs5.prepare("R0", self.ids["R0"], output_root)
            self.assertTrue((prepared / "runtime/plan.json").is_file())
            config = json.loads((prepared / "runtime/planned-config.json").read_text())
            self.assertEqual(config["candidate_key"], "R0")
            self.assertEqual(config["workload"]["path"], "workloads/performance/v1.json")
            self.assertEqual(marker.read_text(), '{"immutable":true}\n')
            with self.assertRaises(FileExistsError):
                wbs5.prepare("R0", self.ids["R0"], output_root)

    def test_experiment_id_must_match_candidate(self):
        with self.assertRaises(ValueError):
            wbs5.build_plan("R1", self.ids["R0"])

    def test_ngram_counter_delta_is_measured_window_scoped(self):
        def snapshot(drafts, accepted, steps):
            return {"backends": {"backend_0": {"/metrics": "\n".join([
                f"llamacpp:spec_decode_num_draft_tokens_total {drafts}",
                f"llamacpp:spec_decode_num_accepted_tokens_total {accepted}",
                f"llamacpp:spec_decode_num_drafts_total {steps}",
            ])}}}
        evidence = harness.speculative_metric_delta(snapshot(100, 20, 12), snapshot(500, 140, 70))
        self.assertEqual(evidence["aggregate"]["draft_tokens"], 400)
        self.assertEqual(evidence["aggregate"]["accepted_tokens"], 120)
        self.assertEqual(evidence["aggregate"]["verification_steps"], 58)
        self.assertEqual(evidence["aggregate"]["acceptance_ratio"], 0.3)


if __name__ == "__main__":
    unittest.main()
