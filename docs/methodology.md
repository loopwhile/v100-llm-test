# Methodology

## Mission

Validate practical serving configurations for independent single-agent coding projects on 2× Tesla V100 16GB, then publish reproducible recipes and bounded failure/limitation evidence. The project does **not** automatically choose a single production winner.

Operating pattern:
- C1 normally
- C2 occasionally
- C3+ out of scope
- 128K target per agent

## Measurement order
1. Fresh runtime/model/artifact compatibility.
2. C1 128K capacity/correctness for every required lane.
3. C2 128K residency/active overlap for C1 survivors, proven with runtime-side overlap evidence.
4. Ornith 9B 1GPU×2 + LiteLLM end-to-end topology validation where the backend can fit the requested 128K contract.
5. Performance comparisons inside valid configurations.
6. Publish validated recipes, reference baselines, closed branches, and known limitations without automatic overall winner selection.

Do not broaden into large context sweeps. 96K/64K is diagnostic only after a clear 128K capacity failure.

## Fresh evidence

Historical repositories are implementation references only. One experiment has one immutable ID, config identity, raw directory and final report. Retries use new IDs.

Historical raw/config/plan files preserve the state that existed when the experiment was planned or executed. Current status is recorded separately; do not rewrite historical evidence to make it look current.

## Correctness before performance

Performance is valid only after the exact configuration produces valid output and remains healthy. Performance-workload mechanical PASS does not create a new task-level semantic certification.

## C2 meaning

C2 is two independent projects released through a common barrier with different prompt material and hashes. Shared-server `PASS_C2_ACTIVE` requires sampled server state consistent with two running/processing requests during the overlapping decode window; client sockets alone are insufficient.

For a runnable Ornith 9B 1GPU×2 topology, both requests enter through the same LiteLLM endpoint and evidence must show that both one-GPU backends participated. Direct per-request backend routing is diagnostic only.

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

`QUEUE_ONLY` is not `PASS_C2_ACTIVE`.

## Metrics

Keep TTFT, ITL, prefill throughput, request decode throughput, aggregate decode throughput, end-to-end output throughput, request/batch wall time and GPU telemetry distinct. Never label all of them simply tok/s.

Sustained C2 comparisons use `workloads/performance/v1.json` (4096 reserved output, at least 1024 actual output, diversified identifiers), while capacity acceptance uses the shorter 2048/256-token objective.

## Repetition and warmup

Default to one measured execution per configuration unless explicitly authorized otherwise. Readiness/JIT probes are allowed; duplicate full 128K warmups require a documented reason.

## Required lanes

llama.cpp uses TARGET, NGRAM, MTP and MTP_NGRAM. TARGET versus NGRAM is mandatory. MTP and MTP_NGRAM remain explicit rows even when `UNSUPPORTED`.

For C1/C2, NGRAM is an acceptance/compatibility lane: prove that the declared NGRAM configuration starts, remains healthy, preserves output integrity, and meets the requested context/concurrency capacity. Draft/accepted-token activity or a throughput gain is not required for C1/C2 PASS. NGRAM performance effectiveness is evaluated with the sustained performance workload.

STOCK 1Cat and v100-skinny are separate mandatory backend rows.

LiteLLM v1.101.0 is a mandatory measured component for any runnable Ornith 9B 1GPU×2 topology. Its routing overhead is intentionally included in end-to-end TTFT and throughput. A backend that fails its per-GPU 128K startup/capacity gate does not inherit the successful llama.cpp topology result.

## Hardware policy

Benchmark scripts observe but do not change power limits, clocks, persistence, drivers, kernel or CPU power policy.
