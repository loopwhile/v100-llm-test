# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp C1: DONE.
- All WBS 2.1 llama.cpp C1 model items are complete.
- WBS 2.2 execution contract is prepared in `docs/WBS-2.2-execution-manifest.md`.
- WBS 2.2 measured runner: `scripts/run_c1_onecat.py`.
- 2.2.1 Qwen3.8 STOCK: CLOSED — 128K CAPACITY PASS / OUTPUT INTEGRITY FAIL. Attempts 002~007 reproduced repetition failure. A later B200-aligned E4M3 diagnostic preserved 128K capacity and completed non-repetitively, but post-hoc semantic audit found that the 280-token answer did not substantiate the requested concrete cross-file/component correctness risk; its raw harness PASS is preserved while publication remains FAIL_OUTPUT.
- 2.2.2 Ornith 9B STOCK: DONE — PASS_C1_128K (EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-003; TTFT 165.43s, Decode 8.98 tok/s, Wall 201.64s).
- 2.2.3 Ornith 35B STOCK: DONE — PASS_C1_128K (EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-002; TTFT 62.05s, Decode 10.45 tok/s, Wall 118.88s).
- 2.2.4 Gemma4 26B STOCK: CLOSED — FAIL_STARTUP.
  - Historical NVFP4 run: `EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-002` failed at startup because 1Cat-vLLM 1.5.0 SM70 TurboMind NVFP4 MoE does not support Gemma4 MoE architecture shape (2816, 704, 128, 8) and gelu_pytorch_tanh activation.
  - Revalidation AWQ INT4 run: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001` failed at startup (`FAIL_STARTUP`). The SM70 Marlin MoE path was successfully selected (`Using MarlinLinearKernel for CompressedTensorsWNA16`, `Using CompressedTensorsWNA16MoEMethod`), but 1Cat-vLLM 1.5.0's `gemma4.py` heterogeneous `head_dim` initialization failed under `transformers 5.16.1` (global `global_head_dim` stripped into `per_layer_config`, causing full-attention layers 5, 11, 17, 23, 29 to fall back to `head_dim=256` instead of `512`), resulting in `AssertionError: Attempted to load weight (torch.Size([512])) into parameter (torch.Size([256]))` during shard loading. Gemma4 1Cat-vLLM remains ineligible for C2 / WBS 5.
- Current task: WBS 2.2.4 AWQ INT4 C1 revalidation completed and closed as FAIL_STARTUP. Stopped per policy.
- Do not launch work beyond WBS 2.2 automatically.

## Root-Cause Diagnostic: Qwen3.8-27B 1Cat-vLLM 128K Realistic Workload (2026-09-25)
- Purpose: Distinguish whether Qwen3.8 128K repetition collapse is artifact of synthetic repetition-heavy workload (1,333 duplicate sections) or general 1Cat-vLLM 128K path issue.
- Measured Inference: Exactly 1 run executed (`EXP-V100-Q38-1CAT-FP8E4M3-TARGET-DIAG-REALISTIC-128K-20260925-003`).
- Workload: 116 unique source/test/config/doc files (Python 101, JSON 8, MD 6, Shell 1) across 4 repositories; 0 duplicate sections, no benchmark meta-instructions in context. Post-template prompt tokens: 128,832.
- Hardware / Serving: 2x V100 16GB TP2 shared, KV `fp8_e4m3`, context 131,072, `temperature=0.7`, `top_p=0.8`, `presence_penalty=0.0`, `seed=520`, `thinking=True`, `reasoning_effort="medium"`.
- Results:
  - Hardware Capacity: PASS (128,832 tokens prefill in 739.29s, decode 9.76 tok/s, Peak VRAM 15,287 MiB GPU0/1 symmetric, OOM none, post-health 200 OK).
  - Output Integrity: **FAIL_OUTPUT** (Items 18~26 repeated 5 times in an infinite periodic collapse until 2,048 token length limit).
- Conclusion: The hypothesis that exact duplicate-heavy synthetic padding is a **necessary cause** is rejected because repetition collapse also reproduced on a 116-file diversified snapshot. Broader prompt-composition / ultra-long code-dump effects remain possible. Qwen3.8-specific long-context runtime/checkpoint/KV/kernel interaction hypotheses are strengthened, but no single root cause is proven.
- Note: WBS 2.2.1 verdict remains `CLOSED — 128K CAPACITY PASS / OUTPUT INTEGRITY FAIL` (unchanged). Single measured inference budget exhausted; stopped.

## 128K Recovery Validation: Qwen3.8-27B 1Cat-vLLM E5M2/GDN Triton Path (2026-09-25)
- Purpose: Verify whether combining the historically clean Qwen 1Cat execution path (fp8_e5m2 KV, GDN Triton prefill, VLLM_SM70_GDN_DECODE_FLASHQLA=0, FLASH_ATTN_V100, thinking=false, temp=0, top_p=1, seed=38) with proven 128K capacity settings (--language-model-only, util=0.92, partition 256) recovers 128K output integrity.
- Measured Inference: Exactly 1 run attempted (`EXP-V100-Q38-1CAT-FP8E5M2-TARGET-RECOVERY-C1-128K-20260925-001`).
- Hardware / Serving: 2x V100 16GB TP2 shared, KV `fp8_e5m2`, context 131,072, `temperature=0`, `top_p=1`, `seed=38`, `thinking=False`, `--language-model-only`, `gpu_memory_utilization=0.92`, `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`, `VLLM_SM70_GDN_DECODE_FLASHQLA=0`, `--additional-config '{"gdn_prefill_backend":"triton"}'`.
- Results:
  - Final Verdict: **FAIL_STARTUP** (Capacity: **FAIL_CAPACITY**, Integrity: **NOT_REACHED**).
  - Cause: During engine core initialization profiling, Triton prefill kernel memory overhead reduced available KV cache memory to 1.5 GiB, which is insufficient for 131,072 max_model_len requiring 2.15 GiB (`ValueError: To serve at least one request with the model's max seq len (131072), (2.15 GiB KV cache is needed, which is larger than the available KV cache memory (1.5 GiB). Based on the available memory, the estimated maximum model length is 87808.`). Server exited prematurely before measured inference.
  - Peak VRAM: GPU0 13,987 MiB / GPU1 13,987 MiB during profile crash.
- Conclusion:
  - The E5M2 + GDN Triton prefill candidate is **not capacity-compatible with 128K on 2× V100 16GB** (ceiling is ~87.8K tokens).
  - Existing E4M3 128K capacity PASS evidence remains preserved as an independent configuration (`E4M3 128K = Capacity PASS / Output Integrity FAIL`).
  - E5M2-GDN 128K recovery candidate is closed as `FAIL_STARTUP / FAIL_CAPACITY`.
  - Qwen 1Cat 128K recovery test is concluded as failed. Qwen 1Cat is not eligible for WBS 5 throughput optimization.
- Policy Enforcement: Exactly 1 measured inference completed. All further automatic sweeps, retries, and tuning are strictly STOPPED per policy.

## 128K Recipe Diagnostic: Qwen3.8-27B 1Cat-vLLM B200-Aligned Candidate (2026-09-25)
- Purpose: Test a B200-aligned candidate configuration (reasoning-parser qwen3, tool-call-parser qwen3_coder, default-chat-template-kwargs enable_thinking=false, top_k=20, presence_penalty=0.15) on V100 16GB TP2 E4M3. The raw artifact does not preserve an upstream URL/revision receipt, so 'official' provenance is not independently asserted here.
- Measured Inference: Exactly 1 run executed (`EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001`).
- Hardware / Serving: 2x V100 16GB TP2 shared, KV `fp8_e4m3`, context 131,072, `temperature=1.0`, `top_p=0.95`, `top_k=20`, `presence_penalty=0.15`, `frequency_penalty=0.05`, `thinking=False`, `--language-model-only`, `gpu_memory_utilization=0.92`, `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder`, `--default-chat-template-kwargs '{"enable_thinking": false}'`.
- Results:
  - Hardware Capacity: **PASS** (128,834 prompt tokens prefill in 740.60s, decode 9.27 tok/s, Peak VRAM 15,567 MiB GPU0/1, OOM none, post-health 200 OK).
  - Mechanical output integrity: **PASS** for this run (280 tokens, `finish_reason=stop`, no repetition loop/periodic collapse observed).
  - Semantic correctness: **FAIL_OUTPUT**. The answer did not substantiate the requested concrete cross-file/component correctness risk; it only described a generic possible `apply_record` / `stage_artifact` mismatch.
  - Raw harness verdict: `PASS_C1_128K`; authoritative publication verdict after semantic audit: **FAIL_OUTPUT**.
- Conclusion:
  - This run is valid evidence that the tested configuration can hold 128K and can terminate without the earlier repetition collapse in at least one measured execution.
  - It does **not** prove which setting removed repetition, that the effect is repeatable, or that task-level output correctness is recovered.
  - Qwen 1Cat remains **not eligible** for formal C2 promotion or WBS 5 throughput optimization until a user-authorized fresh 128K semantic revalidation passes.

## Gemma4 26B-A4B 1Cat-vLLM AWQ INT4 C1 Revalidation (2026-09-25)
- Purpose: Revalidate Gemma4 26B-A4B on 1Cat-vLLM 1.5.0 using the newly downloaded AWQ INT4 (`compressed-tensors`) artifact (`cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4@18a3c7285c33ee39d3e5e16ee6fb2c18f4955ef9`), bypassing the previously failed SM70 TurboMind NVFP4 MoE gate via `VLLM_SM70_QUANT_BACKEND=marlin`.
- Measured Inference: Not reached (`EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001`).
- Hardware / Serving: 2x V100 16GB TP2 shared, KV `FP16` (`float16`), context 131,072, `--quantization compressed-tensors`, `VLLM_SM70_QUANT_BACKEND=marlin`, `attention-backend TRITON_ATTN`, `max_num_batched_tokens=4096`, `gpu_memory_utilization=0.90`.
- Results:
  - Final Verdict: **FAIL_STARTUP**.
  - Backend Selection Evidence: SM70 Marlin backend was successfully selected and active:
    - `Using MarlinLinearKernel for CompressedTensorsWNA16`
    - `Using MarlinLinearKernel for mixed-precision linear`
    - `Using CompressedTensorsWNA16MoEMethod`
    - SM70 TurboMind NVFP4 MoE path was bypassed as intended.
  - Failure Stage & Root Cause: Model weight loading (`load_weights`) failed at 0% shard progress with:
    `AssertionError: Attempted to load weight (torch.Size([512])) into parameter (torch.Size([256]))`
    at `vllm/model_executor/model_loader/weight_utils.py:1456` via `gemma4.py:1500`.
    - Specific parameter: Layer 5's `k_norm.weight` (and `q_norm.weight`), which in Gemma4's heterogeneous attention architecture has `head_dim = 512` for full-attention layers (layers 5, 11, 17, 23, 29) versus `head_dim = 256` for sliding-attention layers.
    - Upstream defect: Under `transformers 5.16.1`, the heterogeneous configuration mechanism strips global attributes into `per_layer_config[i]`. In 1Cat-vLLM 1.5.0, `Gemma4DecoderLayer` attempts to read `getattr(config, "global_head_dim", config.head_dim)`, which falls back to global default `head_dim = 256` because `global_head_dim` is absent on `Gemma4TextConfig`. Full-attention layers are therefore instantiated with head dimension 256 instead of 512, crashing when loading the 512-element norm weights.
- Conclusion:
  - Gemma4 26B-A4B fails at the compatibility startup gate in 1Cat-vLLM 1.5.0 across both tested quantization formats (historical NVFP4: TurboMind MoE shape rejection; AWQ INT4: heterogeneous full-attention `head_dim` parameter shape mismatch).
  - Gemma4 1Cat-vLLM remains **not eligible** for C2 capacity testing or WBS 5 throughput optimization.
- Policy Enforcement: Stopped per policy. Raw evidence is preserved under `results/raw/EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001/`.

## Next planned work after current stop

- Remaining project scope is WBS 3, WBS 4, and revised WBS 5.
- WBS 3: C2 capacity/residency/active-overlap testing for eligible C1 lanes. Qwen3.8-27B 1Cat-vLLM remains excluded pending a fresh 128K semantic PASS.
- WBS 4: Ornith 1.5 9B 1GPU×2 + LiteLLM topology validation.
- WBS 5: performance optimization and per-model/per-runtime final recipe capture.
- Automatic execution beyond current stop is forbidden without explicit user instruction.
