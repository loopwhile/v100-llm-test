from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

import run_c1_onecat as runner


class OneCatC1RunnerTests(unittest.TestCase):
    def test_wbs22_model_mapping_is_complete(self):
        self.assertEqual(
            runner.MODEL_WBS,
            {
                "qwen3.8-27b": "2.2.1",
                "ornith-1.5-9b": "2.2.2",
                "ornith-1.5-35b-a3b": "2.2.3",
                "gemma4-26b-a4b": "2.2.4",
            },
        )

    def test_runner_is_p520_gated_and_uses_single_stock_lane(self):
        source=(ROOT/"scripts/run_c1_onecat.py").read_text()
        self.assertIn('requires p520-llm',source)
        self.assertIn('"STOCK", 1, "tp2-shared"',source)
        self.assertIn("server_startup_compatibility_gate",source)
        self.assertNotIn("for retry",source.lower())

    def test_qwen_thinking_and_reasoning_effort_configuration(self):
        source=(ROOT/"scripts/run_c1_onecat.py").read_text()
        self.assertIn('thinking = True if args.model == "qwen3.8-27b" else False', source)
        self.assertIn('reasoning_effort = "medium" if args.model == "qwen3.8-27b" else None', source)
        self.assertIn('"temperature": 0.7', source)
        self.assertIn('reasoning_effort=medium', source)


if __name__=="__main__":
    unittest.main()
