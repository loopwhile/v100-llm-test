"""Runtime compatibility hooks for 1Cat-vLLM serving on SM70."""
from __future__ import annotations

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
