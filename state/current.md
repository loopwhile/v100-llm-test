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
- Previous task: WBS 3.2 (1Cat-vLLM STOCK C2 v2) execution complete:
  - 3.2.1 Qwen3.8-27B (`EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C2-128K-20260925-002`): QUEUE_ONLY / FAIL_OUTPUT (Project A passed, Project B failed length/repetition; queue_only confirmed).
  - 3.2.2 Ornith 1.5 9B (`EXP-V100-ORN15-9B-1CAT-F16-MTP1-C2-128K-20260925-003`): PASS_C2_ACTIVE (Peak processing 2.0, resident true, active_overlap true; TTFT 310.90s, Aggregate decode 15.60 tok/s; Project A 865 tok PASS, Project B 1460 tok PASS).
  - 3.2.3 Ornith 1.5 35B-A3B (`EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C2-128K-20260925-001`): PASS_C2_ACTIVE (Peak processing 2.0, resident true, active_overlap true; TTFT 113.71s, Aggregate decode 9.57 tok/s; Project A 947 tok PASS, Project B 1181 tok PASS).
- Previous task: WBS 3.1 llama.cpp C2 v2 matrix execution complete ([DONE]):
  - 3.1.1 Qwen3.8-27B [DONE]:
    - TARGET (`EXP-V100-Q38-LLAMA-Q80-TARGET-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 925.17s, Aggregate decode 1.83 tok/s, Batch Wall 1,446.44s; Project A 886 tok PASS, Project B 842 tok PASS).
    - NGRAM (`EXP-V100-Q38-LLAMA-Q80-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 925.67s, Aggregate decode 2.16 tok/s, Batch Wall 1,489.30s; Project A 886 tok PASS, Project B 1249 tok PASS; NGRAM draft 288/86 A, 561/117 B).
  - 3.1.2 Ornith 1.5 9B [DONE]:
    - TARGET (`EXP-V100-ORN15-9B-LLAMA-F16-TARGET-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 264.40s, Aggregate decode 9.17 tok/s, Batch Wall 425.82s; Project A 1190 tok PASS, Project B 1402 tok PASS; Peak VRAM 8,235 MiB).
    - NGRAM (`EXP-V100-ORN15-9B-LLAMA-F16-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 264.44s, Aggregate decode 7.76 tok/s, Batch Wall 417.21s; Project A 897 tok PASS, Project B 1235 tok PASS; Peak VRAM 8,311 MiB; NGRAM draft 288/76 A, 350/65 B).
    - MTP (`EXP-V100-ORN15-9B-LLAMA-F16-MTP-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 325.09s, Aggregate decode 7.85 tok/s, Batch Wall 509.80s; Project A 894 tok PASS, Project B 1686 tok PASS, B decode 41.29 tok/s; Peak VRAM 10,009 MiB; MTP draft 1023/552 54.0% A, 1911/1048 54.8% B).
    - MTP_NGRAM (`EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 324.95s, Aggregate decode 6.45 tok/s, Batch Wall 498.39s; Project A 879 tok PASS, Project B 1168 tok PASS, B decode 39.83 tok/s; Peak VRAM 10,071 MiB; draft 1173/558 47.6% A, 1554/747 48.1% B).
  - 3.1.3 Ornith 1.5 35B-A3B [DONE]:
    - TARGET (`EXP-V100-ORN15-35B-LLAMA-Q80-TARGET-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 815.97s, Aggregate decode 3.07 tok/s, Batch Wall 1,183.89s; Project A 917 tok PASS, Project B 1217 tok PASS, B decode 29.91 tok/s; Peak VRAM 12,831 MiB GPU0 / 12,309 MiB GPU1).
    - NGRAM (`EXP-V100-ORN15-35B-LLAMA-Q80-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 816.17s, Aggregate decode 2.83 tok/s, Batch Wall 1,183.06s; Project A 867 tok PASS, Project B 1098 tok PASS, B decode 27.83 tok/s; Peak VRAM 12,831 MiB; draft 312/80 25.6% A, 272/68 25.0% B).
    - MTP (`EXP-V100-ORN15-35B-LLAMA-Q80-MTP-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 857.77s, Aggregate decode 3.50 tok/s, Batch Wall 1,251.11s; Project A 1030 tok PASS, Project B 1566 tok PASS, B decode 34.97 tok/s; Peak VRAM 12,897 MiB GPU0 / 13,737 MiB GPU1; draft 574/455 79.3% A, 888/677 76.2% B).
    - MTP_NGRAM (`EXP-V100-ORN15-35B-LLAMA-Q80-MTP-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 860.09s, Aggregate decode 2.70 tok/s, Batch Wall 1,240.18s; Project A 905 tok PASS, Project B 1065 tok PASS, A decode 29.38 tok/s; Peak VRAM 12,897 MiB GPU0 / 13,737 MiB GPU1; draft 759/445 58.6% A, 858/463 54.0% B).
  - 3.1.4 Gemma4 26B-A4B [DONE]:
    - TARGET (`EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 447.02s, Aggregate decode 4.77 tok/s, Batch Wall 667.36s; Project A 924 tok PASS, Project B 1068 tok PASS; Peak VRAM 10,039 MiB GPU0 / 10,537 MiB GPU1).
    - NGRAM (`EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 457.15s, Aggregate decode 4.86 tok/s, Batch Wall 689.16s; Project A 1066 tok PASS, Project B 1055 tok PASS; Peak VRAM 10,039 MiB GPU0 / 10,607 MiB GPU1; draft 527/186 35.3% A, 528/141 26.7% B).
    - MTP (`EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 458.73s, Aggregate decode 4.66 tok/s, Batch Wall 697.62s; Project A 1066 tok PASS, Project B 1016 tok PASS; Peak VRAM 10,345 MiB GPU0 / 10,981 MiB GPU1; draft 1160/777 67.0% A, 1112/738 66.4% B, overall 66.7%).
    - MTP_NGRAM (`EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 462.43s, Aggregate decode 4.59 tok/s, Batch Wall 703.74s; Project A 1058 tok PASS, Project B 1016 tok PASS; Peak VRAM 10,345 MiB GPU0 / 11,051 MiB GPU1; draft 1564/800 51.2% A, 1557/748 48.0% B, overall 49.6%).
- Current status: WBS 4 (Ornith 1.5 9B 1GPU×2 + LiteLLM topology) 전체 평가 완료.
  - 4.1.1 TARGET C1: **`PASS_C1_128K`** (`EXP-V100-ORN15-9B-LLAMA-F16-TARGET-1GPU2-C1-128K-20260926-002`; TTFT 190.01s, Prefill 679.04 tok/s, Decode 43.34 tok/s, Batch Wall 202.08s, Peak VRAM GPU0 10,891 MiB / GPU1 10,769 MiB).
  - 4.1.1 TARGET C2: **`PASS_C2_ACTIVE`** (`EXP-V100-ORN15-9B-LLAMA-F16-TARGET-1GPU2-C2-128K-20260926-001`; TTFT 186.45s, Prefill 692.18 tok/s, Mean Decode 43.51 tok/s, Aggregate Decode 77.40 tok/s, Batch Wall 220.01s, Peak VRAM GPU0 10,893 MiB / GPU1 10,893 MiB).
  - 4.1.2 NGRAM C2: **`PASS_C2_ACTIVE`** (`EXP-V100-ORN15-9B-LLAMA-F16-NGRAM-1GPU2-C2-128K-20260926-001`; TTFT 186.98s, Prefill 690.25 tok/s, Mean Decode 44.31 tok/s, Aggregate Decode 77.66 tok/s, Batch Wall 220.96s, NGRAM 수락률 24.75%, Peak VRAM GPU0 10,895 MiB / GPU1 10,895 MiB).
  - 4.1.3 MTP C2: **`PASS_C2_ACTIVE`** (`EXP-V100-ORN15-9B-LLAMA-F16-MTP-1GPU2-C2-128K-20260926-001`; TTFT 208.55s, Prefill 618.85 tok/s, Mean Decode 51.01 tok/s (+17.2%), Aggregate Decode 75.34 tok/s, Batch Wall 235.74s, MTP 수락률 53.27%, Peak VRAM GPU0 11,903 MiB / GPU1 11,903 MiB).
  - 4.1.4 MTP_NGRAM C2: **`PASS_C2_ACTIVE`** (`EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-1GPU2-C2-128K-20260926-001`; TTFT 208.74s, Prefill 618.26 tok/s, Mean Decode 49.96 tok/s, Aggregate Decode 79.35 tok/s, Batch Wall 234.89s, Speculative 수락률 45.30%, Peak VRAM GPU0 11,905 MiB / GPU1 11,905 MiB).
  - 4.2.1 STOCK MTP1 C2 (1Cat-vLLM): **`FAIL_STARTUP`** (`EXP-V100-ORN15-9B-1CAT-F16-MTP1-1GPU2-C2-128K-20260926-001`; 1GPU TP1 128K FP16 KV 캐시 필요량 4.68 GiB가 가용 VRAM 2.61 GiB를 초과하여 기동 불가, 최대 시퀀스 한도 ~71.2K로 1GPU 128K 수용 불가 입증 및 CLOSED).
- Conclusion: WBS 4 전체 완료 [DONE]. llama.cpp는 1GPUx2 + LiteLLM topology에서 128K C1/C2 전 레인 완전 통과. 1Cat-vLLM은 현재 exact pinned profile (1Cat-vLLM 1.5.0, Ornith 1.5 9B NVFP4, STOCK MTP1, FP16 KV, TP1, V100 16GB)에서 128K startup 불가 확인 (CLOSED — FAIL_STARTUP). 다음 단계는 WBS 5(최종 서빙 레시피 확정).

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

## WBS 6 CPU+RAM Dual-Resident Feasibility & Preflight (2026-09-26)

- Scope: WBS 6.1 (CPU Docker build), WBS 6.4 (artifact verification), Preflight A/B, and WBS 6.5 (Dual-Resident Startup Gate). 32K measured runs (WBS 6.6) prepared and gated (`[READY]`), requiring explicit `--run-32k-measured` opt-in.
- Models verified:
  - Gemma 4 26B-A4B: `gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf` (23,295,391,456 B, SHA256 `b01ee10a1423c17f9c4384f1fc569726b8782c5403557ff138ceb9468ca49d6b`, `unsloth/gemma-4-26B-A4B-it-GGUF@c099eb48e663fd284577b04978a94ffccb261841`).
  - Ornith 1.5 35B-A3B: `Ornith-1.5-35B-Q4_K_M.gguf` (21,713,463,040 B, SHA256 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`, `ornith-ai/Ornith-1.5-35B-A3B-GGUF@12393612fd4f730ff5aadc23e9b8f9648aa49ceb`).
- Preflight A/B Comparison (`results/raw/WBS6-PREFLIGHT-AB/preflight_ab_result.json`):
  - P520 Xeon W-2135 native build (`GGML_NATIVE=ON`, `GGML_CUDA=OFF`, single native backend).
  - Comparison on Ornith 35B (760 prompt tokens, 128 completion tokens, 4 threads, cpuset `1,2,3,4`):
    - `b10428` (`885c5bbe`): TTFT 21.67s, Prompt Eval 35.07 tok/s, Decode 10.05 tok/s, Duration 34.33s.
    - `b10775` (`67a17c17`): TTFT 21.61s, Prompt Eval 35.18 tok/s, Decode 10.02 tok/s, Duration 34.29s.
  - Winner: No material CPU regression observed for `b10775` relative to `b10428` in the pinned preflight workload (prompt 35.18 vs 35.07 tok/s, decode 10.02 vs 10.05 tok/s). Pinned image: `p520-cpu-llama:b10775` (`p520-cpu-llama@sha256:8ee3818eee9df3690a64177b976692cffd509972cb31c0907f7136b567a4729b`).
- WBS 6.5 Dual-Resident Startup Gate (`results/raw/WBS6-STARTUP-GATE/startup_gate.json`):
  - Verdict: **`PASS_STARTUP_GATE`**.
  - Server A: `p520-cpu-gemma` (Port 8082, Gemma 4 26B UD-Q6_K_XL, server ctx-size 131,072).
  - Server B: `p520-cpu-ornith` (Port 8083, Ornith 1.5 35B Q4_K_M, server ctx-size 131,072).
  - Both servers simultaneously healthy (`/health` 200 OK).
  - CPU Coexistence: logical CPU IDs 1, 2, 3, 4 (mapped to physical CORE 1, 2, 3, 4); Core 0, 5 & SMT siblings preserved for host OS / GPU serving.
  - GPU VRAM Isolation: CPU-only Docker with no GPU devices passed, `GGML_CUDA=OFF`, `--n-gpu-layers 0`; GPU VRAM allocation = 0.0 MiB, Compute Apps = 0. GPU0/GPU1 serving may exist independently.
  - Memory Evidence & Limits: Host Total 62.56 GiB, Available 31.59 GiB at snapshot. SwapTotal 4,194,300 kB, SwapFree 528 kB (~4GB swap in use). Startup gate proved dual server startup, health, and 0B VRAM isolation; it did not measure `pswpin`/`pswpout`/`pgmajfault` deltas, so absence of swap thrash is unproven at gate time. Due to `mmap`, initial MemAvailable does not guarantee physical RAM headroom once working sets fault in; memory pressure and stability will be measured during 32K request execution.
  - Post-gate cleanup: Both containers cleanly removed after verification per contract.
- Status: WBS 6.1~6.5 [DONE]. WBS 6.6 (32K serial inference with 128K context capacity) is [READY] with Checkpoints A~G (`baseline_before_startup`, `startup_healthy`, `gemma_pre`, `gemma_post`, `ornith_pre`, `ornith_post`, `final_post_health`), `memory-baseline-before-startup.json` persistence, failure-resilient delta telemetry, and raw evidence immutability guards implemented; awaiting user execution command. WBS 6.7 [TODO].

## Next planned work

- WBS 2: DONE
- WBS 3: DONE
- WBS 4: DONE
- WBS 6.1~6.5: DONE (Startup Gate PASS)
- WBS 6.6: READY (32K serial measured requests wired with Checkpoints A~G and immutability guards, gated on `--run-32k-measured`)
- WBS 6.7: TODO (verdict `PASS_CPU_128K_SERVER_32K_REQUEST_DUAL_RESIDENT`)
- Next = Execute WBS 6.6 (32K serial runs with `--run-32k-measured`) or proceed to WBS 5 (optimization & final recipe capture).


