# WBS 7.0 — Qwen native MTP / SM70 GQA×2 preflight

Status: **DONE — STATIC/BUILD PREFLIGHT; NO GENERATION**.

This step audits the frozen control, model/runtime support and isolated GQA×2
source/build provenance. It does not establish MTP feasibility, GQA correctness
or a performance improvement. WBS 7.1 and 7.2 remain unexecuted.

## Frozen control

The authoritative control is `Q38-LLAMA-WBS5-R2-TARGET-UB256`, experiment
`EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001`. Its recorded verdict is
`PASS_C2_ACTIVE`, with mechanical output PASS for both requests and healthy
post-health. The [baseline audit](../results/preflight/7.0-qwen-sm70/frozen-baseline.json)
preserves the exact command, model/runtime/workload identities, metrics and
41 evidence/publication file hashes.

- GGUF: `/srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf`.
- SHA256: `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`.
- llama.cpp: b10775 / `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`.
- OCI: `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`.
- Layer split: `--split-mode layer --tensor-split 1,1`; project topology label
  `tp2-shared` does not mean llama.cpp tensor-parallel mode.
- Context: `--ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072`.
- Batch/ubatch: `512/256`; K/V `q8_0`; Flash Attention on; speculative mode none.
- Workload: `workloads/performance/v1.json`, SHA256
  `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`.
- Sampling: temperature 0, top_p 1, seed 520; output reserve 4096,
  minimum output 1024; two independent projects.

| Historical metric | R2 |
| --- | ---: |
| Mean TTFT | 679.053 s |
| Prefill | 264.112 tok/s |
| Mean request decode | 5.593 tok/s |
| Aggregate decode | 4.514 tok/s |
| End-to-end output | 3.457 tok/s |
| Batch wall | 1337.272 s |
| Measured peak VRAM, GPU0 / GPU1 | 13,447 / 14,533 MiB |

Historical active overlap uses positive interleaved server-log evidence; the
slot sampler captured idle endpoints only. Aggregate decode includes mixed
overlap/output windows and is not a pure decode-kernel measurement. Mechanical
output PASS does not establish semantic coding quality.

## Embedded MTP evidence

The exact R2 [server log](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/runtime/server-0.log)
lines 9–23 records 15 unused `blk.64.*` tensors, including
`nextn.eh_proj`, `nextn.enorm`, `nextn.hnorm` and `nextn.shared_head_norm`.
The baseline audit records the original lines and the log hash. This proves
that the target-only load ignored the embedded module; actual MTP use and
non-zero draft activity must be established in WBS 7.1.

Fresh read-only [GGUF header inspection](../results/preflight/7.0-qwen-sm70/gguf-header.json)
also finds those 15 tensors, including all four `nextn.*` tensors. The metadata
records architecture `qwen35`, 65 blocks and `nextn_predict_layers=1`; attention
has 24 Q heads, 4 KV heads (GQA ratio 6) and head dimension 256. The filename's
Qwen3.8 identity and the GGUF architecture tag are recorded separately.

The complete 16,464,440,224-byte model SHA256 was freshly recomputed on P520
and matches the frozen value. The pinned control reports build 10775, commit
prefix `67a17c17c`, GNU 11.4.0. Its
`--spec-type draft-mtp --spec-draft-n-max 1 --help` invocation exits 0.
The exact base source maps `draft-mtp` to the native-MTP implementation and
accepts the nonnegative maximum value 1. See [static checks](../results/preflight/7.0-qwen-sm70/static-checks.json).
No model was loaded. An initial help invocation lacked `libcuda.so.1`; the
successful invocation exposed the driver library using Docker `--gpus all`.
This was a CLI environment correction, not a measured retry.

## Source/build preflight

The external reference is
[`dual-v100-llama.cpp@5edfd28`](https://github.com/123123213weqw/dual-v100-llama.cpp/tree/5edfd28c56ef10d21f32fdcfcb12361bb6db1c55).
Its `patches/sm70-tuning.patch` Git blob independently verifies as
`7074ba8d0a48142823f7f4befff271ff1879633d`. Only its GQA×2 Flash Attention
changes are retained in the [forward-port patch](../results/preflight/7.0-qwen-sm70/source/b10775-sm70-gqa2.patch).
The complete downloaded b10775 source archive reconstructs Git tree
`5d61cb84711c5ad70d6a3c213e45b949bcf7e3d7`, matching the pinned commit's tree;
see [base tree verification](../results/preflight/7.0-qwen-sm70/source/base-tree-check.json).

- Patch SHA256: `25632d838c5e04c6b32920e5f61c39868e995d83156cb315ff477cf287197f80`.
- Changed file: `ggml/src/ggml-cuda/fattn-vec.cuh` only.
- Existing 128-thread geometry and `__launch_bounds__(..., 1)` are preserved.
- GDN, ARGMAX, MTP subvocabulary and unrelated tuning changes are excluded.
- An independent [patch review](../results/preflight/7.0-qwen-sm70/patch-review.json)
  applied the patch with `--fuzz=0` and reproduced the candidate source bytes.
- The first CUDA compile revealed one forward-port interface mismatch: b10775
  requires an explicit `use_sparse` argument on `launch_fattn`. The corrected
  GQA-only call supplies `false`, matching the neighboring existing vector
  call. The failed build log and original patch are preserved; see
  [build correction](../results/preflight/7.0-qwen-sm70/build-correction.json).
- The compile-time switch defaults to 1 and enables the new branch at
  `GGML_CUDA_FATTN_VEC_GQA_HEADS=2`. Dispatch additionally requires
  `Q->ne[1] == 1` and GQA ratio ≥ 2. C2 joint decode can therefore bypass this
  branch; compile-time inclusion does not prove measured-window use.

The [MTP serving reference](https://github.com/jackinthebox52/qwen38-v100-serve/tree/7080181335f660cbb801c9ccb68e1a74697b5604)
describes a different base (b10793) and is supporting evidence only. WBS 7
retains b10775; external performance figures are not imported as results.

Build verification is complete. Evidence is retained under
[results/preflight/7.0-qwen-sm70](../results/preflight/7.0-qwen-sm70/).
The original control's complete CMake flags are unavailable; candidate flags
are recorded explicitly. A rebuilt candidate must not be described as a
bitwise-controlled kernel-only A/B comparison.

The final [receipt](../state/wbs7-preflight.json) records the full build
command, CMake cache, toolchain and correction history. The successful build
uses CUDA architecture 70, Release, Flash Attention and CUDA graphs on,
NCCL/RPC on, and `GGML_CUDA_FATTN_VEC_GQA_HEADS=2`. A link-only CUDA driver
stub search path was needed in the builder; runtime loading resolves the real
driver library.

| Identity | SHA256 / value |
| --- | --- |
| GQA-only patch | `25632d838c5e04c6b32920e5f61c39868e995d83156cb315ff477cf287197f80` |
| Candidate image | `sha256:5a247f632e6b3922d6d33906e9ccc16739391f2088f3488427ef4fb88221f262` |
| Candidate `llama-server` | `4c126892b08b2951b9d97c0172700693a05a3a71b1857f2c7053b7359e57a71d` |
| Candidate `libggml-cuda.so.0.22.0` | `5d3ea1ba757dbe04f61f0fbac73277823d418962f9cf65bfe97aaa86731fba94` |
| Control `libggml-cuda.so.0.22.0` | `41c55516c675015d3f0c3d7a8feacc38bdb0365ee6fc8dbc36dc6c23f7493dc5` |

The candidate reports b10775 and the full pinned commit. Its server resolves
`libggml-cuda.so.0` from `/opt/wbs7/bin`; `libcuda.so.1` and `libnccl.so.2`
resolve to runtime system libraries. Symbol inspection found 24 grouped-GQA
kernel symbols in the candidate and 0 in the control. This proves compile-time
inclusion only. No model load or GPU inference was used in these checks.

## Scope and next steps

No short generation, warmup, calibration or measured request is part of this
step. The control is reused without rerunning it. No combined MTP+GQA candidate
is created. WBS 7.1 and WBS 7.2 each permit only their single specified C2
128K-per-slot measured execution when separately requested. Static support
does not guarantee memory fit or output correctness.
