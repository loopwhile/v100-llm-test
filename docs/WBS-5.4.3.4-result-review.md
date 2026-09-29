# WBS 5.4.3.4 — Ornith 1.5 35B-A3B / 1Cat-vLLM track result review

Review date: 2026-09-29

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
