# Workload and Measurement Contract

This document defines what a comparable measurement means. It does not authorize GPU execution.

## 1. Workload identity

Every measured workload has immutable source bytes and a SHA256. Every intended request records at least:

- request ID and project/branch identity;
- raw prompt SHA256;
- tokenizer/chat-template identity;
- exact post-template prompt tokens;
- context budget;
- requested and actual completion tokens;
- sampling, reasoning and tool settings.

Do not reuse guessed token counts when the tokenizer, template, model or runtime identity changes.

## 2. Primary context target

The primary target is **128K per agent**, where K = 1024.

`context_budget_tokens_per_request` includes both prompt and output reservation:

`post_template_prompt_tokens + requested_output_tokens <= 131072`.

Primary capacity/C2 workloads reserve 2048 output tokens and require at least 256 actual completion tokens. The sustained C2 performance workload reserves 4096 and requires at least 1024 actual completion tokens.

A small prompt sent to a server configured for 128K is not a 128K test. Startup, KV allocation, slot creation or scheduler admission alone is not a context PASS. The request must fill the vast majority of the declared budget and complete its declared output objective.

The normal acceptance path goes directly to 128K. 96K/64K may be used only as diagnostic fallback points after a 128K failure.

## 3. C1 and C2

Only two serving concurrency levels are primary:

- **C1**: one independent single-agent project request.
- **C2**: two independent single-agent project requests released through a common barrier.

C2 represents Project A + Project B, not two cooperating agents in one project. The two long prompts must use distinct project material and distinct hashes. Do not manufacture a large common prefix merely to reduce KV consumption.

A C2 result must distinguish:

- both requests accepted by the API;
- both contexts resident concurrently;
- actual server-side active overlap;
- queue-only behavior.

Client socket overlap or `parallel=2` / `max_num_seqs=2` configuration alone does not prove active C2. Shared llama.cpp evidence samples `llamacpp:requests_processing`, `llamacpp:requests_deferred` and `/slots`; shared vLLM evidence samples `vllm:num_requests_running` and `vllm:num_requests_waiting`. For Ornith 9B 1GPU×2, both requests are sent to one LiteLLM endpoint. Acceptance requires overlapping decode lifetimes plus evidence that both backend deployments participated, using backend processing samples and/or distinct LiteLLM deployment response headers. Direct client routing to backend A/B is diagnostic only.

### 3.1 Authoritative WBS 3 C2 workload

`workloads/concurrency/v1.json` is historical evidence only. WBS 3 final acceptance uses `workloads/concurrency/v2.json`.

v2 contains one pre-registered seeded defect per project in a non-repeated anchor and fills the remaining 128K budget with semantically-neutral section-variant padding. The semantic oracle is frozen before execution in `workloads/concurrency/v2-ground-truth.json`.

C2 records three independent dimensions: runtime concurrency topology, mechanical output integrity, and oracle-grounded semantic correctness. Output failure must not erase scheduler evidence; runtime C2 success does not convert a semantically wrong answer into a correctness PASS.

## 4. Required request and batch evidence

Per request, preserve where available:

- post-template prompt tokens;
- requested/actual output tokens;
- TTFT and ITL;
- prefill throughput;
- decode throughput;
- wall time;
- final status/error;
- speculative drafted/accepted counters.

Per C2 batch, preserve:

- common release timestamp and submission skew;
- lifecycle timestamps for both requests;
- server-side overlap evidence;
- for 1GPU×2: LiteLLM deployment ID/API-base response headers when present and both backend probe summaries;
- completion count;
- aggregate decode throughput;
- end-to-end output throughput;
- batch wall time;
- post-run health;
- GPU telemetry window.

SSE chunks are not tokens. Missing metrics are null/N/A with a reason, never fabricated as zero.

## 5. Context acceptance

A request is capacity PASS only if it is admitted, completes prefill, produces the declared output objective, avoids OOM/unintended truncation/corruption, and leaves the server healthy.

Capacity and usability are separate. A configuration can fit 128K while falling outside the useful performance frontier.

## 6. Speculative and cache comparability

Target-only, MTP, MTP+ngram and other speculative implementations are distinct configurations. Record exact flags and acceptance definitions.

For llama.cpp, ngram is a required test axis. Unsupported model/build combinations are recorded as `UNSUPPORTED`, not silently omitted or patched into a different test. Capacity fillers may contain repeated synthetic structure, so performance claims involving NGRAM use the dedicated diversified performance workload rather than the capacity filler alone.

Prefix caching must be declared. C2 acceptance workloads should not depend on a large cross-project shared prefix. If cache instrumentation is unavailable, do not attribute performance differences to cache hits.

## 7. Hardware telemetry

Capture per GPU at a declared interval where practical:

`timestamp, temperature, power draw/limit, utilization, memory used/total, SM clock, memory clock`.

Benchmark automation observes hardware policy; it does not set GPU power, clocks or persistence. The measured request window also samples `nvidia-smi` memory usage and merges GPU0/GPU1 sampled peak VRAM into normalized experiment metrics; this is a sampled peak and may miss between-sample transients.

## 8. Evidence lifecycle

1. Freeze experiment, workload, model and runtime identities.
2. Capture fresh read-only host/process/hardware preflight.
3. Start only project-owned benchmark services.
4. Execute the declared C1 or synchronized C2 workload.
5. Save every intended request, logs, telemetry and post-health.
6. Classify the original objective without silently changing context or concurrency.
7. Generate the Markdown report and normalized CSV rows from the same raw evidence.
