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

## 8B~8D remediation result — 2026-09-28

8A 관찰/과거 verdict는 위에 보존한다. 아래는 새 runner 구현 이후의 준비 상태이며 measured PASS를 뜻하지 않는다.

- Runner readiness: **READY_FOR_PRE_RUN_VALIDATION**. `scripts/run_wbs5.py` 명시적 track/candidate dispatch; 기본 동작은 dry-plan이다. 기존 WBS3 runner의 concurrency/v2 기본값은 유지한다.
- Frozen guard: pinned input SHA와 normalized effective argv/env OFAT allowlist, final worker config/command drift를 검사하며 위반은 `FROZEN_DELTA_MISMATCH`로 중단한다. context 131072/request, independent A/B, reserve4096/min1024, temp0/top_p1/seed520을 유지한다.
- Identity/evidence: candidate ID/run label/workload SHA/model+runtime+artifact hash, exact argv 및 host/container environment receipt; fresh raw exclusive creation, telemetry/post-health/output integrity/total output tokens 경로를 연결했다. 반복/confirm/실패 retry를 자동 실행하지 않는다.
- Metric remediation: 기존 TTFT/prefill/per-request decode/mean decode/aggregate decode/end-to-end TPS/batch wall 산식 유지. 새 WBS5 run만 graph-evidence.json, slot-progress JSONL/JSON, speculative counters/ratio를 저장한다. missing/ambiguous/reset counters와 unavailable slot fields는 UNKNOWN/null; raw server log는 보존한다.
- Remaining runtime-only unknown: **VERIFY_AT_STARTUP / VERIFY_DURING_MEASURED_RUN** — graph reuse, batch1024 VRAM fit, 실제 graph-off 효과.
- Remaining blocker/gate: R3는 CONDITIONAL_PENDING_GATE: Gate B의 R0 VRAM upward drift/graph instability와 graph support evidence가 필요하다.
- BLOCKED_BY_HARNESS: **없음**. Pre-run ChatGPT Ready: **YES** (host approval/gate가 남아 있는 후보는 measured admission 금지).
- Tests: 전체 `pytest` **146 passed, 25 subtests passed**; WBS5 offline 24 tests 포함. `scripts/validate_repo.py`: **Repository contract: PASS**. Python AST/JSON validation 및 git diff --check PASS. 실제 HTTP/GPU를 쓰는 inference test는 실행하지 않았다.
- Measured inference executed: **NO**. GPU server startup/model load/G0/128K request/benchmark/설치/host 설정 변경도 실행하지 않았다.

| Candidate | Run label | 8C state | Dry plan |
|---|---|---|---|
| `G4-LCPP-WBS5-R0-TARGET-B512-UB128` | `screening-1` | `STATIC_READY` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/candidate-plan.json) |
| `G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128` | `screening-1` | `STATIC_READY` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001/candidate-plan.json) |
| `G4-LCPP-WBS5-R2-TARGET-B1024-UB128` | `screening-1` | `STATIC_READY` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001/candidate-plan.json) |
| `G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF` | `screening-1` | `CONDITIONAL_PENDING_GATE` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-GEMMA-LLAMA-R3-PERF-20260928-001/candidate-plan.json) |

공통 구현/guard/evidence 및 8D receipt 설명: [WBS5 preparation report](WBS-5-preparation-readiness.md). 다음 단계는 ChatGPT의 pre-run final validation이며 자동 measured 실행으로 이어지지 않는다.

## 5.3.4.6 Measured track result review — 2026-09-29

이 섹션은 위 pre-inference/static review 이후 실제 publication된 WBS5 raw를 대상으로 한 non-executable track review다. 새로운 GPU inference나 candidate 생성은 수행하지 않았다.

| Candidate | TTFT | Prefill | Mean decode | Aggregate decode | E2E output | Batch wall | Peak VRAM GPU0/GPU1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| R0 TARGET b512/ub128 | 439.10 s | 359.09 tok/s | 22.54 tok/s | 7.54 tok/s | 4.78 tok/s | 671.54 s | 10,039 / 10,537 MiB |
| R1 NGRAM default | 448.49 s | 353.18 tok/s | 21.48 tok/s | 7.10 tok/s | 4.52 tok/s | 685.38 s | 10,039 / 10,607 MiB |
| R2 TARGET b1024/ub128 | 440.10 s | 355.46 tok/s | 22.28 tok/s | 7.60 tok/s | 4.77 tok/s | 670.94 s | 10,039 / 10,537 MiB |

- 세 measured run 모두 `PASS_C2_ACTIVE`, active overlap true, queue-only false, output minimum 충족, post-health healthy.
- R1은 NGRAM draft 144 / accepted 54 / acceptance 37.5%였지만 R0 대비 mean decode -4.69%, aggregate -5.92%, E2E -5.56%, wall +2.06%로 실효 성능이 악화됐다. **R1 branch 종료**.
- R2는 R0 대비 TTFT +0.23%, prefill -1.01%, mean decode -1.15%, aggregate +0.72%, E2E -0.22%, wall -0.09%다. intended TTFT/prefill improvement가 없고 차이는 3%보다 훨씬 작아 noise 가능성을 명시한다. 자동 confirm/repetition은 요구하지 않는다. **R2 branch 종료**.
- R0 graph reuse 4,425회에도 VRAM upward drift나 graph-related instability가 없어 Gate B는 `NOT_TRIGGERED`; **R3 GRAPH-OFF는 정상 SKIP**.
- Power/temp/clock envelope는 세 run이 유사했다. R0/R1/R2 GPU0 max power 169.00/169.35/168.88 W, GPU1 161.46/159.58/161.93 W; max temp는 각각 GPU0 61/60/61 C, GPU1 58/58/58 C; max SM clock 1,200 MHz, memory clock 877 MHz.
- 요청별 decode 비대칭은 R0 약 41.26/3.82 tok/s, R2 약 40.81/3.75 tok/s로 유지되어 b1024가 기존 layer-split C2 topology behavior를 바꾼 evidence는 없다.
- **Final recipe 승격 대상으로 남는 configuration은 R0 `G4-LCPP-WBS5-R0-TARGET-B512-UB128` 하나다.** 실제 recipe status publication은 WBS 5.5에서 처리하며 이 review 자체에서 `VALIDATED_RECIPE`를 선행 선언하지 않는다.

