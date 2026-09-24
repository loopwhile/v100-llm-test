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
