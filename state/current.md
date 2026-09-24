# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp C1: DONE.
- All WBS 2.1 llama.cpp C1 model items are complete.
- WBS 2.2 execution contract is prepared in `docs/WBS-2.2-execution-manifest.md`.
- WBS 2.2 measured runner: `scripts/run_c1_onecat.py`.
- 2.2.1 Qwen3.8 STOCK: READY — QUASAR NVFP4, explicit fp8_e4m3, target-only.
- 2.2.2 Ornith 9B STOCK: READY FOR HOST COMPATIBILITY GATE — FP16 KV, MTP1, target FLASH_ATTN_V100, draft TRITON_ATTN.
- 2.2.3 Ornith 35B STOCK: READY FOR HOST COMPATIBILITY GATE — explicit fp8_e5m2, target-only, FLASH_ATTN_V100.
- 2.2.4 Gemma4 26B STOCK: READY AFTER DOWNLOAD — nvidia/Gemma-4-26B-A4B-NVFP4@a19cfe00be84568a6867111c9a68c9c44fdcffe6, FP16 KV, target-only, TRITON_ATTN.
- Next planned measured execution: WBS 2.2.1.
- If the user explicitly delegates all of WBS 2.2, follow the execution manifest sequentially without re-research or per-item re-planning.
- A failed WBS 2.2 item must not be silently retried with changed KV/quant/spec/context/topology. Independent later WBS 2.2 items may proceed under their own pinned contracts when the user delegated the full section.
- Do not launch work beyond WBS 2.2 automatically.
