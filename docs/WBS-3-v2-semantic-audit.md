# WBS 3 C2 v2 Semantic Audit

Audit basis: `workloads/concurrency/v2-ground-truth.json`.

This audit does not rerun inference and does not mutate existing raw measurement files. It adds a derived `acceptance-review.json` to each measured V2 experiment and makes normalized reports/CSV/WBS use the publication verdict.

## Verdict model

- Runtime concurrency: `PASS_C2_ACTIVE`, `QUEUE_ONLY`, etc. This is preserved from sampled server evidence.
- Mechanical output: minimum length / termination / repetition checks from the harness.
- Semantic: pre-registered V2 oracle for Project A and Project B.
- Publication: runtime verdict is publishable only when mechanical and semantic both pass; otherwise `FAIL_OUTPUT`.

## Audited results

| WBS | Model/runtime | Lane | Runtime concurrency | Mechanical | Semantic | Publication |
| --- | --- | --- | --- | --- | --- | --- |
| 3.2.1 | Qwen3.8 1Cat | TARGET B200 E4M3 | QUEUE_ONLY | FAIL_OUTPUT | FAIL_OUTPUT | FAIL_OUTPUT |
| 3.2.2 | Ornith 9B 1Cat | MTP1 | PASS_C2_ACTIVE | PASS | FAIL_OUTPUT | FAIL_OUTPUT |
| 3.2.3 | Ornith 35B 1Cat | TARGET E5M2 | PASS_C2_ACTIVE | PASS | FAIL_OUTPUT | FAIL_OUTPUT |
| 3.1.1 | Qwen3.8 llama | TARGET | PASS_C2_ACTIVE | PASS | PASS | PASS_C2_ACTIVE |
| 3.1.1 | Qwen3.8 llama | NGRAM | PASS_C2_ACTIVE | PASS | PASS | PASS_C2_ACTIVE |
| 3.1.2 | Ornith 9B llama | TARGET | PASS_C2_ACTIVE | PASS | FAIL_OUTPUT | FAIL_OUTPUT |
| 3.1.2 | Ornith 9B llama | NGRAM | PASS_C2_ACTIVE | PASS | FAIL_OUTPUT | FAIL_OUTPUT |
| 3.1.2 | Ornith 9B llama | MTP | PASS_C2_ACTIVE | PASS | FAIL_OUTPUT | FAIL_OUTPUT |
| 3.1.2 | Ornith 9B llama | MTP_NGRAM | PASS_C2_ACTIVE | PASS | FAIL_OUTPUT | FAIL_OUTPUT |
| 3.1.3 | Ornith 35B llama | TARGET | PASS_C2_ACTIVE | PASS | PASS | PASS_C2_ACTIVE |
| 3.1.3 | Ornith 35B llama | NGRAM | PASS_C2_ACTIVE | PASS | PASS | PASS_C2_ACTIVE |
| 3.1.3 | Ornith 35B llama | MTP | PASS_C2_ACTIVE | PASS | FAIL_OUTPUT | FAIL_OUTPUT |
| 3.1.3 | Ornith 35B llama | MTP_NGRAM | PASS_C2_ACTIVE | PASS | FAIL_OUTPUT | FAIL_OUTPUT |

Summary:
- 13 measured V2 experiments audited.
- Runtime: 12 `PASS_C2_ACTIVE`, 1 `QUEUE_ONLY`.
- Mechanical: 12 PASS, 1 FAIL_OUTPUT.
- Semantic: 4 PASS, 9 FAIL_OUTPUT.
- Publication: 4 `PASS_C2_ACTIVE`, 9 `FAIL_OUTPUT`.

## Main semantic failure patterns

- Qwen 1Cat: Project A misses the seeded `Transaction.commit` in-loop clear; Project B underfills and never performs the requested bug analysis.
- Ornith 9B 1Cat: Project B substitutes an impossible `_sequence` asyncio race even though `push()` has no await.
- Ornith 35B 1Cat: Project B locates the correct await window but proposes an empty-queue trace/reproduction; an empty queue returns before the await and cannot reproduce the seeded defect.
- Ornith 9B llama.cpp lanes: Project B repeatedly replaces the required empty-heap `IndexError` with reversed ordering, double-dispatch, or same-item-twice mechanisms.
- Ornith 35B llama.cpp MTP/MTP_NGRAM: runtime C2 is valid, but the Project B regression/mechanism does not satisfy the exact oracle. TARGET/NGRAM do satisfy it.
- Qwen llama.cpp TARGET/NGRAM and Ornith 35B llama.cpp TARGET/NGRAM satisfy both Project A and Project B oracle requirements.

Full per-experiment reasons are stored in each `acceptance-review.json`.
