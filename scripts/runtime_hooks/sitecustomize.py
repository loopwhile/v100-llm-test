"""Runtime compatibility hooks for 1Cat-vLLM serving on SM70."""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger("vllm.sm70.gemma4_compat")

# 1. HeterogeneousConfigMixin compatibility for transformers 5.16+
try:
    from transformers.integrations.heterogeneity.configuration_utils import (
        HeterogeneousConfigMixin,
    )

    # In transformers 5.16+, per-layer attributes (such as head_dim on Gemma4)
    # raise AmbiguousGlobalPerLayerAttributeError unless allow_global_per_layer_attribute_access is True.
    # Set default to True so vLLM's model arch config convertor can read global config attributes safely.
    HeterogeneousConfigMixin.allow_global_per_layer_attribute_access = property(
        lambda self: self.__dict__.get(
            "allow_global_per_layer_attribute_access", True
        ),
        lambda self, val: self.__dict__.__setitem__(
            "allow_global_per_layer_attribute_access", val
        ),
    )
except ImportError:
    pass

# 2. Gemma4TextConfig compatibility: preserve global_head_dim and num_global_key_value_heads
try:
    from transformers.models.gemma4.configuration_gemma4 import Gemma4TextConfig

    orig_post_init = Gemma4TextConfig.__post_init__

    def _patched_gemma4_text_config_post_init(self, **kwargs):
        # Extract before transformers pops them
        global_head_dim = kwargs.get("global_head_dim", None)
        num_global_key_value_heads = kwargs.get("num_global_key_value_heads", None)

        orig_post_init(self, **kwargs)

        # If not provided in kwargs, attempt to resolve from per_layer_config overrides
        if global_head_dim is None and hasattr(self, "per_layer_config") and hasattr(self, "layer_types"):
            for idx, lt in enumerate(self.layer_types):
                if lt == "full_attention" and idx < len(self.per_layer_config):
                    plc = self.per_layer_config[idx]
                    global_head_dim = getattr(plc, "head_dim", 512)
                    break
        if global_head_dim is None:
            global_head_dim = 512

        if num_global_key_value_heads is None and hasattr(self, "per_layer_config") and hasattr(self, "layer_types"):
            for idx, lt in enumerate(self.layer_types):
                if lt == "full_attention" and idx < len(self.per_layer_config):
                    plc = self.per_layer_config[idx]
                    num_global_key_value_heads = getattr(plc, "num_key_value_heads", 2)
                    break
        if num_global_key_value_heads is None:
            num_global_key_value_heads = 2

        self.__dict__["global_head_dim"] = global_head_dim
        self.__dict__["num_global_key_value_heads"] = num_global_key_value_heads

    Gemma4TextConfig.__post_init__ = _patched_gemma4_text_config_post_init
except ImportError:
    pass


# 3. Gemma4DecoderLayer patch in vllm.model_executor.models.gemma4
def _apply_gemma4_model_patch(gemma4_mod):
    if getattr(gemma4_mod, "_GEMMA4_COMPAT_PATCHED", False):
        return
    gemma4_mod._GEMMA4_COMPAT_PATCHED = True

    try:
        from vllm.model_executor.models.utils import extract_layer_index
    except ImportError:
        def extract_layer_index(prefix: str) -> int:
            parts = prefix.split(".")
            for i, p in enumerate(parts):
                if p == "layers" and i + 1 < len(parts):
                    return int(parts[i + 1])
            raise ValueError(f"Could not extract layer index from prefix {prefix}")

    orig_decoder_layer_init = gemma4_mod.Gemma4DecoderLayer.__init__

    def _patched_decoder_layer_init(
        self,
        config,
        cache_config=None,
        quant_config=None,
        prefix: str = "",
    ):
        layer_idx = extract_layer_index(prefix)
        layer_type = config.layer_types[layer_idx]
        is_full_attention = (layer_type == "full_attention")

        # Read from per_layer_config if available
        resolved_head_dim = None
        resolved_num_kv = None
        if hasattr(config, "per_layer_config") and config.per_layer_config:
            if isinstance(config.per_layer_config, (list, tuple)) and layer_idx < len(config.per_layer_config):
                plc = config.per_layer_config[layer_idx]
                resolved_head_dim = getattr(plc, "head_dim", None)
                resolved_num_kv = getattr(plc, "num_key_value_heads", None)
            elif isinstance(config.per_layer_config, dict) and layer_idx in config.per_layer_config:
                plc = config.per_layer_config[layer_idx]
                resolved_head_dim = getattr(plc, "head_dim", None)
                resolved_num_kv = getattr(plc, "num_key_value_heads", None)

        if resolved_head_dim is None:
            if is_full_attention:
                resolved_head_dim = getattr(config, "global_head_dim", 512)
            else:
                resolved_head_dim = config.head_dim

        if resolved_num_kv is None:
            use_k_eq_v = is_full_attention and getattr(config, "attention_k_eq_v", False)
            if use_k_eq_v:
                resolved_num_kv = getattr(
                    config,
                    "num_global_key_value_heads",
                    getattr(config, "num_key_value_heads", 2),
                )
            else:
                resolved_num_kv = config.num_key_value_heads

        # Assertions per contract: prove head_dim and num_kv_heads match architecture
        if is_full_attention:
            assert resolved_head_dim == 512, (
                f"[Gemma4Compat] Layer {layer_idx} (full_attention) expected head_dim 512, got {resolved_head_dim}"
            )
            assert resolved_num_kv == 2, (
                f"[Gemma4Compat] Layer {layer_idx} (full_attention) expected num_kv_heads 2, got {resolved_num_kv}"
            )
        else:
            assert resolved_head_dim == 256, (
                f"[Gemma4Compat] Layer {layer_idx} (sliding_attention) expected head_dim 256, got {resolved_head_dim}"
            )
            assert resolved_num_kv == 8, (
                f"[Gemma4Compat] Layer {layer_idx} (sliding_attention) expected num_kv_heads 8, got {resolved_num_kv}"
            )

        # Call original init
        orig_decoder_layer_init(
            self,
            config=config,
            cache_config=cache_config,
            quant_config=quant_config,
            prefix=prefix,
        )

        print(
            f"[Gemma4Compat] Layer {layer_idx:2d} ({layer_type:17s}): "
            f"head_dim={self.self_attn.head_dim}, num_kv={self.self_attn.total_num_kv_heads} [VERIFIED]",
            flush=True,
        )

    gemma4_mod.Gemma4DecoderLayer.__init__ = _patched_decoder_layer_init
    print("[Gemma4Compat] Successfully hooked Gemma4DecoderLayer.__init__", flush=True)


# Hook via sys.meta_path loader wrapper
class _Gemma4PatchLoader:
    def __init__(self, original_loader):
        self.original_loader = original_loader

    def create_module(self, spec):
        if hasattr(self.original_loader, "create_module"):
            return self.original_loader.create_module(spec)
        return None

    def exec_module(self, module):
        self.original_loader.exec_module(module)
        try:
            _apply_gemma4_model_patch(module)
        except Exception as e:
            print(f"[Gemma4Compat] Failed to apply patch: {e}", file=sys.stderr, flush=True)


class _Gemma4PatchFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname == "vllm.model_executor.models.gemma4":
            for finder in sys.meta_path:
                if finder is self:
                    continue
                if hasattr(finder, "find_spec"):
                    spec = finder.find_spec(fullname, path, target)
                    if spec is not None and spec.loader is not None:
                        spec.loader = _Gemma4PatchLoader(spec.loader)
                        return spec
        return None


if "vllm.model_executor.models.gemma4" in sys.modules:
    _apply_gemma4_model_patch(sys.modules["vllm.model_executor.models.gemma4"])
else:
    sys.meta_path.insert(0, _Gemma4PatchFinder())
