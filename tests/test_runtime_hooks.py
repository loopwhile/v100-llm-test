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


if __name__ == "__main__":
    unittest.main()
