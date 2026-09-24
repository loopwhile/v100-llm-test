# WBS 2.2 — 1Cat-vLLM STOCK execution manifest

This file is the pre-decided execution contract for WBS 2.2. It exists so the
benchmark orchestrator does not spend model quota re-researching model/runtime
choices that are already pinned here.

## Global contract

- Runtime: pinned 1Cat-vLLM 1.5.0 wheel from `config/runtime-lock.json`.
- Hardware: P520, 2× V100 16GB, shared TP2.
- Context: `max_model_len=131072`.
- Concurrency: C1 only, `max_num_seqs=1`.
- Workload: `workloads/capacity/v1.json`.
- Measured repetitions: exactly 1.
- No full-size warmup.
- No silent fallback to a different KV dtype, quantization, speculative method,
  context length, topology, or artifact.
- Server startup is the runtime-compatibility gate. The measured 128K request is
  sent only after the pinned server plan becomes healthy.
- A startup/OOM/capacity/output failure is recorded as evidence. Do not retry
  under a changed configuration unless the user explicitly authorizes a new
  experiment ID.
- Use `scripts/run_c1_onecat.py` for measured WBS 2.2 runs.
- If the user explicitly delegates “WBS 2.2 전체”, the four items may be
  processed in this order without re-planning. A failed item must not be
  auto-reconfigured; independent later items may still be attempted under their
  own pinned contracts.

## Static upstream findings already resolved

Do not repeat this research during execution.

1. 1Cat-vLLM 1.5.0 contains registered Qwen3.5 and Qwen3.5-MoE model paths,
   including Qwen3.5 MTP support. This is enough to justify a host startup gate
   for the exact Ornith checkpoints, but it is **not** host compatibility proof.
2. On pinned 1Cat-vLLM 1.5.0 + SM70/Flash-V100, the generic `fp8` alias maps
   to `fp8_e5m2`. This project therefore writes E4M3/E5M2 explicitly.
3. The Qwen3.8 QUASAR NVFP4 target-only long-context contract is pinned to
   explicit `fp8_e4m3`.
4. The 1Cat SM70 release matrix treats Gemma4 as a TRITON_ATTN family. Its
   Gemma4 NVFP4 + E5M2 KV diagnostic path is skipped by default because that
   combination is rejected by SM70 KV-cache quantization validation.
5. Exact remote Gemma4 26B-A4B NVFP4 artifact is pinned to
   `nvidia/Gemma-4-26B-A4B-NVFP4@a19cfe00be84568a6867111c9a68c9c44fdcffe6`.
   It must exist at the configured local path before 2.2.4 runs.

Upstream code references:

- `1CatAI/1Cat-vLLM@v1.5.0:vllm/engine/arg_utils.py`
- `1CatAI/1Cat-vLLM@v1.5.0:vllm/config/speculative.py`
- `1CatAI/1Cat-vLLM@v1.5.0:vllm/model_executor/models/qwen3_5.py`
- `1CatAI/1Cat-vLLM@v1.5.0:vllm/model_executor/models/qwen3_5_mtp.py`
- `1CatAI/1Cat-vLLM:benchmarks/run_sm70_release_matrix.py`
- `nvidia/Gemma-4-26B-A4B-NVFP4@a19cfe00be84568a6867111c9a68c9c44fdcffe6`

## 2.2.1 Qwen3.8-27B STOCK

Status before host run: **READY**.

Pinned contract:

- model: `QUASAR-QAT/Qwen3.8-27B-QUASAR-NVFP4`
- revision: `15d2e47bffe5d8ad23928879f8f7d2f74909e259`
- weight: NVFP4
- KV: `fp8_e4m3`
- speculative: target-only
- attention backend: `FLASH_ATTN_V100`
- topology: TP2 shared
- experiment ID:
  `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-001`

Command:

```bash
python3 scripts/run_c1_onecat.py \
  --experiment-id EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-001 \
  --model qwen3.8-27b
```

## 2.2.2 Ornith 1.5 9B STOCK

Status before host run: **READY FOR HOST COMPATIBILITY GATE**.

Pinned compatibility profile:

- model: `ornith-ai/Ornith-1.5-9B-NVFP4`
- revision: `155f200d85ad58464571c77d5e1122ea5d419d7b`
- weight: NVFP4
- KV: FP16
- speculative: MTP, conservative `num_speculative_tokens=1`
- draft attention backend: `TRITON_ATTN`
- target attention backend: `FLASH_ATTN_V100`
- topology: TP2 shared
- experiment ID:
  `EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-001`

Why MTP1: the checkpoint family exposes Qwen3.5 MTP and 1Cat has a Qwen3.5
MTP path; MTP1 is used here as the compatibility profile, not as a performance
optimum. Phase 5 remains responsible for performance tuning.

Command:

```bash
python3 scripts/run_c1_onecat.py \
  --experiment-id EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-001 \
  --model ornith-1.5-9b
```

If startup fails, preserve that exact failure. Do not silently switch to
target-only, another MTP depth, or another KV type.

## 2.2.3 Ornith 1.5 35B-A3B STOCK

Status before host run: **READY FOR HOST COMPATIBILITY GATE**.

Pinned contract:

- model: `ornith-ai/Ornith-1.5-35B-A3B-NVFP4`
- revision: `94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`
- weight: NVFP4
- KV: `fp8_e5m2` explicitly
- speculative: target-only
- attention backend: `FLASH_ATTN_V100`
- topology: TP2 shared
- experiment ID:
  `EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-001`

The previous profile said generic `FP8`. On pinned 1Cat 1.5.0/SM70 that
means E5M2, so this manifest makes the same intent explicit rather than changing
the numerical format.

Command:

```bash
python3 scripts/run_c1_onecat.py \
  --experiment-id EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-001 \
  --model ornith-1.5-35b-a3b
```

## 2.2.4 Gemma4 26B-A4B STOCK

Status before host run: **REMOTE ARTIFACT PINNED; LOCAL DOWNLOAD REQUIRED**.

Pinned contract:

- model: `nvidia/Gemma-4-26B-A4B-NVFP4`
- revision: `a19cfe00be84568a6867111c9a68c9c44fdcffe6`
- local path: `/srv/models/gemma-4-26b-a4b-nvfp4`
- weight: NVFP4
- KV: FP16
- speculative: target-only
- attention backend: `TRITON_ATTN`
- topology: TP2 shared
- experiment ID:
  `EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-001`

Before the run, the exact revision must be downloaded to the configured local
path. Preferred command when the `hf` CLI is already installed:

```bash
hf download nvidia/Gemma-4-26B-A4B-NVFP4 \
  --revision a19cfe00be84568a6867111c9a68c9c44fdcffe6 \
  --local-dir /srv/models/gemma-4-26b-a4b-nvfp4
```

Do not install a new download tool silently. If `hf` is unavailable, report
the missing prerequisite.

After the exact artifact exists:

```bash
python3 scripts/run_c1_onecat.py \
  --experiment-id EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-001 \
  --model gemma4-26b-a4b
```

FP8 KV is not substituted automatically. The current 1Cat SM70 release matrix
specifically records Gemma4 NVFP4 + E5M2 KV as a rejected diagnostic
combination; the compatibility profile therefore starts with FP16 KV.

## Per-item closeout

For each item:

1. inspect `completion.json`, `metrics.json`, `requests.json`,
   `runtime/preflight.json`, `runtime/artifact-check.json`,
   `runtime/cleanup.json`, and `runtime/exit.json`;
2. verify output integrity and post-health;
3. run `python3 scripts/report_experiment.py <raw-dir>`;
4. update summary/comparison evidence;
5. update WBS/state with the exact result;
6. never convert a startup/config failure into a PASS by changing the pinned
   contract under the same experiment ID.
