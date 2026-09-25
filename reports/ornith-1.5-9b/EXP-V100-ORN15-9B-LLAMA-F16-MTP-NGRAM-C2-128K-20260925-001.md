# EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001

## 실험 식별 정보

- 실행 일시: 2026-09-25T15:36:04.764410+00:00
- 최종 publication 판정: **FAIL_OUTPUT**
- Runtime concurrency 판정: **PASS_C2_ACTIVE**
- Mechanical output 판정: **PASS**
- V2 semantic oracle 판정: **FAIL_OUTPUT**
- 모델: Ornith-1.5-9B
- 런타임: llama.cpp
- Runtime revision: 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb

## 서빙 설정

- Weight: Q6_K
- KV: FP16
- Speculative: mtp+ngram
- ngram: ngram-simple
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C2

## Capacity / Concurrency

- C2 resident: true
- C2 active: true
- Queue only: false
- Runtime concurrency classification은 semantic/output 판정과 독립적으로 보존한다.

## 성능 결과

- TTFT: 324.95s
- Prefill tok/s: 495.7412001688273
- Mean request decode tok/s: 21.401737265250897
- Aggregate decode tok/s: 6.447545902121714
- End-to-end output tok/s: 4.107191343047599
- Batch wall: 498.39411632599877s
- Peak VRAM: GPU0 7965.0 MiB / GPU1 10071.0 MiB

## V2 semantic acceptance review

- Project A: **PASS** (879 output tokens)
  - Correctly identifies the Transaction.commit in-loop clear, lost writes, regression, and minimal fix.
- Project B: **FAIL_OUTPUT** (1168 output tokens)
  - Locates the check-await-pop window but claims both workers pop the same heap entry and execute the job twice. The real seeded failure is first pop succeeds, second heappop sees an empty heap and raises IndexError.

Semantic oracle: `workloads/concurrency/v2-ground-truth.json`.

Runtime C2 active is valid, but Project B's central failure mechanism is wrong.

## 증거 경로

- Raw measurement artifact: `results/raw/EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001`
- Derived semantic review: `results/raw/EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001/acceptance-review.json`
- Existing config/workload/payload/tokenization/request/overlap/metrics/health evidence is not rewritten by this audit.

## 결론

Runtime C2 evidence와 model-output correctness를 분리한다. 최종 publication verdict는 mechanical output과 pre-registered V2 semantic oracle을 모두 만족해야 runtime concurrency verdict를 그대로 유지한다. 하나라도 실패하면 publication verdict는 `FAIL_OUTPUT`이며, runtime `PASS_C2_ACTIVE` evidence 자체는 유효한 측정으로 보존한다.
