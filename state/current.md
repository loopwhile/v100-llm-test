# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp C1: DONE.
- All WBS 2.1 llama.cpp C1 model items are complete.
- WBS 2.2 execution contract is prepared in `docs/WBS-2.2-execution-manifest.md`.
- WBS 2.2 measured runner: `scripts/run_c1_onecat.py`.
- 2.2.1 Qwen3.8 STOCK: CLOSED — FAIL_STARTUP (EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-001; KV cache 2.15 GiB > available 1.19 GiB at 128K).
- 2.2.2 Ornith 9B STOCK: DONE — PASS_C1_128K (EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-003; TTFT 165.43s, Decode 8.98 tok/s, Wall 201.64s).
- 2.2.3 Ornith 35B STOCK: DONE — PASS_C1_128K (EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-002; TTFT 62.05s, Decode 10.45 tok/s, Wall 118.88s).
- 2.2.4 Gemma4 26B STOCK: CLOSED — FAIL_STARTUP (EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-002; 1Cat-vLLM 1.5.0 SM70 TurboMind NVFP4 MoE does not support Gemma4 MoE architecture shape (2816, 704, 128, 8) and gelu_pytorch_tanh activation).
- All WBS 2.2 items (2.2.1 ~ 2.2.4) are executed and closed out.
- Next user goal: Investigate and optimize 2.2.1 Qwen 3.8 27B 1Cat-vLLM to make 128K context runnable on 2x V100 16GB.
- If the user explicitly delegates all of WBS 2.2, follow the execution manifest sequentially without re-research or per-item re-planning.
- A failed WBS 2.2 item must not be silently retried with changed KV/quant/spec/context/topology. Independent later WBS 2.2 items may proceed under their own pinned contracts when the user delegated the full section.
- Do not launch work beyond WBS 2.2 automatically.
