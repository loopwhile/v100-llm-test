"""Offline checks for the WBS5 remote orchestration command."""
from pathlib import Path
import shlex
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_wbs5_remote as remote
import wbs5_contract as contract


class Ornith9G0CommandTests(unittest.TestCase):
    def test_g0_pins_remote_onecat_python(self):
        experiment_id = "EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-002"
        argv = remote.ornith9_g0_argv(experiment_id)
        self.assertEqual(argv[:3], ["env", f"V100_1CAT_PYTHON={contract.PYTHON}", "python3"])
        self.assertEqual(argv[3:], ["scripts/run_c2_onecat.py", "--experiment-id", experiment_id,
                                     "--model", "ornith-1.5-9b"])
        self.assertIn(f"V100_1CAT_PYTHON={contract.PYTHON}", shlex.join(argv))


if __name__ == "__main__":
    unittest.main()
