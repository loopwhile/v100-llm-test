# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: IN_PROGRESS.
- 2.1.3 artifact: Q4_K_M, KV: Q8_0, topology: tp2-shared, context: C1 128K.
- 2.1.3 base GGUF SHA256: `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`.
- Required lanes: TARGET, NGRAM, MTP, MTP_NGRAM.
- Native MTP uses the embedded 1-layer NextN predictor in the target GGUF with `--spec-draft-n-max 1`; the separately recorded mtp_companion artifact is not injected as --model-draft for this lane.
- NGRAM policy: C1/C2 only require NGRAM-on compatibility/capacity/output integrity; draft activity or speedup is not an acceptance gate. Performance effectiveness is deferred to Phase 5.
- Generic runner: `scripts/run_c1_llama.py`.
- Next measured execution: TARGET only.
- No automatic retry and no automatic next-lane launch.
