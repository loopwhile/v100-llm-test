# EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C1-128K-20260923-001

## 실험 식별 정보

- 실행 완료: 2026-09-23T14:57:25.631525+00:00
- 판정: **PASS_C1_128K**
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
- Concurrency: C1
- `--spec-draft-n-max 3`

## Capacity / 성능

- prompt: **129,023** tokens
- output reserve: **2,048** tokens
- budget: **131,071 / 131,072**
- actual output: **507** tokens
- finish_reason: `stop`
- TTFT: **177973.273 ms**
- Prefill: **725.998 tok/s**
- Mean decode: **52.164 tok/s**
- Aggregate decode: **52.245 tok/s**
- Batch wall: **187.687 s**
- Peak VRAM: GPU0 **5,671 MiB** / GPU1 **7,113 MiB**

## Speculative evidence

- draft generated: **645**
- accepted: **291**
- acceptance: **45.116%**
- mean draft length: **2.35**
- MTP-only와 counters/output가 동일하며 이번 요청에서 NGRAM 추가 기여를 보여주는 evidence는 없다.

## Acceptance 검토

- 요청 후 health 정상, truncated=0, cleanup 정상, exit code 0.
- MTP-only와 동일한 의미 오류(`dict(self.pages)`를 live reference로 오인)가 있다.
- 모델 품질 caveat로 기록하며 C1 serving/output-integrity PASS는 유지한다.

## 증거

- Raw: `results/raw/EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C1-128K-20260923-001`
- 추가 검토: `acceptance-review.json`
