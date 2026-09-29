# WBS 5.4.2.6 — Ornith 1.5 9B / 1Cat-vLLM track result review

Review date: 2026-09-29

## 1. Scope and admission state

이 review는 **추가 GPU inference 없이** G0 및 WBS5 performance diagnostic raw/report만 사용한다.

G0 `EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003`은 raw harness 관점에서 `PASS_C2_ACTIVE`였지만 pre-registered semantic oracle 기준 Project B가 seeded `JobQueue.pop` check -> await -> heappop race 대신 `_sequence` 문제를 지목해 semantic audit가 FAIL이다. 따라서 G0 PASS receipt는 존재하지 않으며 R0~R3는 모두 `performance_diagnostic=true`로만 실행되었다.

이 admission failure 하나만으로도 R0~R3를 semantic-qualified final recipe로 승격할 수 없다.

## 2. Diagnostic comparison

| Candidate | Final verdict | TTFT | Prefill | Mean req decode | Aggregate decode | E2E output | Wall | Peak VRAM |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| R0 baseline / MTP1 | `FAIL_OUTPUT` | 299.28 s | 424.28 | 10.01 | 14.85 | 5.60 | 478.89 s | 13,899 / 13,899 MiB |
| R1 MBT8192 | `FAIL_OUTPUT` | 299.38 s | 424.13 | 10.01 | 14.85 | 5.60 | 478.98 s | 13,995 / 13,995 MiB |
| R2 target graph | `FAIL_OUTPUT` | 302.53 s | 419.71 | 11.74 | 19.53 | 5.29 | 413.14 s | 14,019 / 14,019 MiB |
| R3 MTP2 | `FAIL_OUTPUT` | 302.16 s | 420.24 | 11.27 | 17.32 | 5.99 | 459.76 s | 13,883 / 13,885 MiB |

모든 run은 C2 active / queue=false였지만 Project B output이 실패했다. 총 output tokens도 R0/R1 2,684, R2 2,184, R3 2,754로 서로 달라 aggregate/wall 수치를 pure decode 또는 recipe superiority로 해석하지 않는다.

## 3. Candidate interpretation

- **R1 MBT8192:** R0 대비 TTFT +0.03%, prefill -0.03%, mean decode +0.01%, aggregate 사실상 동일, wall +0.02%다. Peak VRAM만 GPU당 +96 MiB 증가했다. `CLOSED — NO MEASURABLE BENEFIT`.
- **R2 target graph:** mean request decode +17.24%, aggregate +31.47%, wall -13.73%가 관측됐지만 E2E output은 -5.68%이고 output token 수가 더 짧다. `graph-evidence.json`은 capture/replay `UNKNOWN`이다. 따라서 관측 차이를 graph 효과로 귀속하지 않으며, Project B 실패 때문에 recipe 승격도 금지한다.
- **R3 MTP2:** MTP acceptance는 1,462 / 2,580 = 56.67%다. R0 MTP1은 1,131 / 1,552 = 72.87%였다. R3의 mean decode +12.53%, aggregate +16.60%, E2E +6.88%, wall -3.99%는 diagnostic observation으로만 남긴다. depth 2 superiority를 선언하지 않는다.
- **R0 baseline:** performance diagnostic reference로만 유지한다. G0 semantic qualification이 없으므로 final recipe 후보가 아니다.

## 4. Track closeout

R0~R3 어느 것도 WBS 5.5의 output-integrity/admission 조건을 충족하지 않는다. 따라서 이 track에서는 **final recipe 후보를 남기지 않는다**.

R2/R3의 throughput 신호를 이유로 G0 FAIL을 우회하거나 새로운 graph/MTP depth tuning candidate를 추가하지 않는다. 향후 G0를 다시 수행하려면 별도 user-authorized fresh semantic requalification이 필요하며, 이번 review는 이를 자동 스케줄하지 않는다.

WBS 5.4.2.6 status: **DONE — REVIEW_COMPLETE / NO ELIGIBLE RECIPE**.
