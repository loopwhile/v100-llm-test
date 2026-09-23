# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- 2.1.3 results: TARGET / NGRAM / MTP / MTP_NGRAM all `PASS_C1_128K`.
- 2.1.3 native MTP n=1 evidence: 401/505 accepted (79.406%); MTP_NGRAM: 364/512 accepted (71.094%).
- NGRAM policy: C1/C2 only require NGRAM-on compatibility/capacity/output integrity; performance effectiveness is deferred to Phase 5.
- Next planned llama.cpp C1 item: WBS 2.1.4 Gemma4 26B-A4B (UD-Q4_K_XL, FP16, TARGET/NGRAM/MTP/MTP_NGRAM).
- Before WBS 2.1.4 execution, verify whether Gemma4 MTP lanes require the pinned separate mtp_companion GGUF rather than the embedded-native-MTP path used by Ornith 35B.
- Generic runner: `scripts/run_c1_llama.py`.
- No automatic retry and no automatic next-lane launch.
