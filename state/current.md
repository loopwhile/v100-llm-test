# Current execution

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- 2.1.2 artifact: Q6_K, KV: FP16, topology: tp2-shared, context: C1 128K.
- 2.1.2 results: TARGET / NGRAM / MTP / MTP_NGRAM all `PASS_C1_128K`.
- MTP evidence: 645 drafts, 291 accepted, 45.116% acceptance; MTP_NGRAM counters matched MTP-only.
- NGRAM-only produced no draft/accepted-token evidence on this capacity workload.
- Next planned llama.cpp C1 item: WBS 2.1.3 Ornith 1.5 35B-A3B (Q4_K_M, Q8_0, TARGET/NGRAM/MTP/MTP_NGRAM).
- Generic runner: `scripts/run_c1_llama.py`.
- No automatic retry and no automatic next-lane launch.
