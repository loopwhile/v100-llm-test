"""Lifecycle regressions for the generic llama C1 runner without GPU inference."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import run_c1_llama as runner
import runtime_launcher


class LlamaC1RunnerTests(unittest.TestCase):
    def test_ornith9_contract_exposes_all_four_c1_lanes(self):
        for lane in ('TARGET', 'NGRAM', 'MTP', 'MTP_NGRAM'):
            plan = runtime_launcher.build_plan(
                ROOT, 'ornith-1.5-9b', lane, 1, 'tp2-shared', 18080
            )
            self.assertTrue(plan['supported_for_planning'])
            self.assertEqual(plan['weight_quant'], 'Q6_K')
            self.assertEqual(plan['kv_cache'], 'FP16')
            self.assertEqual(plan['context_tokens_per_agent'], 131072)
            self.assertEqual(plan['concurrency'], 1)

    def test_ornith35_contract_exposes_all_four_c1_lanes(self):
        for lane in ('TARGET', 'NGRAM', 'MTP', 'MTP_NGRAM'):
            plan = runtime_launcher.build_plan(
                ROOT, 'ornith-1.5-35b-a3b', lane, 1, 'tp2-shared', 18080
            )
            self.assertTrue(plan['supported_for_planning'])
            self.assertEqual(plan['weight_quant'], 'Q4_K_M')
            self.assertEqual(plan['kv_cache'], 'Q8_0')
            self.assertEqual(plan['context_tokens_per_agent'], 131072)
            self.assertEqual(plan['concurrency'], 1)
            self.assertEqual(
                plan['model_identity']['sha256'],
                '42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f',
            )
            self.assertNotIn('--model-draft', plan['commands'][0])
            self.assertNotIn('--spec-draft-model', plan['commands'][0])

    def test_preflight_failure_is_durable_and_cannot_be_reused(self):
        plan = runtime_launcher.build_plan(
            ROOT, 'ornith-1.5-9b', 'TARGET', 1, 'tp2-shared', 0
        )
        args = argparse.Namespace(
            experiment_id='EXP-V100-ORN9-TEST-C1',
            model='ornith-1.5-9b',
            lane='TARGET',
            port=0,
            retry_of=None,
            retry_evidence=None,
        )
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
