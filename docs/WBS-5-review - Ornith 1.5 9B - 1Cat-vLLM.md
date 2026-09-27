# Ornith 1.5 9B / 1Cat-vLLM WBS5 static verification

## 1. Overall result

**READY_WITH_STATIC_UNKNOWNS**. Installed artifact/runtime/native capability and frozen command deltas are statically consistent. This is not G0 semantic PASS or WBS5 execution readiness. The required separate G0 must run before any future WBS5 measured candidate; it was not performed. Current runner lacks frozen R1/R2/R3 dispatch and performance workload selection. These are blockers before WBS5 integration, not evidence that the checkpoint failed startup in this task.

Review parent HEAD: `a50952220fbc3e2af17e3e4563776f51ff844494`, main, clean before this report. Runtime/GPU/model inspections used `ssh p520` -> `p520-llm`. No subagent used for this review. No model/weight load, warmup, kernel, server startup, graph capture or requests executed. Task/source/config/historical raw unchanged.

## 2. Verification table

Installed source root below is `/home/loopwhile/qwen3.8-bench-runtime/venv/lib/python3.12/site-packages/`; source references are to this installed copy, not upstream.

| Check | Expected | Observed | Status | Evidence path/source |
|---|---|---|---|---|
| Python | 3.12.x | 3.12.14 | PASS | venv/bin/python, sys.version |
| 1Cat | 1.5.0 | distribution1cat-vllm1.5.0, cp312 wheel direct_url | PASS | 1cat_vllm-1.5.0.dist-info |
| Wheel SHA | 2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b | same, recomputed on P520 in preceding track review | PASS | /home/loopwhile/1cat-vllm-wheel/1cat_vllm-1.5.0-cp312-cp312-linux_x86_64.whl |
| Installed tree identical to wheel | not assumed | package metadata/selected hashes only, no full-tree comparison | UNKNOWN | direct_url has no archive hash |
| torch | 2.10.0+cu128 | metadata2.10.0, torch/version.py2.10.0+cu128/cuda12.8 | PASS | file read, no torch import |
| CUDA userspace | 12.8 | nvidia-cuda-runtime-cu12 12.8.90; cublas12.8.4.1; NCCL2.27.5 | PASS | distribution metadata |
| Flash-V100 | 1.2.0 | __init__.py1.2.0; separate distribution metadata absent | PASS | flash_attn_v100 package exists |
| GPU | two V100 SXM2 16GB, SM70 | name match, 16384MiB each, compute_cap7.0, 0MiB used at receipt | PASS | actual P520 nvidia-smi; driver580.178.04 |
| Model repo/revision | ornith-ai/Ornith-1.5-9B-NVFP4 / 155f200d85ad58464571c77d5e1122ea5d419d7b | HF download receipts for config/model/tokenizer/hf_quant all match revision | PASS | /srv/models/ornith-1.5-9b-nvfp4/.cache/huggingface/download/*.metadata |
| Model content SHA | downloaded model receipt | 1cdf915951ce890af09973dba6403a457c6098f31e8613225eef0204c7dd4caa, full-file recomputation matches HF receipt | PASS | model.safetensors, 8818103892 bytes |
| Config identity | actual metadata | config84bd143f937ebe7f2eb26fe251c2219d318f1945367d8b332ad74b3a80fdd057; tokenizer_config316230d6a809701f4db5ea8f8fc862bc3a6f3229c937c174e674ff3ca0a64ac8 | PASS | SHA256 independently computed; no supplied expected metadata digest claimed |
| Quantization | NVFP4 supported checkpoint | modelopt MIXED_PRECISION: MLP/lm_head W4A16_NVFP4 group16 plus FP8 attention projections; not uniformly NVFP4 | PASS | config.json + hf_quant_config.json, SHA3316235a83349627194f92a27f226bad95e173fc08b741eab681fd6e797adef3 |
| Architecture/hybrid | Qwen3.5 + GDN | Qwen3_5ForConditionalGeneration/qwen3_5; text32layers:24linear_attention +8full_attention; linear head128 | PASS | config.json text_config.layer_types |
| Native MTP | metadata/weights | text mtp_num_hidden_layers1; safetensors JSON header contains mtp.fc and mtp.layers.0 attention/MLP/norm weights | PASS | single model.safetensors bounded header read only, no index file required |
| Exact effective n_predict | source-derived | native layer count1; outer config has no mtp_num_hidden_layers; hf_config_override outer getter can produce n_predictNone | UNKNOWN | speculative.py:612; qwen3_5_mtp.py:135; see below |
| SM70 NVFP4 source | exact-SM70 support | ModelOpt min capability70 under backend gate, preparation/apply paths exist | PASS | modelopt.py:1091,1187,1370,1382; sm70_turbomind.py |
| Required native API | SM70 NVFP4 operators | _C.abi3.so strings include nvfp4_sm70_prepare and QPN SM70 symbols | PASS | actual binary SHA c35b76ca723ec1a6907e31b2f0fe4f96c2e1b212603e04b976f9a48b85d0916a |
| Actual selected route | TurboMind W4A16 for eligible NVFP4 layers | source expectation, no startup route receipt | UNKNOWN | source capability differs from future measured hit |
| Target backend/KV | FLASH_ATTN_V100 / float16 | plan exact; CLI/source support | PASS | runtime_launcher.onecat_plan + pinned help |
| Prefix caching/mamba | True / align | server+linear defaults retained, no disable override | PASS | arg_utils.py:1776-1787 |
| MTP greedy/local argmax | greedy / True | explicit MTP defaults apply on SM70; explicit TRITON_ATTN retained | PASS | arg_utils.py:1828,1852 |
| Drafter graph default | speculative eager absent => False | create_speculative_config sets enforce_eagerFalse; actual drafter graph activation also depends on target/dispatcher mode | PASS | arg_utils.py:1725; llm_base_proposer.py:557-576; worker:11148 |
| R1 MBT8192 | parser accepts + only MBT changes | exact in-memory diff verified; no candidate override currently implemented | PASS | arg_utils scheduler CLI; expected commands below |
| R2 target graph | removing target eager | generic and SM70 graph branches reachable; capture/replay unexecuted | UNKNOWN | config/vllm.py:1411,1640; graph analysis below |
| R3 MTP2 | positive depth permitted / repeated layer | positive parser field; modulo validation rejects only nonmultiples of non-null n_predict;2 divisible by1; actual layer reused | PASS | speculative.py:132,950-965; qwen3_5_mtp.py:213 |
| Common-prefix token length | prefix behavior audited | Project A/B differ in title/id/sections; exact tokenized common prefix unavailable without tokenizer endpoint | UNKNOWN | NEEDS FUTURE RUNTIME CHECK |
| G0 oracle | pre-registered v2 ProjectB race | files exist and explicit check -> await asyncio.sleep(0) -> heappop race retained | PASS | concurrency/v2.json + v2-ground-truth.json |
| G0 semantic requalification | required before WBS5 | not executed (inference prohibited) | UNKNOWN | future separate admission run |

Flash native SHA (same installed runtime inspected directly): flash_attn_v100_cuda.so `16812336d72bafdd09c6f6ad857412e07ef807602972946e848c469f7f9158e5`; paged_kv_utils.so `bc81a9d7919f13a2997d654ae863d047c24e7e3c64ba4c05cb7a179de4ef35f5`. FlashQLA package0.1.0 and native strided.so SHA `b491df95a321a0b6a5cbacd114752021a5c56198c994de69f10f560393470f64`; TileLang0.1.10. No whole-directory model hash invented.

### SM70 route and default analysis

VLLM_SM70_NVFP4_TURBOMIND effective default1. `sm70_turbomind.is_exact_sm70_cuda` requires CUDA tensor and capability(7,0), `prepare_nvfp4_linear` requires torch.ops._C.nvfp4_sm70_prepare; actual binary symbol exists. ModelOpt `_try_prepare_sm70_modelopt_nvfp4` prepares then apply_prepared_linear dispatches weight-only NVFP4 with half activations. This is the expected R0 route for eligible W4A16_NVFP4 layers. Mixed FP8 layers have separate routes. Operator registration/import/weight preparation were not executed, so native symbol evidence is not model compatibility PASS.

GDN prefill baseline ORIGINAL_PREFILL0 is launcher default; GDN decode FlashQLA default1 (envs.py:3254), subject to platform/dtype/head/import checks. P520 inspected ambient performance envs and VLLM_1CAT_* flags unset; auto-MTP enable/disable flags default0. Explicit MTP1 prevents implicit MTP4. Prefix caching remains enabled. No prefix cache toggle added.

Native MTP vs n_predict: actual text_config defines one layer; installed qwen3_5_mtp uses hf_text_config.mtp_num_hidden_layers and spec_step_idx % num_mtp_layers, so MTP2 reuses layer0. Installed speculative.hf_config_override for qwen3_5 reads the outer hf_config.mtp_num_hidden_layers, while this checkpoint stores it only inside text_config. Installed Transformers base __getattribute__ maps named attributes but does not generally forward to text_config; Qwen config has no custom __getattr__ found. Therefore n_predict=1 cannot be certified from raw nested metadata alone; outer-getter path yields None unless a separate conversion intervenes. The validation only checks divisibility when n_predict is non-null; explicit2 is allowed for both None and1. Future resolved config should record actual n_predict. Warning branch for depth>1: speculative.py:894-902 says multiple forwards on the same MTP layer may lower acceptance. No correctness/performance claim made.

### Capture shapes and automatic deltas

SM70 MTP defaults run in arg_utils.py before VllmConfig. With default split-draft flag0, base shapes [1,2,4,8,9] are unioned with `(depth+1)*n_requests` for1..max_num_seqs. For C2:

| Candidate | depth | decode_query_len | verifier production shapes | default configured capture list |
|---|---|---|---|---|
| R0/R1 |1|2|2,4|[1,2,4,8,9]|
| R2 |1|2|2,4|[1,2,4,8,9]|
| R3 |2|3|3,6|[1,2,3,4,6,8,9]|

Default split flag is0; the alternate helper exists but is not enabled or added as candidate. R1 MBT8192 does not enter this verifier shape formula; depth/TP/sequences/backends/KV/eager are unchanged. Generic compilation range upper bound depends on MBT (config/vllm.py:2595), so changing MBT can affect derived scheduler/compile metadata without changing the frozen axis.

R0/R1/R3 target eager forces global target compilation NONE/graph NONE (vllm.py:1411). Drafter speculative.enforce_eagerFalse is an eligibility default, **not proof of an independent graph capture while target graph NONE**: proposer initialization maps target mixed-modeNONE to drafterNONE and worker dummy path checks target runtime mode. R2 removes only target eager, so the graph branch enables VLLM_COMPILE/FULL_AND_PIECEWISE and PIECEWISE drafter dispatcher. Actual graph replay/hit is a future check; do not claim R0 drafter captured from the default flag alone.

Automatic R2 derived settings under current SM70 policy: compile graph env1; VLLM_COMPILE/FULL_AND_PIECEWISE; capture list above/max9; ind_graph_partitionFalse; RMSNorm/fused_add priorities[vllm_c,native]; eliminate_noops if enabled; MQ chunks64; memory graph estimate0; LM_HEAD_TOP1=0; AOT1; disable compile cache1; combo_kernels/benchmark_combo_kernelTrue. MTP defaults greedy/local argmax/fast_moe_cold_start/capture sizes are common to all candidates, so they are not independently changed. No automatic smallq override is needed unless computed query length exceeds the existing default. Full effective child config/env must be captured at future startup.

## 3. Exact future command table

| Candidate ID | Core delta |
|---|---|
| ORN15-9B-1CAT-WBS5-R0-BASELINE | baseline |
| ORN15-9B-1CAT-WBS5-R1-MBT8192 | MBT4096 ->8192 |
| ORN15-9B-1CAT-WBS5-R2-TARGET-GRAPH | remove target --enforce-eager |
| ORN15-9B-1CAT-WBS5-R3-MTP2 | speculative depth1 ->2 |

Common environment: CUDA_VISIBLE_DEVICES=0,1; VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0. Launcher also adds PYTHONPATH=<P520 repo>/scripts/runtime_hooks, preserving any ambient suffix; no concrete remote checkout chosen or changed in this review. This hook and full inherited env must remain identical for all candidates. No command below was executed.

### R0

```sh
CUDA_VISIBLE_DEVICES=0,1 VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.90 --enforce-eager --speculative-config '{"method":"mtp","num_speculative_tokens":1,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

### R1

```sh
CUDA_VISIBLE_DEVICES=0,1 VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 8192 --gpu-memory-utilization 0.90 --enforce-eager --speculative-config '{"method":"mtp","num_speculative_tokens":1,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

### R2

```sh
CUDA_VISIBLE_DEVICES=0,1 VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.90 --speculative-config '{"method":"mtp","num_speculative_tokens":1,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

### R3

```sh
CUDA_VISIBLE_DEVICES=0,1 VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.90 --enforce-eager --speculative-config '{"method":"mtp","num_speculative_tokens":2,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

## 4. Normalized command/config diff

In-memory runtime_launcher plan comparisons verified:

- R1 differs only max-num-batched-tokens4096->8192. Depth1, eager, TP2, seq2, len131072, float16KV, attention backends remain.
- R2 differs only removal of target --enforce-eager. Spec JSON is byte-identical: methodmtp, num_speculative_tokens1, attention_backendTRITON_ATTN. All other explicit args/env unchanged; graph-derived deltas are listed above.
- R3 differs only num_speculative_tokens1->2 inside speculative JSON; target eager and MBT4096 are restored to baseline. Derived query length/shape changes follow depth axis, not extra candidates.

Current runtime_launcher emits R0 but hardcodes MBT4096/eager; it lacks dispatch for R1/R2/R3. Existing run_c2_onecat selects WBS3 concurrency/v2, not performance/v1. No executable WBS5 candidate integration was claimed from these textual transforms.

### Prefix-cache confound

build_128k_workload.render starts project-specific title/id, adds independent anchors, section IDs and diversified identifiers. performance/v1 diversification isTrue. calibrate sizes content by adapter tokenizer endpoint, reserves4096, records raw prompt SHA and prompt count, checks independent message hashes. Different hashes do not prove a zero-length common token prefix; chat wrappers can be shared. Exact common-prefix token length: **NEEDS FUTURE RUNTIME CHECK**. Prefix cache remains enabled as frozen behavior.

### Metric definitions

bench_harness.stream_complete/worker/aggregate are authoritative:

- TTFT_ms = (first nonempty streamed content timestamp - HTTP stream start)*1000. Submission timestamp is separate.
- Per-request decode TPS uses runtime timings.predicted_per_second if present; otherwise actual completion token count/(stream end - first content), when output token count valid.
- Prefill TPS uses timings.prompt_per_second; fallback prompt token count/(TTFT_ms/1000), an approximation including request/first-token overhead.
- mean_request_decode_tps = arithmetic mean of available decode TPS for runtime-completed records.
- aggregate_decode_tps = sum actual output tokens across runtime-completed records/(latest stream end - earliest first content).
- end_to_end_output_tps = same summed tokens/batch_wall_s.
- batch_wall_s = latest record terminal_s - earliest submitted_s (includes harness tail), not simply sum/mean request durations.

**mean_request_decode_tps * concurrency is not generally equal to aggregate_decode_tps**: request intervals differ, output lengths differ, and runtime-provided decode timing may differ from stream timing. Preserve current formulas; don't rename aggregate to mean*C2. Runtime-completed records can include output semantic failures; output integrity is reported separately.

## 5. Future model/runtime-only unknowns

Actual native API registration/route, model load and VRAM fit, effective n_predict, graph capture/replay, acceptance/correctness of MTP2, exact common-prefix token length and actual metric/route counters remain unproved. No fake PASS or alternative optimization candidate supplied.

## 6. Admission gate and blockers

Required separate G0 uses pre-registered oracle, not performance nonempty criterion. Frozen file receipts:

| File | SHA256 |
|---|---|
| workloads/concurrency/v2.json | ab6ac578301c8f48700d5a50c808e1bfb42538f186c50a82168509215dc9e479 |
| workloads/concurrency/v2-ground-truth.json | 221d0606a19b08e223d3eecac59ff99da151441dace3f5937ebed29a275ed7bb |
| scripts/build_128k_workload.py | 969d4e9882b14e9cc739dc37c72047996b5db55841e852c6460f5167813648e0 |

Project B still seeds JobQueue.pop nonempty check -> explicit await asyncio.sleep(0) -> heapq.heappop race; with one job/two workers the second pop may raise IndexError. Ground truth requires correct mechanism/reproduction and grounded fix. G0 not executed here. No artifact/version mismatch found that statically prevents preparing G0; exact metadata mapping and route are registered startup unknowns. Before WBS5 measured execution: G0 semantic requalification must PASS separately; frozen candidate dispatch/performance workload and effective env/config receipts must be integrated; fresh raw IDs and counters preserved. Existing benchmark results are not modified or relabeled.

GPU MEASURED INFERENCE EXECUTED: NO

## 8B~8D remediation result — 2026-09-28

8A 관찰/과거 verdict는 위에 보존한다. 아래는 새 runner 구현 이후의 준비 상태이며 measured PASS를 뜻하지 않는다.

- Runner readiness: **READY_FOR_PRE_RUN_VALIDATION**. `scripts/run_wbs5.py` 명시적 track/candidate dispatch; 기본 동작은 dry-plan이다. 기존 WBS3 runner의 concurrency/v2 기본값은 유지한다.
- Frozen guard: pinned input SHA와 normalized effective argv/env OFAT allowlist, final worker config/command drift를 검사하며 위반은 `FROZEN_DELTA_MISMATCH`로 중단한다. context 131072/request, independent A/B, reserve4096/min1024, temp0/top_p1/seed520을 유지한다.
- Identity/evidence: candidate ID/run label/workload SHA/model+runtime+artifact hash, exact argv 및 host/container environment receipt; fresh raw exclusive creation, telemetry/post-health/output integrity/total output tokens 경로를 연결했다. 반복/confirm/실패 retry를 자동 실행하지 않는다.
- Metric remediation: 기존 TTFT/prefill/per-request decode/mean decode/aggregate decode/end-to-end TPS/batch wall 산식 유지. 새 WBS5 run만 graph-evidence.json, slot-progress JSONL/JSON, speculative counters/ratio를 저장한다. missing/ambiguous/reset counters와 unavailable slot fields는 UNKNOWN/null; raw server log는 보존한다.
- Remaining runtime-only unknown: **VERIFY_AT_STARTUP / VERIFY_DURING_MEASURED_RUN** — target/drafter graph shapes, MTP correctness/acceptance, VRAM fit 및 semantic correctness.
- Remaining blocker/gate: R0~R3 모두 CONDITIONAL_PENDING_GATE: WBS3 Project A/B G0 semantic requalification PASS receipt가 필요하다. G0 inference 미실행.
- BLOCKED_BY_HARNESS: **없음**. Pre-run ChatGPT Ready: **YES** (host approval/gate가 남아 있는 후보는 measured admission 금지).
- Tests: 전체 `pytest` **146 passed, 25 subtests passed**; WBS5 offline 24 tests 포함. `scripts/validate_repo.py`: **Repository contract: PASS**. Python AST/JSON validation 및 git diff --check PASS. 실제 HTTP/GPU를 쓰는 inference test는 실행하지 않았다.
- Measured inference executed: **NO**. GPU server startup/model load/G0/128K request/benchmark/설치/host 설정 변경도 실행하지 않았다.

| Candidate | Run label | 8C state | Dry plan |
|---|---|---|---|
| `ORN15-9B-1CAT-WBS5-R0-BASELINE` | `screening-1` | `CONDITIONAL_PENDING_GATE` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-ORNITH9-ONECAT-R0-PERF-20260928-001/candidate-plan.json) |
| `ORN15-9B-1CAT-WBS5-R1-MBT8192` | `screening-1` | `CONDITIONAL_PENDING_GATE` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-ORNITH9-ONECAT-R1-PERF-20260928-001/candidate-plan.json) |
| `ORN15-9B-1CAT-WBS5-R2-TARGET-GRAPH` | `screening-1` | `CONDITIONAL_PENDING_GATE` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-ORNITH9-ONECAT-R2-PERF-20260928-001/candidate-plan.json) |
| `ORN15-9B-1CAT-WBS5-R3-MTP2` | `screening-1` | `CONDITIONAL_PENDING_GATE` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-ORNITH9-ONECAT-R3-PERF-20260928-001/candidate-plan.json) |

공통 구현/guard/evidence 및 8D receipt 설명: [WBS5 preparation report](WBS-5-preparation-readiness.md). 다음 단계는 ChatGPT의 pre-run final validation이며 자동 measured 실행으로 이어지지 않는다.
