# Current execution

## WBS 3 authoritative workload reset — 2026-09-25

- User approved redesigning the flawed C2 workload and rerunning **all runnable WBS 3 lanes**, including Qwen3.8 and Ornith 9B.
- Authoritative WBS 3 workload: `workloads/concurrency/v2.json`; semantic oracle: `workloads/concurrency/v2-ground-truth.json`.
- `workloads/concurrency/v1.json` and all existing v1 raw artifacts remain immutable historical evidence.
- v2 uses one seeded defect per project anchor, one-time anchor inclusion, safe `{{SECTION}}`-variant calibration padding, structured 300+ token engineering output, and pre-registered semantic criteria.
- Harness concurrency evidence is now independent of output verdict; output underfill/wrong semantics cannot erase observed `QUEUE_ONLY` or active-overlap topology.
- WBS 3.1 llama.cpp v2 scope: Qwen TARGET/NGRAM; Ornith 9B TARGET/NGRAM/MTP/MTP_NGRAM; Ornith 35B TARGET/NGRAM/MTP/MTP_NGRAM; Gemma4 TARGET/NGRAM/corrected-MTP/corrected-MTP_NGRAM.
- WBS 3.2 1Cat v2 scope: Qwen3.8 B200-aligned E4M3, Ornith 9B MTP1/FP16, Ornith 35B target-only/E5M2. Gemma4 remains ineligible from C1 FAIL_TIMEOUT.
- v100-skinny remains CLOSED/UNSUPPORTED and is not rerun.
- Historical v1 Qwen/Ornith9 C2 results remain diagnostics, not authoritative v2 acceptance.
- No GPU experiment is launched by these design commits. Use fresh experiment IDs for v2.
- Execution runners are now wired for both shared-TP2 families: `scripts/run_c2_llama.py` and `scripts/run_c2_onecat.py`.
- Do not advance to WBS 4/5 until WBS 3 v2 matrix is complete.

## Previous execution record

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
- 2.2.4 Gemma4 26B STOCK: CLOSED — FAIL_TIMEOUT (Bounded Recovery Closed).
  - Historical NVFP4 run: `EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-002` failed at startup because 1Cat-vLLM 1.5.0 SM70 TurboMind NVFP4 MoE does not support Gemma4 MoE architecture shape (2816, 704, 128, 8) and gelu_pytorch_tanh activation.
  - Revalidation AWQ INT4 initial run: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001` failed at startup (`FAIL_STARTUP`) due to transformers 5.16.1 heterogeneous attention head_dim initialization defect.
  - Bounded Recovery Attempt 1: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-002` — `FAIL_CRASH` (heterogeneous hook fixed all 30 layers; shard loaded 100%; startup healthy; crashed during 128K prefill with Triton CUDA OOM; peak VRAM 15,243 MiB).
  - Bounded Recovery Attempt 2: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-003` — `FAIL_CRASH` (`--language-model-only` disabled vision tower; but `gpu_memory_utilization=0.90` expanded KV cache to 4.78 GiB, leaving 1.13 GiB free VRAM; Triton kernel spilled 10,896 B/thread requiring 1.66 GiB driver local stack, causing `cuLaunchKernel` OOM; peak VRAM 15,253 MiB).
  - Bounded Recovery Attempt 3 (Final): `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-004` — `FAIL_TIMEOUT` (`gpu_memory_utilization=0.80`, `VLLM_SM70_TRITON_ATTN_PREFILL_TILE_SIZE=16`, `SAFE_DEFAULTS=1`; startup healthy, VRAM rock solid at 13,663 MiB with 2.7 GiB headroom; no OOM, no crash, post-health 100% OK; but 128K chunked prefill with 512-dim attention on SM70 took > 1,800s, reaching client HTTP timeout).
- Previous task: WBS 3.2.2 Ornith 1.5 9B STOCK C2 v2 execution complete (`EXP-V100-ORN15-9B-1CAT-F16-MTP1-C2-128K-20260925-003`). Verdict is PASS_C2_ACTIVE (Peak processing 2.0, Peak waiting 0.0, resident true, active_overlap true; TTFT 310.90s, Aggregate decode 15.60 tok/s, Wall 458.71s; Peak VRAM 13,901 MiB; Project A 865 tokens PASS, Project B 1,460 tokens PASS).
- Next task: WBS 3.2.3 Ornith 1.5 35B-A3B STOCK C2 v2 (`EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C2-128K-20260925-001`).

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

## Gemma4 26B-A4B 1Cat-vLLM AWQ INT4 C1 Revalidation & Bounded Recovery (2026-09-25)
- Purpose: Revalidate Gemma4 26B-A4B on 1Cat-vLLM 1.5.0 using the AWQ INT4 (`compressed-tensors`) artifact (`cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4@18a3c7285c33ee39d3e5e16ee6fb2c18f4955ef9`), followed by up to 3 user-authorized bounded recovery attempts.
- Backend Verification Reality:
  - Dense / mixed-precision linear: `Using MarlinLinearKernel for CompressedTensorsWNA16` and `Using MarlinLinearKernel for mixed-precision linear` (Marlin active).
  - Gemma4 MoE: `Using CompressedTensorsWNA16MoEMethod` (generic MoE, **not** `CompressedTensorsWNA16MarlinMoEMethod`). Past documentation referring to "SM70 Marlin MoE path" was an overstatement and is corrected.
  - Attention backend: `TRITON_ATTN`.
- Execution Sequence & Outcomes (Max 3 retries exhausted):
  1. `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001` — **FAIL_STARTUP**:
     - Model weight loading crashed at 0% shard progress with `AssertionError: Attempted to load weight (torch.Size([512])) into parameter (torch.Size([256]))`.
     - Root cause: `transformers 5.16.1` moved `global_head_dim` into `per_layer_config`, leaving `Gemma4TextConfig` without the global attribute. `gemma4.py` defaulted full-attention layers (5, 11, 17, 23, 29) to `head_dim=256` instead of `512`.
  2. Attempt 1: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-002` — **FAIL_CRASH**:
     - Key modification: Implemented repo-local runtime hook (`scripts/runtime_hooks/sitecustomize.py`) to preserve `global_head_dim=512` and dynamically wrap `Gemma4DecoderLayer.__init__` to instantiate full-attention layers with 512/2 and sliding layers with 256/8.
     - Outcome: All 30 layers correctly instantiated; checkpoint shard 100% loaded (16.20s, 9.85 GiB VRAM); server healthy startup achieved. Measured 128K request sent, but crashed during attention prefill with `RuntimeError: Triton Error [CUDA]: out of memory` in `triton_unified_attention.py:1080` (`kernel_unified_attention`). Peak VRAM: 15,243 MiB.
  3. Attempt 2: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-003` — **FAIL_CRASH**:
     - Key modification: Enabled `--language-model-only` via `config/models/gemma4-26b-a4b.json`, turning the multimodal vision tower into `StageMissingLayer` and removing multimodal encoder cache.
     - Outcome: Model memory decreased, but with `gpu_memory_utilization=0.90`, vLLM expanded KV cache to 4.78 GiB (294,344 tokens), leaving device free memory still at only 1,131 MiB. Triton attention prefill kernel spilled 10,896 bytes/thread to local memory (`n_local`), requiring 1.66 GiB driver local stack, exceeding the 1.13 GiB free memory and causing `cuLaunchKernel` to throw `Triton Error [CUDA]: out of memory`. Peak VRAM: 15,253 MiB.
  4. Attempt 3 (Final): `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-004` — **FAIL_TIMEOUT**:
     - Key modification: Decreased `gpu_memory_utilization` to `0.80` (expanding free VRAM headroom to 3.28 GiB while reserving 195,000 KV tokens, well above 128K) and configured SM70 Triton Attention tuning: `VLLM_SM70_TRITON_ATTN_PREFILL_TILE_SIZE=16`, `VLLM_SM70_TRITON_ATTN_SAFE_DEFAULTS=1`.
     - Outcome: Server started cleanly. VRAM usage remained completely stable at 13,663 MiB (2.7 GiB headroom). No OOM, no crash. Both GPUs sustained 100% compute continuously. However, 128K chunked prefill (31 chunks) with 512 head dimension and tile size 16 on SM70 Volta required > 1,800 seconds, exceeding the benchmark adapter HTTP timeout (`terminal_s: 1800.44s`). Post-test server health check confirmed server remained 100% healthy (`post_health: {"healthy": true}`).
- Conclusion:
  - Gemma4 26B-A4B 1Cat-vLLM AWQ INT4 fails to complete C1 128K measured inference within the 1,800s timeout on 2x V100 SXM2 TP2 (`FAIL_TIMEOUT`).
  - All 3 user-authorized bounded recovery retries are exhausted. Per policy and user instruction, no fourth retry will be attempted.
  - Gemma4 1Cat-vLLM remains **not eligible** for C2 capacity testing or WBS 5 throughput optimization.
- Policy Enforcement: Stopped per contract. Raw evidence is preserved under `results/raw/EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001/` through `-004/`.

## Next planned work after current stop

- Remaining project scope is authoritative WBS 3 v2 revalidation across all runnable llama.cpp/1Cat lanes, then WBS 4 and WBS 5.
- Existing WBS 3 v1 Qwen/Ornith9 results are historical diagnostics; final WBS 3 acceptance is reset to v2.
- WBS 4: Ornith 1.5 9B 1GPU×2 + LiteLLM topology validation.
- WBS 5: performance optimization and per-model/per-runtime final recipe capture.
