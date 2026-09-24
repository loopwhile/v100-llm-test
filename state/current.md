# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp: IN_PROGRESS — corrected MTP device placement.
- TARGET: PASS_C1_128K — prefill 524.64 tok/s, decode 68.10 tok/s.
- NGRAM: PASS_C1_128K — prefill 526.51 tok/s, decode 64.39 tok/s.
- MTP attempt 001 with `--spec-draft-device CUDA0`: FAIL_STARTUP, preserved as configuration-specific evidence.
- Root cause diagnostic D2.1.4D: PASS_STARTUP at exact TP2/full-offload/128K/layer-split baseline when only draft devices changed to `CUDA0,CUDA1`.
- Operational root cause: on pinned b10775 + 2×V100 layer split, CUDA0-only drafter placement is incompatible with the target context/KV placement across CUDA0/CUDA1; aligning drafter devices with both GPUs removes the startup crash.
- Corrected model contract: `--spec-draft-device CUDA0,CUDA1`, smart-Q4_0 companion, MTP n=4.
- Next measured execution: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C1-128K-20260924-002` only.
- MTP_NGRAM is reopened but must not run until corrected MTP C1 is reviewed.
- No automatic retry and no automatic next-lane launch.
