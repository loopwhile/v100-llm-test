# EXP-V100-Q38-1CAT-FP8E4M3-TARGET-DIAG-REALISTIC-128K-20260925-003

## 실험 식별 정보

- 실행 일시: 2026-09-24T17:03:35.020348+00:00
- 판정: **FAIL_OUTPUT** (128K Capacity PASS, Output-Integrity FAIL)
- 모델: Qwen3.8-27B
- 런타임: 1Cat-vLLM
- Runtime revision: 1.5.0 wheel sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b

## 서빙 설정

- Weight: NVFP4
- KV: fp8_e4m3
- Speculative: target-only
- ngram: N/A
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C1
- Prefix cache: cold-independent
- measured_repetitions: 1

## Capacity / Concurrency

- C1 128K: true
- Overlap source: 1Cat-vLLM server metrics/slots sampler

## 성능 결과

- TTFT: 739288.4112739994
- Prefill tok/s: None
- Mean request decode tok/s: 9.756838144358474
- Aggregate decode tok/s: 9.756838144358474
- End-to-end output tok/s: 2.1574916832080917
- Batch wall: 949.2504726390034
- Peak VRAM: GPU0 15,287 MiB / GPU1 15,287 MiB

## 증거 경로

- Raw artifact: results/raw/EXP-V100-Q38-1CAT-FP8E4M3-TARGET-DIAG-REALISTIC-128K-20260925-003
- config.json, workload.json, payloads.json, tokenization.json
- requests.json, overlap-evidence.json, metrics.json
- health-before.json, health-after.json, server snapshots

## 결론 및 Semantic Audit

- **128K Capacity**: PASS (128,832 tokens realistic prefill + 2,048 tokens decode 성공, Peak VRAM GPU0 15,287 MiB / GPU1 15,287 MiB로 OOM 없음, post-health 정상).
- **Output Integrity**: FAIL (116개 고유 파일로 구성된 realistic diversified snapshot임에도, 초반 26개 파일 목록 열거 후 18~26번 9개 파일 블록이 5회 연속 동일하게 반복되는 Repetition Collapse에 진입하여 2,048 tokens에서 finish_reason=length로 강제 종료).
- **실패 원인 및 진단 요약**: 합성 반복 패턴(1,333회 반복)을 배제하고 116개 고유 실제 코드/문서 파일로 구성된 현실적인 128K 워크로드에서도 동일한 주기적 반복 붕괴(periodic repetition collapse)가 재현됨. 따라서 기존 실패는 단순 합성 반복 프롬프트 특화 문제가 아니며, Qwen3.8-27B + 1Cat-vLLM 1.5.0 + 128K context + FP8 E4M3 KV + Flash-V100/XQA 경로의 일반적인 런타임/수치 무결성 한계 가설이 강력하게 강화됨.
- 상세 감사 기록: `results/raw/EXP-V100-Q38-1CAT-FP8E4M3-TARGET-DIAG-REALISTIC-128K-20260925-003/acceptance-review.json`
- 이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
