## A. Environment Identity

```text
repo HEAD (review parent): 1f036672ea42d80b6fe3ae81c290097d4afbccf4
working tree: clean before this report; main
image: kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149
runtime: actual P520 llama-server 0.3.0-dev, build 10775, commit 67a17c17c
configured full commit: 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
model SHA: a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891 (independently recomputed on P520; MATCH)
model size: 14249047104 bytes
GPU topology: 2 x Tesla V100-SXM2-16GB, 16384 MiB each; NODE; NVLink inactive; read/write P2P OK both directions
```

GPU/runtime/artifact inspections used `ssh p520` (hostname p520-llm). Model path: `/srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf`. Config pins `unsloth/gemma-4-26B-A4B-it-qat-GGUF` revision `7b92b5b28818151e8669af2e45e88d6086f490dd`. MTP artifact was not inspected.

Reviewed: docs/WBS.md, config/models/gemma4-26b-a4b.json, config/runtime-lock.json, config/profiles/runtime-lanes.json, config/profiles/topologies.json, scripts/runtime_launcher.py, scripts/run_c2_llama.py, scripts/prepare_wbs5_plan.py, scripts/run_1gpu_litellm.py, scripts/bench_harness.py, workloads/performance/v1.json. Task/source/config/raw unchanged.

## B. Binary Feature Check

| Feature | Result | Evidence |
|---|---|---|
| layer split | SUPPORTED | actual pinned --help: split-mode none/layer/row/tensor |
| tensor-split arg | SUPPORTED | actual --help: --tensor-split |
| kv-unified | SUPPORTED | actual --help: --kv-unified |
| kv-unified-per-slot | SUPPORTED | actual --help: --kv-unified-per-slot |
| b/ub | SUPPORTED | actual --help: --batch-size, --ubatch-size |
| ngram-simple | SUPPORTED | actual --help: spec-type includes none/ngram-simple |
| NGRAM defaults | MATCH | actual --help: size-n12, size-m48, min-hits1; no explicit overrides |
| CUDA Graph compile status | VERIFY_DURING_R0_STARTUP | actual libggml-cuda.so strings: USE_GRAPHS, cudaGraphInstantiate and CUDA graph call; numeric USE_GRAPHS=1 receipt unavailable |
| GGML_CUDA_DISABLE_GRAPHS | SUPPORTED | actual library contains env name; model-free container /usr/bin/env confirms value1 transmitted |

Pinned image help/version used --gpus all and no model args; GPU passthrough supplies libcuda. Safe llama-cli --list-devices identified both V100 devices. Help also confirms ctx-size/parallel/cache-type-k/v/flash-attn/jinja/reasoning/metrics/slots/no-warmup. No model loaded. `PEER_MAX_BATCH_SIZE` was not found in actual CUDA library strings: numeric value UNKNOWN. Topology evidence does not automatically PASS/FAIL R2.

## C. Candidate Validation

| Candidate | Static status | Exact diff verified? | Blocker |
|---|---|---|---|
| R0 G4-LCPP-WBS5-R0-TARGET-B512-UB128 | BLOCKED | YES: TARGET command | no shared-TP2 WBS5 performance runner |
| R1 G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128 | BLOCKED | YES: none -> ngram-simple only | same runner gap |
| R2 G4-LCPP-WBS5-R2-TARGET-B1024-UB128 | BLOCKED | YES: expected batch512 -> 1024 only; ub128 retained | launcher hardcodes b512; override absent |
| R3 G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF | VERIFY_DURING_R0_STARTUP | YES: expected Docker env only | conditional gates and absent env dispatch |

R3 Gate A: VERIFY_DURING_R0_STARTUP for numeric graph feature receipt; graph symbols and disable-env transmission confirmed. Gate B: **PENDING_MEASURED_EVIDENCE**. No R0 VRAM drift/graph instability measured; R3 remains conditional.

## D. Exact Expected Commands

R0/R1 generated in memory by runtime_launcher.build_plan. R2/R3 are exact frozen expected transformations, not implemented WBS5 candidate dispatch. Base environment is empty; only R3 adds Docker --env. Commands below were not executed.

### R0

```sh
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### R1

```sh
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type ngram-simple --jinja --reasoning off --metrics --slots --no-warmup
```

### R2

```sh
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 1024 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### R3

```sh
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --env GGML_CUDA_DISABLE_GRAPHS=1 --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

## E. Differences / Problems Found

- scripts/run_c2_llama.py selects workloads/concurrency/v2.json with no WBS5 candidate selector. prepare_wbs5_plan.py/run_1gpu_litellm.py support Ornith9B llama.cpp only, not this Gemma4 shared-TP2 track.
- runtime_launcher.llama_plan fixes b512/ub128. R2 b1024 and R3 container env lack candidate dispatch; expected transforms above are not a runnable WBS5 path.
- Actual pinned artifact/runtime/binary options match. Numeric USE_GRAPHS=1 is not proved by strings; R3 Gate B requires future measured R0 evidence.
- performance/v1.json matches workload ID V100-PERFORMANCE-C2-128K-v1, performance mode, context131072/request, output reserve4096, minimum1024/request, two independent projects A/B, temperature0/top_p1/seed520 and identifier diversification. Existing shared runner does not select it. No workload run.

## F. Final Pre-Inference Verdict

```text
R0: BLOCKED
R1: BLOCKED
R2: BLOCKED
R3: VERIFY_DURING_R0_STARTUP
GPU MEASURED INFERENCE EXECUTED: NO
```
