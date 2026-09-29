# WBS 5.3.1.7 — Qwen3.8-27B / llama.cpp track result review

Review date: 2026-09-29

## 1. Scope and authoritative evidence

This review performs **no additional GPU inference**. It closes the frozen WBS5 Qwen3.8-27B / llama.cpp track using the already-published `performance/v1.json` raw artifacts.

Authoritative measured runs:

| Candidate / run | Experiment | Verdict |
|---|---|---|
| R0 repetition-1 `Q38-LLAMA-WBS5-R0-TARGET-B512-UB128` | `EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R0 repetition-2, same frozen configuration | `EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002` | `PASS_C2_ACTIVE` |
| R1 `Q38-LLAMA-WBS5-R1-NGRAM-DEFAULT` | `EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R2 `Q38-LLAMA-WBS5-R2-TARGET-UB256` | `EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001` | `PASS_C2_ACTIVE` |

R1/R2 optional confirm runs defined by WBS 5.3.1.5 / 5.3.1.6 remain **SKIP — USER_DECISION**. They have no raw/report and are not treated as missing measured evidence or failures.

Evidence roots:

- R0 rep-1: [raw](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001/) / [report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001.md)
- R0 rep-2: [raw](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002/) / [report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002.md)
- R1: [raw](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001/) / [report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001.md)
- R2: [raw](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/) / [report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001.md)

## 2. Frozen identity and one-variable deltas

Common invariant:

- Model: `unsloth/Qwen3.8-27B-GGUF@4ca720788d1e01f1bff70c033e0d0028fd02e502`
- Artifact: `Qwen3.8-27B-UD-Q4_K_M.gguf`
- SHA256: `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`
- Weight: `UD-Q4_K_M`
- KV: `q8_0` K/V
- Runtime: llama.cpp b10775 / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`
- Topology: two-GPU shared llama.cpp layer split `1,1`
- Context: `--ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072`
- Flash attention on, Jinja, reasoning off, metrics/slots enabled, no full-size warmup
- Workload: WBS5 `performance/v1.json`, two independent 131072-context requests, 4096 output reserve, minimum 1024/request, temperature 0 / top_p 1 / seed 520

Frozen deltas:

- R0: TARGET, `--spec-type none --batch-size 512 --ubatch-size 128`
- R1: R0에서 `--spec-type none -> ngram-simple`만 변경. NGRAM pinned defaults 12/48/1.
- R2: R0에서 `--ubatch-size 128 -> 256`만 변경. batch 512 유지.

No new NGRAM parameters, batch grid, graph-off candidate, P2P override, or combined candidate is introduced by this review.

## 3. Metric semantics and evidence limitation

The review preserves the harness/runtime definitions.

- TTFT is client-observed time to first content.
- Prefill TPS is the arithmetic mean of request-level llama.cpp prompt timing when available.
- Mean request decode TPS is the arithmetic mean of request-level runtime decode rates.
- `aggregate_decode_tps` is total output tokens divided by the interval from the earliest first content to the latest request end. It includes scheduling/overlap effects and is **not a pure decode-kernel metric**.
- End-to-end output TPS is total output tokens divided by synchronized batch wall time.
- Peak VRAM comes from 0.5-second `nvidia-smi memory.used` sampling; transient peaks between samples may be missed.
- Graph reuse count is server-lifetime evidence and may include startup/routing-preflight activity. It is not a measured-window hit rate.

Publication caveat: the four runs contain the already-recorded slot-sampler parser failure in `runtime/measurement.log`. Official C2 ACTIVE publication uses the reconciled log-overlap evidence preserved in `completion.json` / `metrics.json`. Raw snapshots are not rewritten by this review.

## 4. Measured comparison

| Metric | R0 rep-1 | R0 rep-2 | R1 NGRAM | R2 UB256 |
|---|---:|---:|---:|---:|
| TTFT | 901.97 s | 904.12 s | 904.45 s | **679.05 s** |
| Prefill | 206.12 tok/s | 178.23 tok/s | 178.17 tok/s | **264.11 tok/s** |
| Mean request decode | 5.269 tok/s | 5.385 tok/s | 5.559 tok/s | **5.593 tok/s** |
| Aggregate decode | 3.693 tok/s | 3.958 tok/s | 3.998 tok/s | **4.514 tok/s** |
| End-to-end output | 2.527 tok/s | 2.732 tok/s | 2.744 tok/s | **3.457 tok/s** |
| Batch wall | 1541.28 s | 1580.35 s | 1560.73 s | **1337.27 s** |
| Total output tokens | 3,895 | 4,318 | 4,283 | 4,623 |
| Peak VRAM GPU0 | 13,159 MiB | 13,159 MiB | 13,161 MiB | 13,447 MiB |
| Peak VRAM GPU1 | 14,247 MiB | 14,245 MiB | 14,249 MiB | 14,533 MiB |
| Graph reuse evidence | 5,096 | 5,521 | 5,081 | 4,339 |
| Spec acceptance | N/A | N/A | 323 / 985 = 32.79% | N/A |

All four authoritative runs are `PASS_C2_ACTIVE`, resident/active overlap true, queue-only false, and post-health healthy.

## 5. Capacity, stability, and output integrity

- Every run completed both requests above the 1024-token minimum.
- Stored request verdicts and mechanical output verdicts are PASS; completions terminate normally with `finish_reason=stop`.
- No OOM, allocator/runtime crash, server-health failure, or queue-only regression occurred in R2 after increasing ubatch to 256.
- R2 peak VRAM increased by roughly 286–288 MiB/GPU relative to R0 while staying within the measured V100 16 GiB envelope.
- The WBS5 performance lane has no separate task-level semantic oracle. This review therefore confirms mechanical/non-truncated output integrity only and does not manufacture a new semantic PASS.

## 6. R0 repeatability interpretation

The two frozen R0 repetitions give the only direct same-configuration repeatability reference in this track.

- TTFT differs by about 0.24%.
- Mean request decode differs by about 2.2%.
- Batch wall differs by about 2.5%.
- Prefill means differ more because request-level scheduling/client timing is asymmetric; R0 rep-1 project-b contains substantial client TTFT beyond server prompt timing.

Accordingly, tiny single-run differences near a few percent are not treated as decisive recipe evidence without a mechanism-aligned signal.

## 7. R1 NGRAM interpretation

R1 proves that the frozen `ngram-simple` mechanism was active:

- draft tokens: 985
- accepted tokens: 323
- acceptance ratio: 32.79%
- accepted/output coverage: about 7.54%

However, against the cleaner R0 rep-2 reference:

- TTFT +0.04%
- Prefill -0.03%
- Mean request decode +3.23%
- Aggregate +1.02%
- End-to-end +0.44%
- Batch wall -1.24%

These are small changes relative to single-run variability and output-length differences. The observed NGRAM acceptance does not translate into a clear WBS5 workload-level performance win.

Decision: **R1 branch closed**. Preserve mechanism evidence; do not add N/M/hits tuning or another NGRAM candidate.

## 8. R2 UB256 interpretation

R2 changes only the physical microbatch from 128 to 256.

Observed:

- Mean TTFT 679.05 s versus R0 901.97 / 904.12 s: about 24.7–24.9% lower.
- Request-level server prompt timing also decreases materially versus R0 rep-2: project-a about -20.8%, project-b about -36.0%.
- Prefill mean rises to 264.11 tok/s.
- Batch wall falls to 1337.27 s, about 13.2–15.4% shorter than the two R0 repetitions, despite generating more total output tokens.
- Mean request decode is maintained with a weak positive signal rather than a major decode optimization.
- Cost: about +0.29 GiB sampled peak VRAM per GPU.

The robust claim is **long-context prefill / TTFT / wall improvement**. Aggregate and end-to-end gains are valid run-level signals but must not be restated as pure decode-kernel speedups.

Decision: **retain R2 `Q38-LLAMA-WBS5-R2-TARGET-UB256` as the track's final recipe candidate**.

This is candidate selection for later WBS 5.5 recording. It is not an instruction to reopen optional confirm runs, add new candidates, or silently label the recipe `VALIDATED_RECIPE` before final publication.

## 9. Power, temperature, clocks, and graph

No raw evidence indicates that R2's large TTFT/prefill change came from a different thermal/clock failure state.

- R2 sampled max temperature: GPU0 72 C / GPU1 63 C.
- R2 max SM clock: 1200 MHz on both GPUs.
- Memory clock remains 877 MHz.
- Post-health is healthy.
- CUDA graph reuse is observed in all four runs. Reuse count is not used to rank candidates because its scope is the full server lifetime.

## 10. Track closeout

Final track decision:

- R0: canonical repeated reference/control.
- R1 NGRAM: **CLOSED — NO QUALIFYING RECIPE BENEFIT**.
- R2 UB256: **FINAL RECIPE CANDIDATE — LONG-PREFILL / TTFT ORIENTED**.
- R1/R2 optional confirms: remain **SKIP — USER_DECISION**.
- No new candidate and no additional GPU inference.
- Screening R2 is n=1; this limitation must remain in final recipe publication.
- WBS 5.5 is responsible for exact final recipe record/status.

WBS 5.3.1.7 status: **DONE — R2 FINAL RECIPE CANDIDATE**.
