# EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-001

## 실험 식별 정보

- 실행 일시: 2026-09-29T07:16:51.738536+00:00
- 판정: **INCONCLUSIVE**
- 모델: Ornith-1.5-9B
- 런타임: 1Cat-vLLM
- Runtime revision: 1.5.0 wheel sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b

## 서빙 설정

- Weight: NVFP4
- KV: FP16
- Speculative: MTP
- ngram: N/A
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C2
- Prefix cache: cold-independent
- measured_repetitions: 1

## Capacity / Concurrency

- C2 resident: false
- C2 active: false
- Queue only: false

## 성능 결과

- TTFT: None
- Prefill tok/s: None
- Mean request decode tok/s: None
- Aggregate decode tok/s: None
- End-to-end output tok/s: None
- Batch wall: None
- Peak VRAM: None
- Peak VRAM sampling: nvidia-smi memory.used sampled every 0.5s; transient peaks between samples may be missed.

## 증거 경로

- Raw artifact: results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-001
- Evidence files: config.json, identity.json, metrics.json, completion.json
- Runtime files: runtime/plan.json, runtime/planned-config.json, runtime/cleanup.json, runtime/exit.json, runtime/progress.json, runtime/preflight.json

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
