# Gemma4 MTP diagnostics on llama.cpp b10775

## D2.1.4A — TP2, --fit off

- Diagnostic ID: `DIAG-GEMMA4-MTP-FITOFF-B10775-20260924-001`
- Measured C1: no
- Sole change from baseline: `--fit off`
- Target SHA256: exact match
- Smart-Q4_0 MTP companion SHA256: exact match
- Verdict: **FAIL_STARTUP**
- Exit code: **139**

The draft model began loading and the process aborted in `common_speculative_init_result`. Disabling memory fitting did not change the startup failure, so memory fitting itself is not sufficient to explain the crash.

## Same-build CLI diagnostic

- Diagnostic ID: `DIAG-GEMMA4-MTP-CLI-B10775-20260924-001`
- Measured C1: no
- Exit code: **139**

The decisive backend message was:

`pre-allocated tensor (cache_k_l28) in a buffer (CUDA1) that cannot run the operation (NONE)`

The backtrace proceeded through `llama_context::graph_reserve`, `resolve_fused_ops`, `sched_reserve`, and speculative initialization.

This rules out a simple server-only explanation. The next diagnostic isolates multi-GPU layer-split/KV placement by keeping the same build and artifacts while using one GPU and a reduced startup context.

## D2.1.4B — TP2 row-split diagnostic

- Diagnostic ID: `DIAG-GEMMA4-MTP-ROW-B10775-20260924-001`
- Measured C1: no
- Context: 131072
- Change from baseline: `split-mode layer -> row`, `main-gpu=0`
- Verdict: **DIAGNOSTIC TOPOLOGY UNSUPPORTED**
- Process exit code: **1**

The target model did not reach Gemma4 MTP initialization. The pinned V100 CUDA backend rejected row split during model load:

`device CUDA0 does not support split buffers`

Therefore this result cannot support or refute the MTP/KV-placement hypothesis. It only establishes that row split is unavailable for this diagnostic on the pinned V100 runtime.

## D2.1.4C — next diagnostic

Use one visible GPU (CUDA0), reduced 8192 context, and partial target GPU offload so the target + smart-Q4_0 drafter can plausibly fit. Keep the same b10775 and MTP n=4. The goal is startup only: determine whether removing CUDA1 eliminates the speculative-context crash.
