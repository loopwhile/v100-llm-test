# Runtime Policy

This repository compares pinned, reproducible V100/SM70 serving lanes. Mutable labels such as `latest` may be used for discovery, but not as the only benchmark identity.

## 1. Mandatory runtime families

### llama.cpp

Primary V100 lane: a pinned CUDA/SM70 build, with `kyuz0/nvidia-v100-ai-toolboxes` as the preferred reproducible packaging source unless the WBS later pins a different explicitly approved build.

Record:

- image tag and digest when containerized;
- actual llama.cpp version/commit;
- CUDA userspace identity;
- exact launch command;
- multi-GPU topology;
- model artifact hash;
- KV format;
- speculative mode.

**ngram is mandatory in the llama.cpp test program.** For every llama.cpp candidate, the test matrix must include the declared ngram lane (normally MTP+ngram where that model uses native MTP). If the exact pinned model/build does not support it, record `UNSUPPORTED`; do not silently delete the lane or source-patch it into a different benchmark.

### 1Cat-vLLM stock

Pin the exact 1Cat-vLLM revision/build/container or wheel identity and verify the V100/SM70 backend actually used. Record TP, `max_model_len`, `max_num_seqs`, scheduler/batch settings, KV dtype, CUDA Graph settings, attention backend and speculative configuration.

### 1Cat-vLLM + v100-skinny

**v100-skinny is a mandatory test lane, not an optional optimization.**

Pin both the 1Cat-vLLM base identity and the v100-skinny revision/patch identity. Record which QPN/skinny paths are active, TP topology, prepack/graph settings and any memory overhead that changes available KV capacity.

A skinny failure on 2×16GB is still a valid benchmark result. Preserve `FAIL_OOM`, `FAIL_CAPACITY`, `UNSUPPORTED` or other observed verdict rather than substituting stock 1Cat.

## 2. Candidate models

Current model scope:

- Qwen3.8-27B
- Ornith 1.5 35B-A3B
- Ornith 1.5 9B
- Gemma4 26B-A4B

Each runtime/model pair gets a fresh compatibility check. Do not infer support from another model or an older repository run.

## 3. Artifact identity

Record repository/path, revision, quantization, file identity/size and SHA256 where practical. Draft/MTP artifacts receive their own identity.

Same model name with different bytes is a different benchmark artifact.

## 4. Host CUDA vs runtime CUDA

Keep these separate:

- host NVIDIA driver;
- CUDA compatibility shown by host `nvidia-smi`;
- container/runtime CUDA userspace;
- runtime build/revision.

## 5. Cross-runtime comparisons

Do not force implementation details to be artificially identical. Hold the workload objective, per-agent context target, concurrency and output objective constant where possible, while disclosing:

- weight quantization;
- KV format;
- speculative implementation;
- scheduler/batching;
- prefix-cache state;
- chat/tool/reasoning configuration;
- memory-management differences.

The project selects practical serving configurations, not a synthetic claim that all runtimes execute identical kernels.

## 6. No historical acceptance inheritance

Results from `qwen3.8-bench` or `p520-inference-lab` may inform implementation, but they do not count as a fresh `v100-llm-test` acceptance PASS. This repository generates its own runtime identity, raw evidence and verdicts.
