# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp baseline C1: DONE.
- Gemma4 TARGET: PASS_C1_128K — prefill 524.64 tok/s, decode 68.10 tok/s, peak VRAM 8775/8785 MiB.
- Gemma4 NGRAM: PASS_C1_128K — prefill 526.51 tok/s, decode 64.39 tok/s; 4/96 draft tokens accepted.
- Gemma4 MTP baseline: FAIL_STARTUP — target and smart-Q4_0 companion checksums exact; assistant draft initialization crashed before measurement.
- D2.1.4A fit-off diagnostic: DONE — FAIL_STARTUP, exit 139. Memory fitting is not the sole cause.
- CLI diagnostic on the same b10775 also exited 139. The decisive backend error was: pre-allocated tensor cache_k_l28 in CUDA1 buffer cannot run operation NONE, during speculative context graph reservation.
- D2.1.4B row-split diagnostic: DONE — diagnostic topology unsupported. V100 CUDA0 rejected row split at target load with `device CUDA0 does not support split buffers`; this does not classify the MTP failure.
- D2.1.4C single-GPU diagnostic: DONE — INCONCLUSIVE. CUDA0-only + 8K + target -ngl 20 exited 132(SIGILL); partial CPU offload was introduced simultaneously, so it does not isolate the TP2 placement variable cleanly.
- Supplemental diagnostic D2.1.4D: IN_PROGRESS — restore baseline TP2/full-offload/128K/layer split and change only draft device CUDA0 -> CUDA0,CUDA1.
- Baseline acceptance results are not overwritten by diagnostics.
- No automatic next-lane launch.
