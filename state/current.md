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
- Supplemental diagnostic D2.1.4C: IN_PROGRESS — same b10775/artifacts/MTP n=4, CUDA0 only, 8K context, partial target GPU offload, startup-only. This removes CUDA1 entirely to isolate the multi-GPU placement dependency.
- Baseline acceptance results are not overwritten by diagnostics.
- No automatic next-lane launch.
