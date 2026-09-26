# EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-1GPU2-C2-128K-20260926-001

## 실험 식별 정보

- 실행 일시: 2026-09-26T10:11:45.851157+00:00
- 판정: **PASS_C2_ACTIVE**
- 모델: Ornith-1.5-9B
- 런타임: llama.cpp
- Runtime revision: 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
- Gateway runtime: LiteLLM
- Gateway revision: 1.101.0 / 18243cd7af4c3325165ba68b21379e2719e051c7
- Gateway image: ghcr.io/berriai/litellm:v1.101.0
- Gateway endpoint: http://127.0.0.1:18079
- Gateway routing: least-busy
- Gateway backend max parallel: 1

## 서빙 설정

- Weight: Q6_K
- KV: FP16
- Speculative: mtp+ngram
- ngram: ngram-simple
- Topology: 1gpu-x2-independent
- Context per agent: 131072
- Concurrency: C2
- Prefix cache: cold-independent
- measured_repetitions: 1

## Capacity / Concurrency

- C2 resident: true
- C2 active: true
- Queue only: false
- Overlap source: LiteLLM single gateway endpoint + backend runtime probes + deployment response headers

## 성능 결과

- TTFT: 208742.9912735006
- Prefill tok/s: 618.2570934896737
- Mean request decode tok/s: 49.95895585746008
- Aggregate decode tok/s: 79.34695006146242
- End-to-end output tok/s: 9.838754857361133
- Batch wall: 234.88744597299956
- Peak VRAM: GPU0 11,905 MiB / GPU1 11,905 MiB

## 증거 경로

- Raw artifact: results/raw/EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-1GPU2-C2-128K-20260926-001
- config.json, workload.json, payloads.json, tokenization.json
- requests.json, overlap-evidence.json, metrics.json
- health-before.json, health-after.json, server snapshots

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
