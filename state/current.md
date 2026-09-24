# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp baseline C1: DONE.
- Gemma4 TARGET: PASS_C1_128K — prefill 524.64 tok/s, decode 68.10 tok/s, peak VRAM 8775/8785 MiB.
- Gemma4 NGRAM: PASS_C1_128K — prefill 526.51 tok/s, decode 64.39 tok/s; 4/96 draft tokens accepted; NGRAM performance effectiveness deferred to Phase 5.
- Gemma4 MTP baseline: FAIL_STARTUP — target and companion checksums exact, preflight PASS, Gemma4 assistant draft initialization crashed with server exit 139 before any measured request.
- Gemma4 MTP companion identity correction: pinned `mtp-gemma-4-26B-A4B-it.gguf` is the Unsloth smart Q4_0 drafter, not Q8_0.
- Gemma4 MTP_NGRAM baseline disposition: UNSUPPORTED on the pinned default-fit runtime because it shares the failed assistant-draft startup dependency.
- Supplemental diagnostic D2.1.4A: IN_PROGRESS — same b10775/model/drafter/TP2/MTP n=4, startup-only, with `--fit off` as the sole runtime change.
- D2.1.4A does not overwrite the baseline FAIL_STARTUP and does not reuse the measured experiment ID.
- No automatic retry and no automatic next-lane launch.
