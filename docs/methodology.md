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
3. C2 128K residency/active overlap for C1 survivors.
4. Ornith 9B 1GPU×2 independent-server topology.
5. Performance comparisons inside valid configurations.
6. Final operational selection.

Do not broaden into large context sweeps. 96K/64K is diagnostic only after a clear 128K capacity failure.

## Fresh evidence

Historical repositories are implementation references only. One experiment has one immutable ID, config identity, raw directory and final report. Retries use new IDs.

## Correctness before performance

Performance is valid only after the exact configuration produces valid output and remains healthy.

## C2 meaning

C2 is two independent projects released through a common barrier with different prompt material and hashes.

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

Keep TTFT, ITL, prefill throughput, request decode throughput, aggregate decode throughput, end-to-end output throughput, request/batch wall time and GPU telemetry distinct. Never label all of them simply tok/s.

## Repetition and warmup

Default to one measured execution per configuration unless explicitly authorized otherwise. Readiness/JIT probes are allowed; duplicate full 128K warmups require a documented reason.

## Required lanes

llama.cpp uses TARGET, NGRAM, MTP and MTP_NGRAM. TARGET versus NGRAM is mandatory. MTP and MTP_NGRAM remain explicit rows even when UNSUPPORTED.

STOCK 1Cat and v100-skinny are separate mandatory backend rows.

## Hardware policy

Benchmark scripts observe but do not change power limits, clocks, persistence, drivers, kernel or CPU power policy.
