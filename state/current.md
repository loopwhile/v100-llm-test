# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp C1: DONE.
- All WBS 2.1 llama.cpp C1 model items are complete.
- WBS 2.2 execution contract is prepared in `docs/WBS-2.2-execution-manifest.md`.
- WBS 2.2 measured runner: `scripts/run_c1_onecat.py`.
- 2.2.1 Qwen3.8 STOCK: CLOSED — 128K CAPACITY PASS / OUTPUT INTEGRITY FAIL (Attempt 002~007 verified 128K hardware capacity PASS, but failed output integrity due to repetition loop across greedy, stochastic, thinking-off, and reasoning-effort low modes; measured inference budget 2/2 exhausted; closed as FAIL_OUTPUT).
- 2.2.2 Ornith 9B STOCK: DONE — PASS_C1_128K (EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-003; TTFT 165.43s, Decode 8.98 tok/s, Wall 201.64s).
- 2.2.3 Ornith 35B STOCK: DONE — PASS_C1_128K (EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-002; TTFT 62.05s, Decode 10.45 tok/s, Wall 118.88s).
- 2.2.4 Gemma4 26B STOCK: CLOSED — FAIL_STARTUP (EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-002; 1Cat-vLLM 1.5.0 SM70 TurboMind NVFP4 MoE does not support Gemma4 MoE architecture shape (2816, 704, 128, 8) and gelu_pytorch_tanh activation).
- Current task: WBS 2.2 all 4 items are evaluated and closed. WBS 2.2.1 measured inference limit (2/2) reached. Stopped per policy.
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


## Next planned work after current stop

- Remaining project scope is WBS 3, WBS 4, and revised WBS 5 only. There is no separate deployment-selection phase.
- WBS 3: C2 capacity/residency/active-overlap testing for eligible C1 lanes.
- WBS 4: Ornith 1.5 9B 1GPU×2 + LiteLLM topology validation.
- WBS 5: performance optimization and per-model/per-runtime final recipe capture.
- Qwen3.8 1Cat-vLLM receives one additional bounded **128K recovery recipe validation** before further performance tuning:
  - keep 128K (`max_model_len=131072`) and the proven capacity enablers `--language-model-only`, util=0.92, and `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`;
  - switch to the historically stable Qwen 1Cat path: E5M2 KV, GDN Triton prefill, `VLLM_SM70_GDN_DECODE_FLASHQLA=0`, thinking=false, eager, target-only;
  - use a 128K workload, not 64K/96K;
  - exactly one measured inference;
  - preserve the old E4M3 128K failure as a separate configuration.
- Historical p520-inference-lab Profile 007 fast-path results may guide WBS 5 option candidates, but are not imported as fresh acceptance evidence.
