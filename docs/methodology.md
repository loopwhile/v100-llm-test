# Methodology

## Mission

Find a practical final serving configuration for independent single-agent coding projects on 2× Tesla V100 16GB.

Operating pattern:
- C1 normally
- C2 occasionally
- C3+ out of scope
- 128K target per agent

## Measurement order
1. Fresh runtime/model/artifact compatibility.
2. C1 128K capacity/correctness for every required lane.
3. C2 128K residency/active overlap for C1 survivors, proven with runtime-side overlap evidence.
4. Ornith 9B 1GPU×2 + LiteLLM end-to-end serving topology.
5. Performance comparisons inside valid configurations.
6. Final operational selection.

Do not broaden into large context sweeps. 96K/64K is diagnostic only after a clear 128K capacity failure.

## Fresh evidence

Historical repositories are implementation references only. One experiment has one immutable ID, config identity, raw directory and final report. Retries use new IDs.

## Correctness before performance

Performance is valid only after the exact configuration produces valid output and remains healthy.

## C2 meaning

C2 is two independent projects released through a common barrier with different prompt material and hashes. Shared-server PASS_C2_ACTIVE requires sampled server state consistent with two running/processing requests during the overlapping decode window; client sockets alone are insufficient. For Ornith 9B 1GPU×2, both requests must enter through the same LiteLLM endpoint and the evidence must show that both one-GPU backends participated; direct per-request backend routing is not an acceptance test.

Verdicts include:
- PASS_C1_128K
- PASS_C2_RESIDENT
- PASS_C2_ACTIVE
- QUEUE_ONLY
- FAIL_STARTUP
- FAIL_OOM
- FAIL_CAPACITY
- FAIL_TIMEOUT
- FAIL_CRASH
- FAIL_OUTPUT
- UNSUPPORTED
- INCONCLUSIVE

QUEUE_ONLY is not PASS_C2_ACTIVE.

## Metrics

Keep TTFT, ITL, prefill throughput, request decode throughput, aggregate decode throughput, end-to-end output throughput, request/batch wall time and GPU telemetry distinct. Never label all of them simply tok/s. Sustained C2 comparisons use workloads/performance/v1.json (4K reserved output, >=1K actual output, diversified identifiers), while capacity acceptance uses the shorter 2K/256-token objective.

## Repetition and warmup

Default to one measured execution per configuration unless explicitly authorized otherwise. Readiness/JIT probes are allowed; duplicate full 128K warmups require a documented reason.

## Required lanes

llama.cpp uses TARGET, NGRAM, MTP and MTP_NGRAM. TARGET versus NGRAM is mandatory. MTP and MTP_NGRAM remain explicit rows even when UNSUPPORTED.

For C1/C2, NGRAM is an acceptance/compatibility lane: prove that the declared NGRAM configuration starts, remains healthy, preserves output integrity, and meets the requested context/concurrency capacity. Draft/accepted-token activity or a throughput gain is not required for C1/C2 PASS. NGRAM performance effectiveness is evaluated only in Phase 5 with the sustained performance workload.

STOCK 1Cat and v100-skinny are separate mandatory backend rows.

LiteLLM v1.101.0 is a mandatory measured component of the Ornith 9B 1GPU×2 topology. Its routing overhead is intentionally included in end-to-end TTFT and throughput for that topology.

## Hardware policy

Benchmark scripts observe but do not change power limits, clocks, persistence, drivers, kernel or CPU power policy.
