"""Offline checks for the WBS5 remote orchestration command."""
from pathlib import Path
import hashlib
import json
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

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

    def test_gate_evidence_is_copied_into_new_commit_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); gate_id = "EXP-GATE-FAIL"
            raw = root / "results/raw" / gate_id
            raw.mkdir(parents=True)
            source = raw / "semantic-audit.json"
            source.write_text('{"semantic_audit":"FAIL"}')
            receipt_path = raw / "g0-diagnostic-receipt.json"
            receipt_path.write_text(json.dumps({"experiment_id": gate_id, "evidence": [{
                "path": str(source.relative_to(root)),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }]}))
            with patch.object(remote, "ROOT", root), patch.object(remote, "ssh") as ssh, \
                 patch.object(remote, "run") as run:
                remote_path = remote.copy_gate_receipt(receipt_path, "/remote/snapshot", "EXP-R0")
                self.assertEqual(remote_path, "/remote/snapshot/.wbs5-gates/EXP-R0-g0-diagnostic-receipt.json")
                self.assertEqual(run.call_count, 2)
                self.assertIn("/remote/snapshot/results/raw/EXP-GATE-FAIL/semantic-audit.json",
                              run.call_args_list[0].args[0][-1])
                self.assertEqual(ssh.call_count, 2)
                source.write_text("tampered")
                with self.assertRaisesRegex(ValueError, "gate evidence hash mismatch"):
                    remote.copy_gate_receipt(receipt_path, "/remote/snapshot", "EXP-R0")


if __name__ == "__main__":
    unittest.main()
