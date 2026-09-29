# WBS 7.3 — Qwen3.8 post-WBS5 result review

Status: **DONE — NO NEW VALIDATED RECIPE**. This review uses only the frozen
WBS 5 R2 control and the single measured run of each WBS 7 candidate. Its
[machine-readable comparison](../state/wbs7-review.json) records exact metrics,
request-level deltas, output hashes and the decision.

## MTP1: terminal GPU OOM

`EXP-V100-WBS7-QWEN-LLAMA-MTP1-C2-128K-20260929-001` used the control image,
model, workload and serving settings, changing only to native
`--spec-type draft-mtp --spec-draft-n-max 1`. The server created the embedded
MTP draft context, but a 613.03 MiB GPU1 allocation failed. The first admitted
request then hit CUDA VMM out of memory and the server aborted. Zero requests
completed; post-health failed. The raw harness reports `FAIL_CRASH`; the
[failure review](../results/raw/EXP-V100-WBS7-QWEN-LLAMA-MTP1-C2-128K-20260929-001/wbs7-failure-review.json)
records the terminal cause as **FAIL_OOM**. Speculative acceptance and decode
speed were not measured. This candidate is closed with no retry or smaller
context/KV/MTP fallback.

## GQA×2: C2 active, output PASS, small observed delta

`EXP-V100-WBS7-QWEN-LLAMA-GQA2-Q80-C2-128K-20260929-001` used TARGET mode,
Q8_0 K/V and the frozen performance/v1 workload. The candidate image contains
the isolated GQA×2 Flash Attention forward-port on b10775. Both 128K slots
were resident and active; live slot evidence and interleaved server decode
events support C2 active overlap. Both requests completed with mechanical
output PASS and post-health healthy. The two materialized prompts, output token
counts and full output texts exactly match R2. The workload manifest and
materialized workload SHA256 also match R2.

| Metric | Frozen R2 | GQA×2 | Observed delta |
| --- | ---: | ---: | ---: |
| Mean TTFT | 679.053 s | 679.063 s | +0.001% |
| Prefill | 264.112 tok/s | 264.163 tok/s | +0.02% |
| Project A runtime decode | 9.076 tok/s | 9.813 tok/s | +8.12% |
| Project B runtime decode | 2.109 tok/s | 2.109 tok/s | -0.04% |
| Mean request decode | 5.593 tok/s | 5.961 tok/s | +6.58% |
| Aggregate decode | 4.514 tok/s | 4.612 tok/s | +2.17% |
| End-to-end output | 3.457 tok/s | 3.514 tok/s | +1.66% |
| Batch wall | 1337.272 s | 1315.438 s | -1.63% |
| Peak VRAM GPU0 / GPU1 | 13,447 / 14,533 MiB | 13,447 / 14,533 MiB | unchanged |

The identical outputs remove output-length and output-content differences from
this comparison. Project A's recorded runtime decode improved; Project B's was
essentially unchanged. TTFT and prefill were unchanged. The candidate's
`aggregate_decode_tps` includes overlapping prefill/output windows and is not
a CUDA kernel speed measurement. Both runs reported graph reuse 4,339; this
does not prove identical execution scheduling.

The preflight verified 24 grouped-GQA kernel symbols in the candidate and none
in the control. It did not count GQA kernel calls during this C2 run. The
original control's complete CMake flags are unavailable, so the rebuild is not
a bitwise-controlled one-variable binary comparison. One measured run per
candidate cannot establish repeatability or a noise bound. The performance
workload supplies mechanical output checks, not a semantic coding-quality
oracle.

## Decision

- **MTP1:** close as `FAIL_OOM`; no separate recipe.
- **GQA×2:** preserve the reproducible image, patch and raw result as an
  experimental build. Do not promote it to a validated post-WBS5 recipe from
  the single small observed gain and unverified runtime kernel dispatch.
- **WBS 5:** retain the six published recipes and their frozen evidence without
  rewriting their results. No combined MTP+GQA candidate was created.

Detailed reports: [MTP1](../reports/qwen3-8-27b/EXP-V100-WBS7-QWEN-LLAMA-MTP1-C2-128K-20260929-001.md),
[GQA×2](../reports/qwen3-8-27b/EXP-V100-WBS7-QWEN-LLAMA-GQA2-Q80-C2-128K-20260929-001.md).

Final verification: both remote raw directories match their local copies by
checksum dry-run; frozen WBS5 raw/recipe/workload hashes remain unchanged;
`scripts/validate_repo.py` and the full repository unittest suite pass. P520
has no remaining benchmark container or GPU memory allocation.
