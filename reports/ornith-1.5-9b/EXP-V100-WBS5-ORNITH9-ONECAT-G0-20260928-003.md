# EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003

## 실험 식별 정보

- 실행 일시: 2026-09-29T07:53:17.813231+00:00
- 판정: **FAIL_OUTPUT** (raw C2 ACTIVE / mechanical PASS; G0 semantic FAIL)
- 모델: Ornith-1.5-9B
- 런타임: 1Cat-vLLM
- Runtime revision: 1.5.0 wheel sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b
- Harness verdict (raw): PASS_C2_ACTIVE
- Capacity verdict: not separately assessed
- Output-integrity verdict: FAIL_OUTPUT
- Final verdict (semantic audit): FAIL_OUTPUT

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

- C2 resident: true
- C2 active: true
- Queue only: false
- Overlap source: 1Cat-vLLM server metrics/slots sampler
- Submission skew: 0.008s (routing-settled admission stagger)

## 성능 결과

- TTFT: 308001.51221749955
- Prefill tok/s: 418.9099712968833
- Mean request decode tok/s: 10.24566382387495
- Aggregate decode tok/s: 16.379481900042748
- End-to-end output tok/s: 5.102025735540025
- Batch wall: 445.70531743100037
- Peak VRAM: GPU0 13,901 MiB / GPU1 13,901 MiB
- Peak VRAM sampling: nvidia-smi memory.used sampled every 0.5s; transient peaks between samples may be missed.

## 증거 경로

- Raw artifact: results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003
- Evidence files: config.json, identity.json, workload.json, payloads.json, tokenization.json, requests.json, overlap-evidence.json, metrics.json, completion.json, gpu-peak.json, health-before.json, health-after.json, server-before.json, server-after.json, acceptance-review.json
- Runtime files: runtime/plan.json, runtime/planned-config.json, runtime/server-0.log, runtime/measurement.log, runtime/cleanup.json, runtime/exit.json, runtime/progress.json, runtime/preflight.json

## 결론 및 Semantic Audit

- **Output Integrity**: Project A PASS; Project B FAIL against the pre-registered concurrency/v2 ground-truth oracle. Mechanical output PASS does not establish semantic correctness.
- **실패 원인 및 진단 요약**: Project B identifies _sequence/push instead of the seeded JobQueue.pop nonempty-check -> await -> heappop race. See semantic-audit.json for the recorded audit and request/oracle hashes.
- 상세 감사 기록: `results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003/acceptance-review.json`
- 이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
