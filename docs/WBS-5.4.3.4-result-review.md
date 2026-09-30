# WBS 5.4.3.4 — Ornith 1.5 35B-A3B / 1Cat-vLLM track result review

Review date: 2026-09-29

> 이 문서의 1~6절은 2026-09-29 원래 review의 판정 이력이다. 2026-09-30 사용자 요청으로 수행한 동일 R1 설정 재측정과 현재 해석은 **7절**에 기록한다.

## 1. Scope

이 review는 **추가 GPU inference 없이** publication된 R0/R1/R2 WBS5 raw/report와 frozen one-variable delta만 비교한다.

| Candidate | Frozen delta from R0 | Verdict |
|---|---|---|
| R0 `R0-BASELINE-EAGER-MBT4096` | baseline | `PASS_C2_ACTIVE` |
| R1 `R1-GRAPH-AUTO-MBT4096` | `--enforce-eager` 제거만 | `FAIL_OUTPUT` |
| R2 `R2-EAGER-MBT8192` | MBT 4096 -> 8192만 | `PASS_C2_ACTIVE` |

세 run 모두 C2 resident/active=true, queue_only=false, post-health healthy다. R0/R2는 두 요청 mechanical output PASS이고 R1은 Project A PASS / Project B FAIL이다.

## 2. Measured comparison

| Metric | R0 eager MBT4096 | R1 graph-auto | R2 eager MBT8192 |
|---|---:|---:|---:|
| TTFT mean | 109.62 s | 109.22 s | 111.34 s |
| Prefill | 1456.96 tok/s | 1459.67 | 1142.84 |
| Mean request decode | 8.01 tok/s | 51.40* | 9.65 |
| Aggregate decode | 11.48 tok/s | 23.34* | 17.95 |
| End-to-end output | 9.04 tok/s | 16.51* | 11.56 |
| Batch wall | 282.74 s | 205.02 s* | 298.73 s |
| Output tokens | 2,557 | 3,384* | 3,453 |
| Peak VRAM | 14,765 / 14,765 MiB | 14,921 / 14,921 | 14,753 / 14,753 |

`*` R1은 Project B `FAIL_OUTPUT`이라 mean request decode는 성공한 Project A만 반영하고 aggregate/wall에는 실패한 B가 포함된다. 따라서 R1 수치를 정상 candidate와 직접 비교하거나 graph speedup으로 사용하지 않는다. `graph-evidence.json`도 capture/replay `UNKNOWN`이다.

## 3. R1 graph-auto decision

R1은 eager 제거만 한 frozen graph candidate였지만 output integrity를 통과하지 못했고 실제 graph capture/replay도 증명되지 않았다. 숫자상 높은 decode/aggregate 값은 실패한 output trajectory와 섞여 있어 recipe evidence가 아니다.

Decision: **CLOSED — FAIL_OUTPUT / GRAPH EFFECT UNKNOWN**.

## 4. R2 MBT8192 decision

R2는 R0 대비 MBT만 4096 -> 8192로 변경했다.

R0-relative observations:

- TTFT: +1.57% (악화)
- Prefill: -21.56% (악화)
- Mean request decode: +20.34%
- Aggregate decode: +56.30%
- End-to-end output: +27.81%
- Batch wall: +5.66% (악화)
- Peak VRAM: -12 MiB/GPU (사실상 동일)
- Total output tokens: 2,557 -> 3,453 (+35.04%)

MBT8192의 robust한 long-context prefill/latency 이득은 관측되지 않았다. 오히려 prefill은 크게 감소하고 TTFT와 batch wall이 늘었다. Decode/aggregate/E2E 값은 좋아졌지만 output trajectory가 35% 더 길고 R0의 request-B decode가 낮았던 scheduling 비대칭도 포함하므로 이를 MBT8192의 pure decode speedup으로 승격하지 않는다.

Decision: **CLOSED — NO QUALIFYING OVERALL BENEFIT**. MBT grid를 추가하지 않는다.

## 5. R0 retention

R0는 frozen baseline 그대로 C2 active, queue=false, 두 요청 mechanical output PASS, post-health healthy를 만족했다. R1은 invalid output, R2는 intended prefill/latency 효과가 없었으므로 현재 track에서 WBS 5.5 publication 대상으로 남길 configuration은 R0다.

Decision: **R0 `R0-BASELINE-EAGER-MBT4096` RETAINED AS FINAL RECIPE CANDIDATE**.

이 단계에서는 WBS5 performance workload의 mechanical output PASS를 별도 semantic superiority로 확대 해석하지 않는다. `VALIDATED_RECIPE` 최종 표기와 exact recipe record는 5.5 publication contract에서 수행한다.

## 6. Track closeout

- R0: retain for WBS 5.5 final recipe publication.
- R1: close — output failure / graph effect unknown.
- R2: close — MBT8192 did not improve the intended prefill/latency side and overall wall worsened.
- 새 graph/MBT candidate 없음.
- 추가 GPU inference 없음.

WBS 5.4.3.4 status: **DONE — R0 RETAINED**.

## 7. 2026-09-30 R1 재측정 addendum

사용자 요청으로 R1 `R1-GRAPH-AUTO-MBT4096`을 새 experiment ID `EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001`에서 측정 1회 수행했다. 원래 frozen plan 28개에 포함되지 않은 독립 후속 실행이며, runner의 `screening-1` 라벨을 새 날짜의 ID에서 재사용했다. [후속 측정 report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001.md)와 [raw evidence](../results/raw/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001/wbs5-evidence.json)를 보존한다.

두 R1 실행의 normalized serving command, R0 대비 `--enforce-eager` 제거 delta, workload SHA256 `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`가 일치한다. Snapshot 경로가 달라 전체 configuration SHA256은 다르므로 같은 문자열 hash라고 주장하지 않는다.

| R1 측정 | Raw verdict | Project A / B output tokens | TTFT s | Prefill tok/s | Mean decode tok/s | Aggregate decode tok/s | E2E tok/s | Wall s | Graph capture/replay |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-09-29 원측정 | `FAIL_OUTPUT` | 2387 PASS / 997 FAIL | 109.22 | 1459.67 | 51.40* | 23.34* | 16.51* | 205.02* | `UNKNOWN` |
| 2026-09-30 재측정 | `PASS_C2_ACTIVE` | 2915 PASS / 1934 PASS | 108.01 | 1484.15 | 30.51 | 30.32 | 22.16 | 218.77 | `UNKNOWN` |

후속 측정은 두 요청 모두 최소 1024 output tokens를 넘기고 `finish_reason=stop`, C2 active/queue=false, post-health healthy였다. 원측정 B의 997-token 조기 종료는 이번에는 재현되지 않았다. `*` 원측정의 mean decode는 A만 반영하며 다른 값에는 실패한 B가 섞인다. 재측정은 output trajectory가 원측정 및 R0와 크게 달라 aggregate decode나 wall 차이를 graph 자체의 속도 향상으로 분리할 수 없다. Graph capture/replay evidence도 여전히 `UNKNOWN`이다.

**현재 판정:** R1은 `FAIL_OUTPUT` 1회와 `PASS_C2_ACTIVE` 1회의 상충된 output evidence가 있다. 원래 2026-09-29 `CLOSED_FAIL_OUTPUT`은 당시 publication 판정으로 보존한다. 후속 1회 PASS만으로 output 안정성이나 graph 효과가 확인됐다고 보지 않아 R1을 final recipe로 승격하지 않는다. R0의 기존 `VALIDATED_RECIPE`와 5.5 publication receipt는 변경하지 않는다. 별도 [후속 machine-readable receipt](../state/wbs5-ornith35-onecat-r1-followup.json)에 두 실행의 verdict와 evidence SHA256을 기록했다. 추가 측정은 이 review에서 실행하지 않았다.
