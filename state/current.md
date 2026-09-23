# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp C1: IN_PROGRESS.
- 2.1.4 artifact: UD-Q4_K_XL, KV: FP16, topology: tp2-shared, context: C1 128K.
- Base GGUF SHA256: `a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891`.
- Required lanes: TARGET, NGRAM, MTP, MTP_NGRAM.
- Gemma MTP lanes use the pinned separate Q8_0 gemma4-assistant companion via explicit `--model-draft /model/draft.gguf`, `--spec-draft-n-max 4`, and `--spec-draft-device CUDA0`.
- Companion SHA256: `7272d97595f0d4c74bd7b623492b7dbdaafd8b7c72f329a8270ba4eca68f768a`; runner verifies target and companion checksums.
- NGRAM policy: C1/C2 only require NGRAM-on compatibility/capacity/output integrity; performance effectiveness is deferred to Phase 5.
- Generic runner: `scripts/run_c1_llama.py`.
- Next measured execution: TARGET only.
- No automatic retry and no automatic next-lane launch.
