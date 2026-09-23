# <EXPERIMENT_ID>

> 실험 보고서는 한국어로 작성한다. 실험 ID, 모델/런타임명, 명령어, 설정 키, metric 이름, 판정값은 원문 표기를 유지한다.
>
> 최종 보고서는 동일 raw evidence에서 `results/summary.csv`와 `reports/comparison.csv`의 정확히 1행으로 연결한다.

## 실험 식별 정보

- 실행 일시:
- 호스트:
- WBS 항목:
- 판정:
- 실행 단계:

## 모델

- 모델:
- 아티팩트/저장소:
- 아티팩트 hash/revision:
- 가중치 양자화:

## 런타임

- 런타임: llama.cpp | 1Cat-vLLM | 1Cat-vLLM+v100-skinny
- Version/commit/build:
- Container/image digest:
- v100-skinny revision/path (해당 시):
- 정확한 실행 명령어:
- 환경 변수/override:

## 서빙 설정

- GPU topology:
- 요청당 context budget:
- 동시성: C1 | C2
- llama.cpp slots / unified-KV 설정:
- vLLM max_num_seqs / TP 설정:
- KV cache:
- Speculative method/config:
- ngram 설정/지원 판정:
- Prefix-cache state:
- Batch/scheduler/CUDA Graph 설정:
- Chat template / tool parser / reasoning 설정:
- Sampling/output 목표:

## 최신 환경 증거

- GPU 정책 읽기 전용 검증:
- CPU/RAM 상태:
- 기존 process/port 충돌:
- 테스트 전 서버 상태:
- 테스트 후 서버 상태:

## 워크로드

- Workload/version/hash:
- Project A prompt hash/tokens:
- Project B prompt hash/tokens (C2):
- 요청 output reservation:
- 실제 output tokens:
- 정확성 검사:

## Capacity / Concurrency 판정

- C1 128K capacity:
- C2 두 context 동시 resident:
- C2 실제 active overlap:
- Queue-only 여부:
- Server-side overlap evidence:
- 최종 capacity/concurrency 판정:

## 성능 결과

- TTFT:
- ITL:
- Prefill tok/s:
- 요청별 decode tok/s:
- 평균 요청 decode tok/s:
- Aggregate decode tok/s:
- End-to-end output tok/s:
- Request/batch wall time:
- Speculative drafted/accepted evidence:

## 텔레메트리

- GPU0/GPU1 Peak VRAM:
- GPU0/GPU1 Peak power:
- GPU0/GPU1 Peak temperature:
- 부하 중 SM clock:
- Telemetry interval/gap:

## 오류 및 한계

- OOM/capacity/timeout/crash/output 오류:
- 누락된 증거:
- 비교 시 주의사항/한계:

## 증거 경로

- Raw artifact 디렉터리:
- Server log:
- Requests:
- Telemetry:
- Config/environment:

## 결론

이 실험이 확인한 사실과 확인하지 못한 사실을 구분하고, 다음 실험에 미치는 영향만 간결하게 기록한다.
