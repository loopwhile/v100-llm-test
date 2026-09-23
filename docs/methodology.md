# Methodology

## Mission

Determine a practical final serving configuration for independent single-agent coding projects on 2× Tesla V100 16GB.

Primary operating pattern:

- one project active most of the time (C1);
- occasionally two independent projects active together (C2);
- C3+ is out of scope.

The primary context target is 128K per agent.

## Measurement order

The project optimizes in this order:

1. runtime/model compatibility and correctness;
2. C1 128K capacity;
3. C2 128K residency and active-overlap capacity;
4. C1/C2 latency and throughput;
5. required speculative/backend lanes, including llama.cpp ngram and v100-skinny;
6. final operational selection.

Do not expand back into broad 8K→16K→32K→64K sweeps by default. If direct 128K fails for a clearly memory-related reason, 96K/64K may be measured as diagnostics.

## Fresh evidence

Historical repositories are implementation references only. Do not copy historical raw results or reports into this repository as current evidence.

One experiment has one immutable ID, one config identity, one raw evidence directory and one final report. A retry receives a new ID and preserves the failed predecessor.

## Correctness before performance

Performance is valid only after the exact configuration produces readable/protocol-valid output and the server remains healthy. Tool/reasoning/chat-template correctness is recorded when the serving lane requires it.

## C2 meaning

C2 is two independent projects. Use synchronized release but different project material and prompt hashes. Preserve both intended requests even when one fails or queues.

The report must distinguish:

- `PASS_C1_128K`;
- `PASS_C2_RESIDENT`;
- `PASS_C2_ACTIVE`;
- `QUEUE_ONLY`;
- `FAIL_STARTUP`;
- `FAIL_OOM`;
- `FAIL_CAPACITY`;
- `FAIL_TIMEOUT`;
- `FAIL_CRASH`;
- `FAIL_OUTPUT`;
- `UNSUPPORTED`;
- `INCONCLUSIVE`.

A queue-only server may still be operationally useful, but it is not an active-C2 PASS.

## Metric definitions

Keep these names separate:

- TTFT;
- ITL when true token timestamps exist;
- prompt/prefill throughput;
- per-request decode throughput;
- mean request decode throughput;
- aggregate decode throughput over a declared common interval;
- end-to-end output throughput;
- request wall time;
- batch wall time;
- peak VRAM/power/temperature and observed clocks.

Do not call all of them simply `tok/s`. Do not sum per-request decode rates and relabel that value as aggregate throughput.

## Repetition and warmup

Default to one measured execution per declared configuration unless a later WBS explicitly requests repetitions. Lightweight readiness/JIT checks are allowed, but do not run a duplicate full 128K workload merely as warmup without a documented reason.

## Required optimization lanes

### llama.cpp

The final llama.cpp test program must explicitly cover its declared target-only/native-MTP baselines and the required ngram lane. Unsupported ngram is a recorded result, not a skipped row.

### 1Cat-vLLM

Stock 1Cat and 1Cat + v100-skinny are separate mandatory lanes. Do not treat skinny as an informal post-benchmark tweak.

## Hardware policy

All benchmark scripts are read-only with respect to power limits, clocks, persistence, drivers, kernel and CPU power policy. Capture current state before runs; do not normalize it by silently changing the host.
