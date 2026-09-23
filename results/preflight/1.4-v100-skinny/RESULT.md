# WBS 1.4 — v100-skinny preflight result

## Verdict

`FAIL_OOM_MODEL_LOAD`

Current hardware:

- 2× NVIDIA Tesla V100-SXM2-16GB
- TP2 experimental topology

The v100-skinny runtime/kernel bootstrap succeeded, but Qwen3.8-27B could not complete model loading on 2×16GB.

## Verified identity

- v100-skinny revision:
  `5b589c0dc81223e0ba65bcb3e755874723f8b515`
- 1Cat-vLLM:
  `1.2.2`
- 1Cat wheel SHA256:
  `8a628983ad9d675559910372643220c418b307ddc7fd52ac65a7f5fbcb104bc6`
- TileLang:
  `0.1.10`
- apache-tvm-ffi:
  `0.1.10`
- PyTorch:
  `2.10.0+cu128`
- CUDA userspace/toolkit:
  `12.8`
- checkpoint:
  `RadixArk/Qwen3.8-27B-NVFP4`
- checkpoint revision:
  `554ebba9b5f1b79dc11246341960360e6ef05ef4`

All downloaded checkpoint metadata entries resolved to the exact pinned revision.

## Successful preflight stages

- exact source checkout verified
- exact 1Cat-vLLM wheel bootstrap
- SM70/V100 detection
- fork patch deployment
- SM70 skinny CUDA kernel JIT
- required kernel entry points present
- Docker runtime identity verified
- RadixArk checkpoint provenance verified
- TP2 launcher adaptation performed

## Failure

Both TP ranks failed while processing loaded quantized weights:

`process_weights_after_loading`
→ `_qpn_stash`
→ `_qpn_prepack`
→ `torch.OutOfMemoryError`

Representative GPU state at failure:

- GPU total capacity: ~15.77 GiB
- PyTorch allocated: ~15.21 GiB
- free: ~9.5 MiB
- failing allocation: 18 MiB

The failure occurred before KV-cache capacity measurement, server readiness, MTP warm request, or the skinny boot gate.

Therefore:

- server boot: `NOT_REACHED`
- `skinny_gate.py`: `NOT_REACHED`
- C1 128K: `NOT_SCHEDULED`
- C2: `NOT_SCHEDULED`

Published TP4 results are not inherited.

Issue #1 TP2 success reports use 2× V100 32GB and are not treated as evidence that this 2×16GB machine can run the lane.

## Evidence

- `source-check.txt`
- `contract-detail.txt`
- `bootstrap-precheck.txt`
- `toolchain-precheck.txt`
- `v100-skinny-tp2-boot.txt`
- `v100-skinny-tp2-serve.log`
