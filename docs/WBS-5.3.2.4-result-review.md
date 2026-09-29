# WBS 5.3.2.4 — Ornith 1.5 9B / llama.cpp track result review

Review date: 2026-09-29

## 1. Scope and authoritative evidence

This review performs **no additional GPU inference**. It closes the frozen Ornith 1.5 9B / llama.cpp WBS5 track using the three already-published `performance/v1.json` runs.

| Candidate | Experiment | Verdict |
|---|---|---|
| R0 `TARGET_BASELINE` | `EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R1 `TARGET_UB256` | `EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R2 `NGRAM_DEFAULT` | `EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260928-001` | `PASS_C2_ACTIVE` |

Evidence roots:

- R0: [raw](../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001/) / [report](../reports/ornith-1.5-9b/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001.md)
- R1: [raw](../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/) / [report](../reports/ornith-1.5-9b/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001.md)
- R2: [raw](../results/raw/EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260928-001/) / [report](../reports/ornith-1.5-9b/EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260928-001.md)

The old R0 attempt from the pre-fix HEAD that terminated because the llama.cpp slot evidence parser mishandled `next_token: []` is **HARNESS_INVALID / INCONCLUSIVE** and is excluded from the authoritative performance comparison.

## 2. Frozen identity and topology

Common invariant:

- Model artifact: `/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf`
- SHA256: `79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480`
- Weight: Q6_K
- KV: FP16
- Runtime: llama.cpp b10775
- Serving topology: **1GPU×2 + LiteLLM**
- backend-0 on GPU0 and backend-1 on GPU1
- backend each: context 131072, parallel 1, unified KV per slot 131072
- LiteLLM: pinned 1.101.0 gateway, least-busy, `max_parallel_requests=1`, `num_retries=0`
- Flash attention on, Jinja, reasoning off, no-warmup
- WBS5 performance workload: independent A/B, context 131072 each, output reserve 4096, minimum 1024, temperature 0 / top_p 1 / seed 520

Frozen deltas:

- R0: TARGET, batch 512 / ubatch 128.
- R1: both backends `--ubatch-size 128 -> 256` only.
- R2: both backends `--spec-type none -> ngram-simple` only; batch/ubatch remain 512/128 and NGRAM parameters stay at pinned defaults.

## 3. Routing and concurrency validity

All three authoritative runs preserve the intended deployment topology.

- project-a routes to backend-0 `:18080`
- project-b routes to backend-1 `:18081`
- distinct base/deployment evidence is present
- `active_overlap=true`
- `backend_active_in_common_decode_window=true`
- `queue_only=false`
- post-health is healthy

Thus the results are valid measurements of the frozen 1GPU×2 + LiteLLM topology rather than a queue-only fallback.

The performance workload does not include the WBS3 semantic oracle. Stored PASS therefore establishes the WBS5 mechanical/non-truncated output contract, not a new task-level semantic superiority claim.

## 4. Measured comparison

| Metric | R0 TARGET / ub128 | R1 TARGET / ub256 | R1 vs R0 | R2 NGRAM / ub128 | R2 vs R0 |
|---|---:|---:|---:|---:|---:|
| TTFT | 182.020 s | **139.204 s** | **-23.52%** | 182.040 s | +0.01% |
| Prefill | 697.74 tok/s | **912.19 tok/s** | **+30.73%** | 697.67 tok/s | -0.01% |
| Mean request decode | 43.81 tok/s | 43.99 tok/s | +0.40% | 43.21 tok/s | -1.38% |
| Aggregate decode | 77.73 tok/s | **80.90 tok/s** | +4.08% | 76.57 tok/s | -1.49% |
| End-to-end output | 13.03 tok/s | **16.20 tok/s** | **+24.28%** | 13.00 tok/s | -0.24% |
| Batch wall | 215.90 s | **173.34 s** | **-19.71%** | 216.41 s | +0.24% |
| Peak VRAM / GPU | 10,893 MiB | 10,945 MiB | +52 MiB / +0.48% | 10,893 MiB | 0 |

Request output tokens:

- R0: project-a 1,204 / project-b 1,610, both PASS.
- R1: project-a 1,438 / project-b 1,370, both PASS.
- R2: project-a 1,204 / project-b 1,610, both PASS.

## 5. Capacity, stability, and telemetry

R0/R1/R2:

- all finish `PASS_C2_ACTIVE`;
- both requests exceed the 1024-token minimum;
- no OOM, runtime crash, gateway fallback, queue-only regression, or post-health failure is recorded;
- graph reuse is observed in all three runs, but server-lifetime counts are not used as a candidate ranking metric.

R1's ubatch increase costs only +52 MiB sampled peak VRAM per GPU.

Observed thermal/power envelope remains comparable:

- R0 max power GPU0/GPU1: 165.96 / 162.29 W; max temp 72 / 66 C.
- R1: 171.23 / 168.75 W; max temp 71 / 65 C.
- SM clock range remains 135–1200 MHz and memory clock 877 MHz.

There is no evidence that R1's latency gain is explained by a thermal/clock state change.

## 6. R1 UB256 interpretation

R1's intended effect is to reduce the 128K prefill bottleneck while preserving decode and deployment behavior.

Observed versus R0:

- TTFT -23.52%
- Prefill +30.73%
- Batch wall -19.71%
- End-to-end output +24.28%
- Mean request decode +0.40%: effectively preserved
- Aggregate decode +4.08%
- Peak VRAM +52 MiB/GPU

The direction is consistent across the metrics most directly tied to the intended axis: prefill throughput, TTFT, and wall time.

Decision: **retain R1 `TARGET_UB256` as the track's final recipe candidate**.

The validated claim is long-context prefill/latency improvement in the frozen 1GPU×2 + LiteLLM deployment. It is not a claim that ubatch 256 materially accelerates the decode kernel.

## 7. R2 NGRAM interpretation

The R2 configuration was actually launched with `ngram-simple`, but measured-window speculative evidence is:

- `draft_tokens=0`
- `accepted_tokens=0`
- `draft_count=0`
- `acceptance_ratio=None`

Performance versus R0 is effectively unchanged:

- TTFT +0.01%
- Prefill -0.01%
- Mean request decode -1.38%
- Aggregate -1.49%
- E2E -0.24%
- Wall +0.24%
- identical sampled peak VRAM

Decision: **R2 branch closed**. The intended NGRAM activity is not observed for this workload, and the small performance differences are not promoted to a regression claim. No N/M/hits tuning or another speculative candidate is added.

## 8. R0 baseline interpretation

R0 remains the valid serving reference/control for the topology:

- correct distinct routing,
- active overlap,
- stable health,
- mechanical output PASS,
- normal capacity envelope.

It is not retained as the optimization candidate because R1 produces a large, directionally consistent prefill/TTFT/wall improvement without a material capacity penalty.

## 9. Metric interpretation limitations

- Each frozen candidate has one authoritative measured run. There is no automatic repetition requirement.
- Differences below roughly a few percent retain normal single-run uncertainty.
- Aggregate decode includes request overlap/scheduling effects and is not a pure kernel metric.
- End-to-end output TPS depends on generated output length.
- Peak VRAM and telemetry are sampled rather than continuous.
- WBS5 performance output PASS is not a replacement for a separate semantic oracle.

## 10. Track closeout

Final track decision:

- R0 `TARGET_BASELINE`: reference/control.
- R1 `TARGET_UB256`: **FINAL RECIPE CANDIDATE — LONG-PREFILL / LATENCY ORIENTED**.
- R2 `NGRAM_DEFAULT`: **CLOSED — INTENDED EFFECT NOT OBSERVED**.
- No MTP/MTP_NGRAM reopening, no additional ubatch sweep, no graph-off candidate, no new speculative tuning.
- No additional GPU inference.
- Final exact recipe/status publication remains WBS 5.5 work.

WBS 5.3.2.4 status: **DONE — REVIEW_COMPLETE / RECIPE_PENDING**.
