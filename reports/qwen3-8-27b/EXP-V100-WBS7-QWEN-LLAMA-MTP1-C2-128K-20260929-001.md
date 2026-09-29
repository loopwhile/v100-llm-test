# EXP-V100-WBS7-QWEN-LLAMA-MTP1-C2-128K-20260929-001

## 실험 식별 정보

- 실행 일시: 2026-09-29T12:53:36.281295+00:00
- 판정: **FAIL_CRASH**
- 모델: Qwen3.8-27B
- 런타임: llama.cpp
- Runtime revision: 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb

## 서빙 설정

- Weight: UD-Q4_K_M
- KV: Q8_0
- Speculative: native-mtp
- ngram: off
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C2
- Prefix cache: cold-independent
- measured_repetitions: 1

## Capacity / Concurrency

- C2 resident: 측정 불가 (GPU1 OOM)
- C2 active: 측정 불가 (GPU1 OOM)
- Queue only: false
- Overlap source: llama.cpp server metrics/slots sampler
- Submission skew: 0.005s (routing-settled admission stagger)

## 성능 결과

- TTFT: None
- Prefill tok/s: None
- Mean request decode tok/s: None
- Aggregate decode tok/s: None
- End-to-end output tok/s: 0.0
- Batch wall: 0.8345401540000239
- Peak VRAM: GPU0 13,593 MiB / GPU1 16,123 MiB
- Peak VRAM sampling: nvidia-smi memory.used sampled every 0.5s; transient peaks between samples may be missed.


## Speculative evidence

- Draft tokens: None
- Accepted tokens: None
- Acceptance ratio: None
- Verification steps: None
- Counters: backend-level /metrics deltas across the measured request window.
## 증거 경로

- Raw artifact: results/raw/EXP-V100-WBS7-QWEN-LLAMA-MTP1-C2-128K-20260929-001
- Evidence files: config.json, identity.json, workload.json, payloads.json, tokenization.json, requests.json, overlap-evidence.json, metrics.json, completion.json, gpu-peak.json, health-before.json, health-after.json, server-before.json, server-after.json, speculative-evidence.json
- Runtime files: runtime/planned-config.json, runtime/server-0.log, runtime/exit.json, runtime/progress.json

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
