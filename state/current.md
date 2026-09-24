# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp: IN_PROGRESS — corrected MTP_NGRAM remains.
- TARGET: PASS_C1_128K — prefill 524.64 tok/s, decode 68.10 tok/s.
- NGRAM: PASS_C1_128K — prefill 526.51 tok/s, decode 64.39 tok/s.
- MTP attempt 001 with CUDA0-only drafter: FAIL_STARTUP, preserved as configuration-specific evidence only.
- Corrected MTP attempt 002 with smart-Q4_0 drafter n=4 on CUDA0,CUDA1: PASS_C1_128K — prefill 526.99 tok/s, decode 45.49 tok/s, 548/1088 accepted (50.368%), peak VRAM 8983/9101 MiB.
- Validated Gemma4 V100 MTP contract: TP2 layer split + --spec-draft-device CUDA0,CUDA1.
- Next measured execution: corrected MTP_NGRAM C1 128K only.
- Do not run any other lane automatically.
