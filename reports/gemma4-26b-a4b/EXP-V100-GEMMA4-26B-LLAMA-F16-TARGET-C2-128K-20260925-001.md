# EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001

## 실험 식별 정보

- 실행 일시: 2026-09-26T07:46:38.381859+00:00
- 판정: **PASS_C2_ACTIVE**
- 모델: Gemma4-26B-A4B-IT-QAT
- 런타임: llama.cpp
- Runtime revision: 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb

## 서빙 설정

- Weight: UD-Q4_K_XL
- KV: FP16
- Speculative: target-only
- ngram: off
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

- TTFT: 447015.3454544999
- Prefill tok/s: 359.05029032857624
- Mean request decode tok/s: 21.65621125645531
- Aggregate decode tok/s: 4.766136184995442
- End-to-end output tok/s: 2.9848984038082094
- Batch wall: 667.3593973779998
- Peak VRAM: GPU0 10,039 MiB / GPU1 10,537 MiB

## 증거 경로

- Raw artifact: results/raw/EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001
- config.json, workload.json, payloads.json, tokenization.json
- requests.json, overlap-evidence.json, metrics.json
- health-before.json, health-after.json, server snapshots

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
