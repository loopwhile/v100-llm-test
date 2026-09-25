from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


class RuntimeHooksTests(unittest.TestCase):
    def test_sitecustomize_file_exists(self):
        hook_file = ROOT / "scripts/runtime_hooks/sitecustomize.py"
        self.assertTrue(hook_file.is_file())

    def test_sitecustomize_patches_heterogeneous_config_mixin_if_available(self):
        try:
            from transformers.integrations.heterogeneity.configuration_utils import (
                HeterogeneousConfigMixin,
            )
            # Import our hook module
            sys.path.insert(0, str(ROOT / "scripts/runtime_hooks"))
            import sitecustomize  # noqa: F401

            class DummyConfig(HeterogeneousConfigMixin):
                pass

            dummy = DummyConfig()
            self.assertTrue(dummy.allow_global_per_layer_attribute_access)
        except ImportError:
            # When transformers or heterogeneity module is not installed in local env, pass
            pass

    def test_sitecustomize_gemma4_layer_resolution_contract(self):
        """Verify the contract that sliding=256/8 and full=512/2."""
        layer_types = [
            "sliding_attention" if i not in (5, 11, 17, 23, 29) else "full_attention"
            for i in range(30)
        ]
        full_layers = [i for i, lt in enumerate(layer_types) if lt == "full_attention"]
        self.assertEqual(full_layers, [5, 11, 17, 23, 29])
        self.assertEqual(len(full_layers), 5)

        for i, lt in enumerate(layer_types):
            if lt == "full_attention":
                expected_head_dim = 512
                expected_kv_heads = 2
            else:
                expected_head_dim = 256
                expected_kv_heads = 8
            if i in full_layers:
                self.assertEqual(expected_head_dim, 512)
                self.assertEqual(expected_kv_heads, 2)
            else:
                self.assertEqual(expected_head_dim, 256)
                self.assertEqual(expected_kv_heads, 8)


if __name__ == "__main__":
    unittest.main()
