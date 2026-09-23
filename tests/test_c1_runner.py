"""Lifecycle regressions without a GPU, Docker, or inference request."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_c1_qwen as runner
import runtime_launcher


class RunnerTests(unittest.TestCase):
    def test_preflight_failure_is_durable_and_cannot_be_reused(self):
        plan = runtime_launcher.build_plan(ROOT, 'qwen3.8-27b', 'TARGET', 1, 'tp2-shared', 0)
        args = argparse.Namespace(experiment_id='EXP-V100-TEST-C1', lane='TARGET', port=0, retry_of=None)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(runner, 'ROOT', root), \
                 patch.object(runner.socket, 'gethostname', return_value='p520-llm'), \
                 patch.object(runner.launcher, 'build_plan', return_value=plan), \
                 patch.object(runner.launcher, 'preflight', return_value={'pass': False}), \
                 patch.object(runner, 'command', return_value=''), \
                 patch.object(runner.socket, 'socket'), \
                 patch.object(runner.subprocess, 'Popen') as popen:
                self.assertEqual(runner.run(args), 1)
                popen.assert_not_called()
                raw = root / 'results/raw' / args.experiment_id
                completion = json.loads((raw / 'completion.json').read_text())
                self.assertEqual(completion['verdict'], 'INCONCLUSIVE')
                self.assertIn('preflight', completion['error'])
                self.assertTrue((raw / 'runtime/exit.json').exists())
                original = (raw / 'completion.json').read_bytes()
                with self.assertRaises(FileExistsError):
                    runner.run(args)
                self.assertEqual((raw / 'completion.json').read_bytes(), original)

    def test_wrong_host_refuses_before_creating_artifacts(self):
        with patch.object(runner.socket, 'gethostname', return_value='other-host'):
            with self.assertRaisesRegex(RuntimeError, 'p520-llm'):
                runner.run(None)


if __name__ == '__main__':
    unittest.main()
