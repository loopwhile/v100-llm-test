# EXP-V100-Q38-1CAT-FP8E5M2-TARGET-RECOVERY-C1-128K-20260925-001

## 실험 식별 정보

- 실행 일시: 2026-09-25T07:02:29.121616+00:00
- 판정: **FAIL_STARTUP**
- 모델: Qwen3.8-27B
- 런타임: 1Cat-vLLM
- Runtime revision: 1.5.0 wheel sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b

## 서빙 설정

- Weight: NVFP4
- KV: fp8_e5m2
- Speculative: target-only
- ngram: N/A
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C1
- Prefix cache: cold-independent
- measured_repetitions: 1

## Capacity / Concurrency

- C1 128K: false

## 성능 결과

- TTFT: None
- Prefill tok/s: None
- Mean request decode tok/s: None
- Aggregate decode tok/s: None
- End-to-end output tok/s: None
- Batch wall: None
- Peak VRAM: GPU0 13,987 MiB / GPU1 13,987 MiB

## 증거 경로

- Raw artifact: results/raw/EXP-V100-Q38-1CAT-FP8E5M2-TARGET-RECOVERY-C1-128K-20260925-001
- config.json, workload.json, payloads.json, tokenization.json
- requests.json, overlap-evidence.json, metrics.json
- health-before.json, health-after.json, server snapshots

## 결론 및 Semantic Audit

- **128K Capacity**: FAIL_CAPACITY: Qwen3.8-27B QUASAR NVFP4 + 1Cat-vLLM 1.5.0 TP2 + FP8 E5M2 + GDN Triton prefill path failed during engine core initialization profile run. Available KV cache memory shrank to 1.5 GiB, which is insufficient for 131,072 max_model_len requiring 2.15 GiB (estimated max model length 87,808). Server exited prematurely before measured inference.
- **Output Integrity**: NOT_REACHED: Measured inference was never dispatched due to engine startup capacity failure.
- **실패 원인 및 진단 요약**: 과거 64K clean-output evidence에서 가져온 E5M2 KV + GDN Triton prefill path를 현재 128K context 설정에 결합한 결과, Triton prefill 커널 프로파일링 오버헤드로 인해 가용 KV 캐시 메모리가 1.5 GiB로 감소하여 128K 수용에 필요한 2.15 GiB를 확보하지 못하고 startup capacity에서 즉시 실패함 (estimated max context: 87,808). 반면 기존 E4M3 path는 2.8 GiB 가용 메모리로 128K capacity를 통과했으므로, E5M2/GDN Triton path는 현재 2x V100 16GB 환경에서 128K capacity-compatible하지 않음이 확인됨.
- 상세 감사 기록: `results/raw/EXP-V100-Q38-1CAT-FP8E5M2-TARGET-RECOVERY-C1-128K-20260925-001/acceptance-review.json`
- 이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
