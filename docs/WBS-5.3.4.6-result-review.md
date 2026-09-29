# WBS 5.3.4.6 — Gemma4 26B-A4B / llama.cpp track result review

Review date: 2026-09-29

## 1. Scope and authoritative evidence

This review performs **no additional GPU inference**. It closes the frozen Gemma4 / llama.cpp WBS5 track using the already-published R0/R1/R2 raw artifacts and the separately completed Gate B evaluation.

| Candidate | Experiment / state | Verdict |
|---|---|---|
| R0 `G4-LCPP-WBS5-R0-TARGET-B512-UB128` | `EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R1 `G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128` | `EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R2 `G4-LCPP-WBS5-R2-TARGET-B1024-UB128` | `EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R3 `G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF` | Gate B `NOT_TRIGGERED` | **SKIP** |

Evidence roots:

- R0: [raw](../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/) / [report](../reports/gemma4-26b-a4b/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001.md)
- R1: [raw](../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001/) / [report](../reports/gemma4-26b-a4b/EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001.md)
- R2: [raw](../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001/) / [report](../reports/gemma4-26b-a4b/EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001.md)

R3 is not a failed measured run. Its conditional trigger was not observed, so the frozen policy correctly skipped it.

## 2. Frozen identity and one-variable deltas

Common invariant:

- Model: `unsloth/gemma-4-26B-A4B-it-qat-GGUF@7b92b5b28818151e8669af2e45e88d6086f490dd`
- Artifact: `gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf`
- SHA256: `a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891`
- Weight: UD-Q4_K_XL
- KV: FP16
- Runtime: llama.cpp b10775 pinned runtime/image
- Topology: shared two-GPU llama.cpp layer split `1,1`
- Context: 262144 total / parallel 2 / unified KV / 131072 per slot
- Flash attention on
- WBS5 `performance/v1.json`, two independent 131072-context requests

Frozen deltas:

- R0: TARGET, batch 512 / ubatch 128.
- R1: `--spec-type none -> ngram-simple` only.
- R2: `--batch-size 512 -> 1024` only, ubatch remains 128.
- R3: R0 plus `GGML_CUDA_DISABLE_GRAPHS=1`, but executable only if Gate B is triggered.

## 3. Gate B result

R0 is both the performance baseline and the evidence source for the graph-off conditional gate.

Observed R0:

- `PASS_C2_ACTIVE`
- graph reuse observed: 4,425
- GPU memory after model load remains approximately 10,033 / 10,531 MiB for about 10 minutes 33 seconds
- a one-time 6 MiB increase near shutdown is not sustained upward drift
- no graph-related server error/instability
- both requests complete and post-health is healthy

Therefore neither frozen trigger, `R0_VRAM_UPWARD_DRIFT` nor `R0_GRAPH_INSTABILITY`, is observed.

Gate B decision: **NOT_TRIGGERED**. No gate receipt is issued and R3 remains **SKIP**.

## 4. Measured comparison

| Metric | R0 TARGET b512 | R1 NGRAM | R1 vs R0 | R2 TARGET b1024 | R2 vs R0 |
|---|---:|---:|---:|---:|---:|
| TTFT | 439.10 s | 448.49 s | +2.14% | 440.10 s | +0.23% |
| Prefill | 359.09 tok/s | 353.18 tok/s | -1.64% | 355.46 tok/s | -1.01% |
| Mean request decode | 22.54 tok/s | 21.48 tok/s | -4.69% | 22.28 tok/s | -1.15% |
| Aggregate decode | 7.54 tok/s | 7.10 tok/s | -5.92% | 7.60 tok/s | +0.72% |
| End-to-end output | 4.78 tok/s | 4.52 tok/s | -5.56% | 4.77 tok/s | -0.22% |
| Batch wall | 671.54 s | 685.38 s | +2.06% | 670.94 s | -0.09% |
| Peak VRAM GPU0/GPU1 | 10,039 / 10,537 MiB | 10,039 / 10,607 MiB | 0 / +70 MiB | 10,039 / 10,537 MiB | no change |

All three measured candidates are `PASS_C2_ACTIVE`, active overlap true, queue-only false, and post-health healthy.

## 5. Output integrity and capacity

Stored outputs:

- R0: 1,603 / 1,610 tokens, both PASS / `finish_reason=stop`.
- R1: 1,462 / 1,635 tokens, both PASS / `finish_reason=stop`.
- R2: 1,633 / 1,570 tokens, both PASS / `finish_reason=stop`.

No measured candidate shows OOM, runtime crash, server-health failure, or C2 queue-only regression.

The WBS5 performance workload has no separate semantic superiority oracle; mechanical output PASS is not expanded into a new semantic ranking claim.

## 6. R1 NGRAM interpretation

R1 has real speculative activity:

- draft tokens: 144
- accepted tokens: 54
- acceptance ratio: 37.5%

However, compared with R0:

- mean request decode -4.69%
- aggregate decode -5.92%
- end-to-end output -5.56%
- batch wall +2.06%
- GPU1 sampled peak VRAM +70 MiB

The mechanism is active but does not improve this workload.

Decision: **R1 branch closed**. NGRAM acceptance alone is not a reason to preserve the candidate, and the review does not add N/M/hits tuning or another speculative variant.

## 7. R2 batch1024 interpretation

R2 doubles the logical batch size while retaining ubatch 128.

Observed versus R0:

- TTFT +0.23%
- Prefill -1.01%
- Mean request decode -1.15%
- Aggregate +0.72%
- End-to-end -0.22%
- Batch wall -0.09%
- no sampled VRAM change

The intended TTFT/prefill benefit is not observed. All differences are small enough to retain ordinary single-run measurement uncertainty; the +0.72% aggregate change is not treated as a recipe-level win.

Request-level decode asymmetry also remains essentially unchanged: R0 roughly 41.26 / 3.82 tok/s and R2 roughly 40.81 / 3.75 tok/s. The larger logical batch does not demonstrate a topology/scheduling change.

Decision: **R2 branch closed — no qualifying measured benefit**. No b2048/ubatch grid is added.

## 8. Power, temperature, and clocks

Observed maxima:

| Candidate | GPU0/GPU1 max power | GPU0/GPU1 max temp | Max SM clock | Memory clock |
|---|---:|---:|---:|---:|
| R0 | 169.00 / 161.46 W | 61 / 58 C | 1200 MHz | 877 MHz |
| R1 | 169.35 / 159.58 W | 60 / 58 C | 1200 MHz | 877 MHz |
| R2 | 168.88 / 161.93 W | 61 / 58 C | 1200 MHz | 877 MHz |

There is no meaningful thermal or clock-state advantage/penalty that changes the candidate decision.

## 9. R0 retention

R0 remains the only frozen configuration that is both:

- valid C2 ACTIVE with healthy output/capacity;
- free of an unhelpful one-variable optimization result.

R1 is slower despite active NGRAM; R2 does not achieve its intended prefill/TTFT effect; R3's gate condition never occurs.

Decision: **retain R0 `G4-LCPP-WBS5-R0-TARGET-B512-UB128` as the sole configuration to carry forward to WBS 5.5 final recipe publication**.

At this review stage it remains a final recipe **candidate/retained configuration**, not an early re-labeling of the raw run as `VALIDATED_RECIPE`.

## 10. Track closeout

Final track decision:

- R0 TARGET b512/ub128: **RETAINED FOR WBS 5.5**.
- R1 NGRAM: **CLOSED — MEASURED PERFORMANCE WORSE**.
- R2 batch1024: **CLOSED — INTENDED EFFECT NOT OBSERVED**.
- R3 graph-off: **SKIP — GATE B NOT_TRIGGERED**.
- No new candidate, no automatic repetition/confirm, no additional GPU inference.
- Final recipe record/status belongs to WBS 5.5.

WBS 5.3.4.6 status: **DONE — R0 RETAINED**.
