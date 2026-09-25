# WBS 2.2 — 1Cat-vLLM STOCK execution manifest

This file is the pre-decided execution contract for WBS 2.2. It exists so the
benchmark orchestrator does not spend model quota re-researching model/runtime
choices that are already pinned here.

## Execution host and repository flow

The Git checkout lives on the ThinkPad, but measured 1Cat execution must run on
`p520-llm`. Do not run `scripts/run_c1_onecat.py` on the ThinkPad.

Use this WBS 2.2 snapshot:

- ThinkPad checkout: `~/Data/Workspace_VSCode/v100-llm-test`
- P520 snapshot: `/home/loopwhile/v100-llm-test-wbs22-20260924`
- 1Cat Python: `/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python`

Before the first item, from the ThinkPad checkout:

```bash
git pull
python3 scripts/validate_repo.py
python3 -m unittest discover -s tests -q

rsync -av \
  --exclude='.git/' \
  --exclude='results/raw/' \
  --exclude='results/*.nohup.log' \
  ./ p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/
```

Each measured command is executed through SSH with the pinned interpreter
environment, for example:

```bash
ssh p520-llm 'cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
  V100_1CAT_PYTHON=/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python \
  python3 scripts/run_c1_onecat.py ...'
```

After each item finishes, copy only that immutable raw directory back to the
ThinkPad checkout before generating reports or editing Git-tracked closeout
files:

```bash
rsync -av \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/<EXP_ID> \
  results/raw/
```

Then generate the report from the ThinkPad checkout using the raw directory:

```bash
python3 scripts/report_experiment.py results/raw/<EXP_ID>
```

Commit/push the completed item's evidence and closeout before the next item.
When tracked files change between items, rsync the refreshed checkout to the
same P520 snapshot again. The P520 snapshot intentionally has no `.git`;
never run `git pull` there.

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
4. Pinned 1Cat-vLLM 1.5.0's SM70 release matrix explicitly includes Gemma4
   31B AWQ/NVFP4 with TP2 and TP4. Its Gemma4 NVFP4 + E5M2 KV diagnostic path
   is skipped by default because that combination is rejected by SM70 KV-cache
   quantization validation.
5. NVIDIA's Gemma4 26B NVFP4 model card states ordinary upstream vLLM currently
   uses TP=1 for that checkpoint. Do not convert this into either a TP2 PASS or
   FAIL for 1Cat: the pinned 1Cat fork has its own SM70 Gemma TP2 path, so the
   P520 TP2 startup remains the required compatibility gate.
6. Exact remote Gemma4 26B-A4B NVFP4 artifact is pinned to
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
ssh p520-llm 'cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
  V100_1CAT_PYTHON=/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python \
  python3 scripts/run_c1_onecat.py \
    --experiment-id EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-001 \
    --model qwen3.8-27b'
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
ssh p520-llm 'cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
  V100_1CAT_PYTHON=/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python \
  python3 scripts/run_c1_onecat.py \
    --experiment-id EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-001 \
    --model ornith-1.5-9b'
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
ssh p520-llm 'cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
  V100_1CAT_PYTHON=/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python \
  python3 scripts/run_c1_onecat.py \
    --experiment-id EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-001 \
    --model ornith-1.5-35b-a3b'
```

## 2.2.4 Gemma4 26B-A4B STOCK

### Historical NVFP4 Runs (Preserved Evidence)

The initial WBS 2.2.4 runs tested `nvidia/Gemma-4-26B-A4B-NVFP4@a19cfe00be84568a6867111c9a68c9c44fdcffe6` at `/srv/models/gemma-4-26b-a4b-nvfp4`:
- `EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-001` — `FAIL_STARTUP` (transformers 5.16 HeterogeneousConfigMixin per-layer attribute access error).
- `EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-002` — `FAIL_STARTUP` (1Cat-vLLM 1.5.0 SM70 TurboMind NVFP4 MoE does not support shape `(2816, 704, 128, 8)` and `gelu_pytorch_tanh` activation).

These historical failures are artifact-specific and preserved as immutable evidence. The NVFP4 checkpoint has since been deleted from the host.

### Revalidation Contract: AWQ INT4 (compressed-tensors)

User-authorized revalidation replaced the unsupported NVFP4 artifact with the AWQ INT4 compressed-tensors artifact, selecting Marlin for dense/mixed-precision linear (`Using MarlinLinearKernel for CompressedTensorsWNA16`) and generic MoE (`Using CompressedTensorsWNA16MoEMethod`). Note: past references to "SM70 Marlin MoE" were an overstatement and have been corrected.

Status: **CLOSED — FAIL_TIMEOUT (Bounded Recovery Closed)**.

Pinned contract:

- model: `cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4`
- revision: `18a3c7285c33ee39d3e5e16ee6fb2c18f4955ef9`
- local path: `/srv/models/gemma-4-26b-a4b-it-qat-awq-int4`
- weight: AWQ INT4 (`quant_method: compressed-tensors`, `format: pack-quantized`, `int4`, `group_size: 32`)
- quantization flag: `--quantization compressed-tensors`
- KV: FP16 (`float16`)
- speculative: target-only
- attention backend: `TRITON_ATTN`
- environment: `VLLM_SM70_QUANT_BACKEND=marlin`
- topology: TP2 shared

Receipts:
- `config.json`: `8b82e08dc8a4f3a0e7002f88b94d6d3b30d8f136295a30fc5c3144da7bc6d93d`
- `tokenizer_config.json`: `a1bab8c81ed15fa6ce912ec993c66cb49392e0487fb1ea5f5f11ea3618683627`
- `chat_template.jinja`: `94899c0f917d93f6fe81c95744d1e8ddab2d21d39228d2e4aec1fb2a25bff413`
- `model.safetensors`: `c0b6bbe9bacded55f45cd600c703ca299ebfb79efb2ec25023bc6bb563deb201`

Execution Sequence & Bounded Recovery:

1. `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001` — `FAIL_STARTUP`:
   - Server startup failed during shard loading (`0%` progress) with `AssertionError: Attempted to load weight (torch.Size([512])) into parameter (torch.Size([256]))`.
   - Root cause: `transformers 5.16.1` moved `global_head_dim` into `per_layer_config`, causing `gemma4.py` to default full-attention layers (5, 11, 17, 23, 29) to `head_dim=256` instead of `512`.
2. Attempt 1 (`EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-002`) — `FAIL_CRASH`:
   - Modification: Implemented `scripts/runtime_hooks/sitecustomize.py` hook preserving `global_head_dim` and dynamically wrapping `Gemma4DecoderLayer.__init__` for layer-specific dimension resolution.
   - Outcome: All 30 layers resolved correctly (full: 512/2, sliding: 256/8); weights loaded 100% (9.85 GiB VRAM); server healthy startup achieved. Measured 128K request sent, but prefill crashed with `RuntimeError: Triton Error [CUDA]: out of memory` in `kernel_unified_attention`. Peak VRAM: 15,243 MiB.
3. Attempt 2 (`EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-003`) — `FAIL_CRASH`:
   - Modification: Enabled `--language-model-only` to disable multimodal vision tower and encoder cache.
   - Outcome: Weight memory dropped, but `gpu_memory_utilization=0.90` caused vLLM to allocate 4.78 GiB KV cache (294,344 tokens), leaving device free memory still at only 1,131 MiB. Triton attention prefill spilled 10,896 B/thread to local memory, requiring 1.66 GiB driver local stack, exceeding free VRAM and causing `cuLaunchKernel` OOM. Peak VRAM: 15,253 MiB.
4. Attempt 3 (Final, `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-004`) — `FAIL_TIMEOUT`:
   - Modification: Lowered `gpu_memory_utilization` to `0.80` (expanding free VRAM headroom to 3.28 GiB while preserving 195,000 KV tokens, well above 128K) and set `VLLM_SM70_TRITON_ATTN_PREFILL_TILE_SIZE=16`, `VLLM_SM70_TRITON_ATTN_SAFE_DEFAULTS=1`.
   - Outcome: Clean server startup and completely stable VRAM at 13,663 MiB with 2.7 GiB headroom. OOM and kernel crashes eliminated. However, 128K chunked prefill (31 chunks) with 512-dim attention on SM70 took > 1,800s, reaching client HTTP timeout (`terminal_s: 1800.44s`). Post-test server health check confirmed server remained 100% healthy.

Closeout verdict: `CLOSED — FAIL_TIMEOUT (Bounded Recovery Closed)`.
- All 3 user-authorized bounded retries exhausted. No further retries allowed.
- Gemma4 1Cat-vLLM remains ineligible for C2 / WBS 5. Stopped per contract.

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
