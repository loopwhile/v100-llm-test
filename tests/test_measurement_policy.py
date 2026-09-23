from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import measurement_policy as policy


class MeasurementPolicyTests(unittest.TestCase):
    def test_c1_c2_only(self):
        for concurrency in (1, 2):
            plan = policy.execution_plan(concurrency)
            self.assertEqual(plan["concurrency"], concurrency)
            self.assertEqual(plan["measured_repetitions"], 1)
            self.assertEqual(plan["warmup_count"], 0)
            self.assertEqual(plan["total_intended_requests"], concurrency)
        for concurrency in (0, 3, 4, 5):
            with self.assertRaises(ValueError):
                policy.execution_plan(concurrency)

    def test_turns_are_not_repetitions(self):
        plan = policy.execution_plan(2, turns=3)
        self.assertEqual(plan["measured_repetitions"], 1)
        self.assertEqual(plan["measured_batches"], 3)
        self.assertEqual(plan["total_intended_requests"], 6)

    def test_repetitions_and_full_warmup_require_documented_exception(self):
        with self.assertRaises(ValueError):
            policy.future_config({"measured_repetitions": 2})
        with self.assertRaises(ValueError):
            policy.future_config({"warmup_count": 1})
        accepted = policy.future_config(
            {
                "measured_repetitions": 2,
                "repetition_user_request": "explicit test request",
                "warmup_count": 1,
                "full_size_warmup_reason": "explicit technical reason",
                "full_size_warmup_user_approval": "approved for test",
            }
        )
        self.assertEqual(accepted["repetition_count"], 2)
        self.assertEqual(accepted["warmup_count"], 1)

    def test_retry_identity_and_reason(self):
        base = {
            "experiment_id": "EXP-V100-Q38-LLAMA-C1-128K-001",
            "retry_of": "EXP-V100-Q38-LLAMA-C1-128K-001",
            "retry_reason": "harness_bug",
            "retry_evidence": "fixed barrier",
        }
        with self.assertRaisesRegex(ValueError, "new experiment ID"):
            policy.future_config(base)
        retry = base | {"experiment_id": "EXP-V100-Q38-LLAMA-C1-128K-002"}
        self.assertEqual(policy.future_config(retry)["retry_of"], base["retry_of"])
        with self.assertRaises(ValueError):
            policy.future_config(retry | {"retry_reason": "failed_once"})
        with self.assertRaises(ValueError):
            policy.future_config(retry | {"retry_reason": "user_authorized"})


if __name__ == "__main__":
    unittest.main()
