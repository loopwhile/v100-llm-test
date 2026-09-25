# EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-002

## 실험 식별 정보

- 실행 일시: 2026-09-25T09:08:27.322160+00:00
- 판정: **FAIL_CRASH**
- 모델: Gemma4-26B-A4B-IT-QAT
- 런타임: 1Cat-vLLM
- Runtime revision: 1.5.0 wheel sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b

## 서빙 설정

- Weight: AWQ INT4 (compressed-tensors)
- KV: FP16
- Speculative: target-only
- ngram: N/A
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C1
- Prefix cache: cold-independent
- measured_repetitions: 1

## Capacity / Concurrency

- C1 128K: false
- Overlap source: 1Cat-vLLM server metrics/slots sampler

## 성능 결과

- TTFT: None
- Prefill tok/s: None
- Mean request decode tok/s: None
- Aggregate decode tok/s: None
- End-to-end output tok/s: 0.0
- Batch wall: 7.92762732600022
- Peak VRAM: GPU0 15,243 MiB / GPU1 15,243 MiB

## 증거 경로

- Raw artifact: results/raw/EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-002
- config.json, workload.json, payloads.json, tokenization.json
- requests.json, overlap-evidence.json, metrics.json
- health-before.json, health-after.json, server snapshots

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
