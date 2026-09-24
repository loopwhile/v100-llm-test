# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp C1: DONE.
- Gemma4 TARGET: PASS_C1_128K — prefill 524.64 tok/s, decode 68.10 tok/s, peak VRAM 8775/8785 MiB.
- Gemma4 NGRAM: PASS_C1_128K — prefill 526.51 tok/s, decode 64.39 tok/s; 4/96 draft tokens accepted; NGRAM performance effectiveness deferred to Phase 5.
- Gemma4 MTP: FAIL_STARTUP — target and companion checksums exact, preflight PASS, Gemma4 assistant draft initialization crashed with server exit 139 before any measured request.
- Gemma4 MTP_NGRAM: UNSUPPORTED on pinned runtime due the same mandatory assistant-draft startup dependency; no redundant crash replay and no fabricated experiment ID.
- Gemma4 C2 survivors: TARGET and NGRAM only.
- Next planned WBS item: 2.2.1 Qwen3.8-27B STOCK C1 128K.
- No automatic retry and no automatic next-lane launch.
