# Runtime Policy

This repository compares pinned V100/SM70 serving lanes. Mutable labels such as latest may be used for discovery, but not as the benchmark identity.

## llama.cpp

Record image digest, build/commit, CUDA userspace, exact launch command, topology, artifact hash, KV and speculative mode.

Every verified llama.cpp candidate has four explicit rows:
- TARGET — target-only
- NGRAM — ngram-only
- MTP — native MTP
- MTP_NGRAM — native MTP plus ngram

TARGET versus NGRAM is mandatory. MTP versus MTP_NGRAM is also preserved as an explicit support/result pair. Unsupported exact model/build combinations are recorded as UNSUPPORTED, never silently deleted or source-patched into a different benchmark.

## 1Cat-vLLM STOCK

Pin the exact 1Cat wheel/runtime identity and verify the V100/SM70 backend. Record TP, max_model_len, max_num_seqs, scheduler/batch settings, KV dtype, CUDA Graph settings, attention backend and speculative configuration.

## 1Cat-vLLM plus v100-skinny

v100-skinny remains a mandatory explicit result row and is a separate runtime identity from STOCK 1Cat.

Pin both the 1Cat base identity and skinny revision. Record QPN/skinny routes, TP topology, graph settings and memory overhead.

On the current 2×V100-16GB P520, WBS 1.4 produced `FAIL_OOM_MODEL_LOAD` during QPN prepack before server boot. This terminal preflight result is preserved and the lane is not scheduled for C1/C2. Do not substitute STOCK 1Cat, TP4 results, or 2×32GB TP2 results.

## Candidate models
- Qwen3.8-27B
- Ornith 1.5 35B-A3B
- Ornith 1.5 9B
- Gemma4 26B-A4B

Every runtime/model pair requires fresh compatibility evidence.

## Artifact identity

Record repository/path, revision, quantization, file identity/size and SHA256 where practical. Same model name with different bytes is a different benchmark artifact.

## Host CUDA vs runtime CUDA

Keep separate:
- host NVIDIA driver
- host nvidia-smi CUDA compatibility
- runtime CUDA userspace
- runtime build/revision

## Cross-runtime comparisons

Hold workload objective, per-agent context, concurrency and output objective constant where possible, while disclosing weight quantization, KV, speculative implementation, scheduler/batching, prefix-cache state, template/parser and memory-management differences.

The project selects practical serving configurations, not synthetic identical-kernel comparisons.

## No historical acceptance inheritance

qwen3.8-bench and p520-inference-lab may inform implementation but never count as fresh acceptance PASS here.
