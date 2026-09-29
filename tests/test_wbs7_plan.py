"""WBS 7 candidates may change only their registered R2 delta."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_wbs7  # noqa: E402


class WBS7PlanTest(unittest.TestCase):
    def test_candidate_commands_are_exact_r2_deltas(self):
        control = json.loads(run_wbs7.BASE.read_text())["commands"][0]
        for candidate in run_wbs7.EXPERIMENTS:
            with self.subTest(candidate=candidate):
                digest = "sha256:" + "a" * 64 if candidate == "gqa2" else None
                planned = run_wbs7.plan(candidate, digest)
                command = planned["command"]
                self.assertEqual(command[:2], ["docker", "run"])
                self.assertEqual(command[2:6:2], ["--cidfile", "--label"])
                expected = control.copy()
                expected[expected.index("--name") + 1] = planned["experiment_id"].lower() + "-backend-0"
                if candidate == "mtp1":
                    index = expected.index("--spec-type")
                    expected[index + 1] = "draft-mtp"
                    expected[index + 2:index + 2] = ["--spec-draft-n-max", "1"]
                else:
                    expected[expected.index("--entrypoint") + 2] = run_wbs7.GQA_IMAGE
                self.assertEqual(command[6:], expected[2:])
                self.assertEqual(planned["workload_sha256"],
                                 "e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca")
                self.assertEqual(planned["config"]["measured_repetitions"], 1)
                self.assertEqual(planned["config"]["warmup_count"], 0)

    def test_gqa_plan_requires_pinned_image(self):
        with self.assertRaises(ValueError):
            run_wbs7.plan("gqa2")


if __name__ == "__main__":
    unittest.main()
