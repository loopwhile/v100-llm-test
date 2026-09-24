from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bench_harness as h


class OutputIntegrityTests(unittest.TestCase):
    def test_qwen_attempt_003_repetition_fails(self):
        evidence_path = ROOT / "results/raw/EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-003/requests.json"
        self.assertTrue(evidence_path.exists(), f"Evidence missing at {evidence_path}")
        with evidence_path.open() as f:
            req = json.load(f)[0]
        res = req["response"]
        case = {"check": "nonempty"}
        self.assertFalse(h.output_ok(case, res), "Obvious repetition loop must fail output_ok")

    def test_llama_good_long_output_passes(self):
        evidence_path = ROOT / "results/raw/EXP-V100-Q38-LLAMA-Q80-TARGET-C1-128K-20260923-002/requests.json"
        self.assertTrue(evidence_path.exists(), f"Evidence missing at {evidence_path}")
        with evidence_path.open() as f:
            req = json.load(f)[0]
        res = req["response"]
        case = {"check": "nonempty"}
        self.assertTrue(h.output_ok(case, res), "Coherent long output must pass output_ok")

    def test_ornith_good_long_outputs_pass(self):
        for exp_id in [
            "EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-003",
            "EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-002",
        ]:
            evidence_path = ROOT / f"results/raw/{exp_id}/requests.json"
            if evidence_path.exists():
                with evidence_path.open() as f:
                    req = json.load(f)[0]
                res = req["response"]
                case = {"check": "nonempty"}
                self.assertTrue(h.output_ok(case, res), f"{exp_id} output must pass output_ok")

    def test_short_valid_output_passes(self):
        res = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": "The primary correctness risk in PageIndex is shallow copying of pages during snapshot, which can cause mutation leakage if page objects are modified."
                    },
                }
            ]
        }
        case = {"check": "nonempty"}
        self.assertTrue(h.output_ok(case, res))

    def test_empty_output_fails(self):
        for empty_text in ["", "   ", "\n\t"]:
            res = {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": empty_text},
                    }
                ]
            }
            case = {"check": "nonempty"}
            self.assertFalse(h.output_ok(case, res), f"Empty text '{empty_text}' must fail")

    def test_corrupt_output_fails(self):
        for corrupt_text in ["Valid prefix \ufffd corrupted tail", "Line with \x00 null byte", "\x01\x02\x03"]:
            res = {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": corrupt_text},
                    }
                ]
            }
            case = {"check": "nonempty"}
            self.assertFalse(h.output_ok(case, res), "Corrupt text with unprintable or replacement chars must fail")

    def test_short_repetition_loop_fails(self):
        res = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": "loop loop loop loop loop loop loop loop"},
                }
            ]
        }
        case = {"check": "nonempty"}
        self.assertFalse(h.output_ok(case, res), "Short repetition loop must fail")


if __name__ == "__main__":
    unittest.main()
