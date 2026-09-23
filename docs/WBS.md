# WBS — 2× Tesla V100 16GB Final LLM Serving Acceptance

## 0. Project contract [DONE]

### 0.1 Repository foundation [DONE]
- Reuse the proven evidence/reporting structure from qwen3.8-bench.
- Do not import historical raw results as current acceptance evidence.
- Freeze C1/C2 terminology, 128K per-agent target, and immutable experiment IDs.

### 0.2 Measurement harness [DONE]
- C1/C2 barrier execution.
- Live tokenizer receipt and 128K budget validation.
- Independent Project A/B prompt hashes.
- Raw evidence to report to summary/comparison CSV publication.
- Explicit verdicts for C1, C2 residency/active overlap, queue-only, OOM/capacity/runtime/output failures.

### 0.3 Runtime lanes [DONE]
- llama.cpp: TARGET / NGRAM / MTP / MTP_NGRAM.
- 1Cat-vLLM: STOCK.
- v100-skinny: mandatory SKINNY lane.
- Shared TP2 and Ornith 9B 1GPU×2 topology definitions.

## 1. Fresh environment and artifact verification [TODO]

### 1.1 Host snapshot
Capture driver/CUDA compatibility, both V100 identities and VRAM, power/clocks/persistence state, CPU/RAM/kernel, GPU processes and listening ports.

Benchmark automation must not alter hardware policy.

### 1.2 llama.cpp runtime verification
Verify the pinned image/build/commit and confirm support for:
- kv-unified
- kv-unified-per-slot
- spec-type none
- ngram-simple
- draft-mtp
- composite draft-mtp,ngram-simple

### 1.3 1Cat-vLLM STOCK verification
Verify:
- 1Cat-vLLM 1.5.0 exact wheel identity
- FLASH_ATTN_V100
- TP2 startup
- tokenizer/template/tool/parser requirements for each model profile

### 1.4 v100-skinny verification
Mandatory:
- exact skinny commit 5b589c0dc81223e0ba65bcb3e755874723f8b515
- exact 1Cat-vLLM 1.2.2 wheel
- exact Qwen3.8 RadixArk revision
- TP2 experimental boot
- skinny_gate.py with TP2 and depth 3 PASS

A TP2 failure remains UNSUPPORTED, FAIL_STARTUP, FAIL_OOM or FAIL_CAPACITY. Never replace it with the published TP4 result.

### 1.5 Model artifact resolution
Freshly verify the existing pinned artifacts for:
- Qwen3.8-27B llama.cpp
- Qwen3.8-27B STOCK 1Cat
- Qwen3.8-27B SKINNY
- Ornith 1.5 9B llama.cpp
- Ornith 1.5 35B-A3B llama.cpp

Resolve or explicitly mark unsupported/pending:
- Ornith 9B STOCK 1Cat NVFP4
- Ornith 35B STOCK 1Cat NVFP4
- Gemma4 26B llama.cpp exact artifact
- Gemma4 26B STOCK 1Cat NVFP4
- non-Qwen v100-skinny contracts

No guessed repository, revision or path is allowed.

## 2. C1 — 128K capacity and correctness [TODO]

Use workloads/capacity/v1.json, materialized against the exact live tokenizer.

### 2.1 llama.cpp mandatory lanes
For every verified llama.cpp artifact execute:
1. TARGET
2. NGRAM
3. MTP
4. MTP_NGRAM

Rules:
- TARGET versus NGRAM is mandatory.
- MTP versus MTP_NGRAM remains explicit even if either result is UNSUPPORTED.
- Start directly at 128K.
- 96K/64K is diagnostic only after a 128K capacity failure.

C1 PASS requires near-128K live-tokenizer budget, requested output completion, valid output, no OOM/truncation/corruption and healthy post-run server.

### 2.2 1Cat-vLLM STOCK
For every verified STOCK artifact:
- TP2
- max_model_len 131072
- max_num_seqs 1
- declared KV format
- fresh C1 128K acceptance

### 2.3 v100-skinny SKINNY
Mandatory Qwen3.8 TP2 experiment:
- v100-skinny v1.1
- 1Cat 1.2.2
- RadixArk mixed NVFP4/FP8 checkpoint
- FP16 KV
- MTP k=3
- 128K
- TP2 skinny boot gate preserved as evidence

Non-Qwen skinny rows must resolve to executable support or UNSUPPORTED.

## 3. C2 — two independent 128K agents [TODO]

Prerequisite: exact C1 lane passed 128K, except a deliberate C2 failure-boundary experiment.

Use workloads/concurrency/v1.json:
- Project A and Project B are unrelated
- prompt hashes differ
- no large artificial shared prefix

### 3.1 Shared TP2 llama.cpp
Use:
- parallel 2
- ctx-size 262144
- kv-unified
- kv-unified-per-slot 131072

### 3.2 Shared TP2 1Cat / skinny
Use:
- TP2
- max_model_len 131072
- max_num_seqs 2

Record separately:
- both requests admitted
- both contexts resident
- actual active decode overlap
- queue/preemption behavior
- per-request and aggregate performance

Do not convert QUEUE_ONLY into PASS_C2_ACTIVE.

## 4. Ornith 1.5 9B — 1GPU×2 independent topology [TODO]

This is a first-class deployment topology.

For every llama.cpp lane that proves one-GPU 128K compatibility:
- GPU0 to Server A to Project A
- GPU1 to Server B to Project B
- both servers active simultaneously

Evaluate TARGET, NGRAM, MTP and MTP_NGRAM whenever each lane fits one GPU.

Compare with shared TP2 on:
- two-session fit
- TTFT
- per-agent decode
- aggregate throughput
- peak VRAM
- failure isolation
- operational simplicity

## 5. Performance comparison and lane reduction [TODO]

Only capacity/correctness-valid configurations enter performance comparison.

### 5.1 llama.cpp
Within the same model/artifact/KV/topology compare:
- TARGET vs NGRAM
- MTP vs MTP_NGRAM
- TARGET vs MTP where supported
- C1 vs C2 degradation

### 5.2 1Cat
For Qwen3.8 compare STOCK vs SKINNY as practical serving configurations while disclosing checkpoint/KV/spec/runtime differences. Do not claim a kernel-only causal A/B.

### 5.3 Metrics
Preserve TTFT, prefill tok/s, mean request decode tok/s, aggregate decode tok/s, end-to-end output tok/s, batch wall time, GPU0/GPU1 VRAM, power, temperature, clocks, and speculative acceptance evidence when available.

## 6. Final deployment decision [TODO]

Final report must answer:
1. Can one 128K single-agent project run reliably?
2. Can two independent 128K projects coexist and actively execute?
3. Which passing topology is practical for daily coding-agent use?

Include exact model/runtime/quant/KV/spec/topology, C1 result, C2 resident result, C2 active result, measured performance and operational caveats.

Serving feasibility comes first. Model quality and coding-agent usefulness remain a separate final consideration.

## Execution rules
- One measured execution per declared configuration unless explicitly approved otherwise.
- Never silently change context, quantization, KV, speculative method or topology after failure.
- Diagnostic 96K/64K reruns receive new experiment IDs.
- UNSUPPORTED is a valid final row.
- Historical qwen3.8-bench results never count as a PASS here.
