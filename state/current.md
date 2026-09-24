# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp C1: DONE.
- Gemma4 TARGET: PASS_C1_128K — prefill 524.64 tok/s, decode 68.10 tok/s.
- Gemma4 NGRAM: PASS_C1_128K — prefill 526.51 tok/s, decode 64.39 tok/s.
- Gemma4 corrected MTP: PASS_C1_128K — prefill 526.99 tok/s, decode 45.49 tok/s, 548/1088 accepted (50.368%), peak VRAM 8983/9101 MiB.
- Gemma4 corrected MTP_NGRAM: PASS_C1_128K — prefill 518.28 tok/s, decode 45.53 tok/s, 548/1088 accepted (50.368%), peak VRAM 8983/9121 MiB.
- Gemma4 MTP attempt 001 with CUDA0-only drafter remains configuration-specific FAIL_STARTUP evidence; it is not the final lane verdict.
- Validated Gemma4 V100 MTP contract: TP2 layer split + smart-Q4_0 companion n=4 + --spec-draft-device CUDA0,CUDA1.
- All WBS 2.1 llama.cpp C1 model items are complete.
- Next planned WBS item: 2.2.1 Qwen3.8-27B STOCK C1 128K.
- Do not launch the next lane automatically.
