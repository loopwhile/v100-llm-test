# WBS 5.4.1.5 — Qwen3.8-27B / 1Cat-vLLM track result review

Review date: 2026-09-29

## 1. Scope

이 review는 **추가 GPU inference 없이** 이미 publication된 WBS5 raw/report만 사용해 Qwen3.8-27B / 1Cat-vLLM frozen track을 닫는다. 새로운 candidate, retry, host toolchain 변경, CUDA toolkit 설치는 수행하지 않는다.

Authoritative WBS5 state:

| Candidate | Experiment | Verdict | Promotion-relevant state |
|---|---|---|---|
| R0 `R0-E4M3-128K-SEMANTIC-BASELINE` | `EXP-V100-WBS5-QWEN-ONECAT-R0-PERF-20260928-001` | `QUEUE_ONLY` | 두 요청 mechanical PASS, C2 active=false |
| R1 `R1-E4M3-128K-CUDAGRAPH-C1` | `EXP-V100-WBS5-QWEN-ONECAT-R1-PERF-20260928-001` | `FAIL_STARTUP` | Torch Inductor compile 중 CUDA OOM, measured request 없음 |
| R2 `R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL` | 미실행 | `BLOCKED_BY_HOST_TOOLCHAIN` | nvcc / 승인된 isolated CUDA development toolkit 부재 |
| R3 `R3-E5M2-128K-KV-ROUTE` | `EXP-V100-WBS5-QWEN-ONECAT-R3-PERF-20260928-001` | `QUEUE_ONLY` | 두 요청 mechanical PASS, C2 active=false |

## 2. Frozen identity / topology interpretation

- R0와 R3는 `max-num-seqs=1`을 유지한 동일 TP2 shared target-only serving lane이며, R3는 KV dtype `fp8_e4m3 -> fp8_e5m2`만 변경한다.
- 두 run 모두 independent A/B client 요청 2개를 완료했지만 server sampler는 peak processing 1 / waiting 1, `c2_active=false`, `queue_only=true`를 기록했다. 따라서 이 결과를 C2 ACTIVE throughput으로 재해석하지 않는다.
- R1은 eager 제거 + frozen capture size `[1]` graph 축만 바꿨지만 startup compile 단계에서 OOM으로 종료됐다. graph capture/replay 효과를 측정한 run이 아니다.
- R2는 frozen candidate이지만 current host toolchain gate를 통과하지 않아 measured evidence가 없다. 미실행을 candidate failure로 기록하지 않는다.

## 3. R0 vs R3 observed queue-only comparison

| Metric | R0 E4M3 | R3 E5M2 | R3 vs R0 |
|---|---:|---:|---:|
| TTFT mean | 1298.20 s | 470.11 s | -63.79% |
| Prefill | 121.95 tok/s | 457.97 tok/s | +275.55% |
| Mean request decode | 9.38 tok/s | 9.49 tok/s | +1.21% |
| Aggregate decode | 5.02 tok/s | 7.86 tok/s | +56.37% |
| End-to-end output | 3.43 tok/s | 6.71 tok/s | +95.70% |
| Batch wall | 2270.90 s | 1160.41 s | -48.90% |
| Total output tokens | 7,788 | 7,788 | identical |
| Peak VRAM / GPU | 15,567 MiB | 16,117 MiB | +550 MiB (+3.53%) |

R3는 동일 prompt/output-token count의 queue-only 관측에서 R0보다 훨씬 짧은 prefill/TTFT/wall을 보였다. 그러나 이 비교는 **C2 ACTIVE가 아니며**, WBS5 performance workload의 task-level semantic correctness도 별도 PASS로 확정되지 않았다. 또한 R3 peak는 16,384 MiB 카드에서 16,117 MiB로 매우 높은 사용량이다. 따라서 이 관측값만으로 R3를 final serving recipe로 승격하지 않는다.

## 4. Candidate decisions

- **R0:** queue-only reference baseline으로 보존. Mechanical output PASS와 128K serving 관측은 유지하지만 C2 recipe 자격은 없다.
- **R1:** `CLOSED — FAIL_STARTUP`. Compile OOM 이전에 measured request가 없으므로 graph 성능 주장은 금지한다.
- **R2:** `UNMEASURED — BLOCKED_BY_HOST_TOOLCHAIN`. 승인된 host/toolchain 변경 없이 실행하거나 validated로 표기하지 않는다.
- **R3:** `NOT PROMOTED — QUEUE_ONLY DIAGNOSTIC`. 현재 frozen track 안에서 가장 좋은 queue-only latency/prefill 관측은 R3이지만 C2 ACTIVE 및 task-level semantic qualification이 없으므로 final recipe 후보로 올리지 않는다.

## 5. Track closeout

현재 frozen WBS5 evidence만으로 `VALIDATED_RECIPE` 또는 WBS 5.5 final recipe 승격 조건을 충족하는 Qwen3.8 / 1Cat-vLLM candidate는 **없다**.

이 결론은 Qwen3.8 / 1Cat-vLLM의 모든 미래 구성을 영구 차단한다는 뜻이 아니다. 별도 user-authorized semantic revalidation, toolchain unblock 또는 새로운 phase가 생기면 fresh evidence로 다시 평가할 수 있다. 이번 5.4.1.5에서는 새 candidate나 추가 inference를 만들지 않는다.

WBS 5.4.1.5 status: **DONE — REVIEW_COMPLETE / NO ELIGIBLE RECIPE**.
