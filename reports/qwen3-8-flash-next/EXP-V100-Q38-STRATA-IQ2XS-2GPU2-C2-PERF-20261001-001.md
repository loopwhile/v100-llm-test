# EXP-V100-Q38-STRATA-IQ2XS-2GPU2-C2-PERF-20261001-001

## 실험 식별 정보

- 판정: **PASS_C2_ACTIVE** (128K × 2 동시 실행 및 기계적 출력 검사 통과)
- 실행 종료 기준: 2026-10-01T10:52:32.014449+00:00 (`after.json`의 A metrics snapshot 시각; 별도 completion timestamp는 없음)
- 모델: Qwen3.8-Flash-Next (raw endpoint 모델명 `qwen3.8-flash-next-iq2_xs-mmap-a` / `-b`)
- 런타임: Strata, engine 0.1.31
- 하드웨어: Tesla V100-SXM2-16GB × 2; 독립 인스턴스 A/B에 GPU 1장씩

## 서빙 설정과 워크로드

- Weight: IQ2_XS, native pack + mmap experts (engine log 기준)
- KV: int8; GPU resident 32,768 / context 131,072 cells per QSA layer (engine metrics/log 기준)
- Speculative: MTP/verification 활성 (`spec=6`, `mtp_max=4`, engine metrics 기준)
- Topology: `1gpu-x2-independent`; context per agent 131,072; concurrency C2
- Workload: `V100-PERFORMANCE-C2-128K-v1`, manifest SHA256 `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`
- Warmup count: 0; measured repetitions: 1; request cache hits: A/B 모두 0
- 제출 간격: 0.003766 s
- A/B prompt: 126,967 / 126,968 tokens; output reserve: 각각 4,096 tokens; minimum output: 각각 1,024 tokens

## Capacity / Concurrency

- C2 resident: **true** — 전후 health에서 두 인스턴스가 모두 loaded/ok, max context 131,072
- C2 active: **true** — `status-samples.json`에서 두 인스턴스 동시 busy 1,185 samples, 동시 busy + answering 299 samples; `summary.json`의 decode overlap 60.771 s
- Queue only: **false** — 두 요청이 실제로 동시 생성했으며 샘플의 queued 값은 모두 0
- A/B 모두 prompt token count 일치, output ≥1,024 tokens, 비어 있지 않은 응답, `finish_reason=stop`; 사후 health 정상

## 성능 결과

| 지표 | A | B | 배치 / 평균 |
|---|---:|---:|---:|
| Prompt tokens | 126,967 | 126,968 | 253,935 |
| Output tokens | 1,402 | 1,446 | 2,848 |
| TTFT | 181.762 s | 178.345 s | 180,053.269 ms 평균 |
| Prefill | 700.5 tok/s | 714.0 tok/s | 707.25 tok/s 평균 |
| Request decode | 21.2 tok/s | 22.5 tok/s | 21.85 tok/s 평균 |
| Request wall | 247.918 s | 242.537 s | 247.933 s batch wall |

- Aggregate decode: **40.937 tok/s**. 두 출력의 합 2,848 tokens를 B의 추정 첫 토큰부터 A의 종료까지 69.570 s로 나눈 값이다. 상대 시작 시각은 `submission_skew_s`를 사용했으며, 별도의 요청별 절대 first-token/end timestamp는 raw에 없다.
- End-to-end output: **11.487 tok/s** = 2,848 output tokens / 247.933 s batch wall.
- Peak VRAM: **측정값 없음**. `before.json`/`after.json`의 GPU memory.used는 순간 스냅샷이며 측정 구간의 최대값이 아니다. `after.json` 스냅샷은 A 16,008.5 MiB, B 15,986.5 MiB.
- 두 수치는 서로 다른 구간을 분모로 사용한다. 이 결과는 단일 measured batch이므로 반복 간 변동은 평가하지 않았다.

## 판정 범위와 증거

- `summary.json`의 `pass_mechanical`, `active_overlap`, `post_health`가 모두 true이며, `after.json`은 각 인스턴스에서 요청 1회 완료를 기록한다.
- raw에는 최종 응답 본문 전체와 semantic oracle 판정이 없다. `status-samples.json`의 일부 `tail`만으로 코드 작업 품질을 인증할 수 없다. 따라서 PASS는 서빙 용량·동시성·기계적 출력 조건에 한정된다.
- 근거: [`results/raw/EXP-V100-Q38-STRATA-IQ2XS-2GPU2-C2-PERF-20261001-001/`](../../results/raw/EXP-V100-Q38-STRATA-IQ2XS-2GPU2-C2-PERF-20261001-001/)의 `summary.json`, `workload.json`, `before.json`, `after.json`, `status-samples.json`, `agent-a-engine.log`, `agent-b-engine.log`, `payload-a.json`, `payload-b.json`.
- 이 보고서는 해당 모델·런타임·토폴로지·워크로드의 raw에 한정한다.
