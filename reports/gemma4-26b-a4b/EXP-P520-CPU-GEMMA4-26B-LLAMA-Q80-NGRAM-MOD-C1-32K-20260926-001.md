# EXP-P520-CPU-GEMMA4-26B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001

## 실험 식별 정보

- 실행 일시: 2026-09-26T16:14:08.000075+00:00
- 판정: **PASS**
- 모델: gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf
- 런타임: llama.cpp
- Runtime revision: p520-cpu-llama:b10775 (p520-cpu-llama@sha2)

## 서빙 설정

- Weight: UD-Q6_K_XL
- KV: Q8_0
- Speculative: ngram-mod
- ngram: ngram-mod-24-48-64
- Topology: cpu-standalone-4core
- Context per agent: 32768
- Concurrency: C1
- Prefix cache: cold-independent
- measured_repetitions: 1

## Capacity / Concurrency

- C1 128K: false
- Overlap source: llama.cpp server metrics/slots sampler

## 성능 결과

- TTFT: 4927281.9147660015
- Prefill tok/s: 6.442329669076854
- Mean request decode tok/s: 2.7246637292429017
- Aggregate decode tok/s: 2.7283856083225997
- End-to-end output tok/s: 0.13796497507883818
- Batch wall: 5189.722968389997
- Peak VRAM: GPU0 0 MiB / GPU1 0 MiB

## 증거 경로

- Raw artifact: results/raw/EXP-P520-CPU-GEMMA4-26B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001
- Evidence files: config.json, identity.json, workload.json, payloads.json, tokenization.json, requests.json, overlap-evidence.json, metrics.json, completion.json, gpu-peak.json, health-before.json, health-after.json, server-before.json, server-after.json
- Runtime files: runtime/planned-config.json, runtime/progress.json

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
