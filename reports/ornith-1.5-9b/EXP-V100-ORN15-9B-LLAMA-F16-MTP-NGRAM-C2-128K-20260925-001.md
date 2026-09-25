# EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001

## 실험 식별 정보

- 실행 일시: 2026-09-25T15:36:04.764410+00:00
- 판정: **PASS_C2_ACTIVE**
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
- Prefix cache: cold-independent
- measured_repetitions: 1

## Capacity / Concurrency

- C2 resident: true
- C2 active: true
- Queue only: false
- Overlap source: llama.cpp server metrics/slots sampler

## 성능 결과

- TTFT: 324949.701137999
- Prefill tok/s: 495.7412001688273
- Mean request decode tok/s: 21.401737265250897
- Aggregate decode tok/s: 6.447545902121714
- End-to-end output tok/s: 4.107191343047599
- Batch wall: 498.39411632599877
- Peak VRAM: GPU0 7,965 MiB / GPU1 10,071 MiB

## 증거 경로

- Raw artifact: results/raw/EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001
- config.json, workload.json, payloads.json, tokenization.json
- requests.json, overlap-evidence.json, metrics.json
- health-before.json, health-after.json, server snapshots

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
