# Qwen3.8-27B / 1Cat-vLLM WBS5 local feasibility

Review parent HEAD: `3c758c7ae2c5940c60770dbfb0bf3b7261ed06e7`, main, clean before this report. Actual runtime/model host: `ssh p520` -> `p520-llm`; repository inspection and command construction on laptop. No model startup, CUDA kernels, JIT, capture, inference or package/source changes. User explicitly requested separate result commits/pushes; task's prohibition on new commits is overridden only for these reports.

| Candidate | Local verdict | Exact supported delta | Blocking issue | Runtime-only uncertainty |
|---|---|---|---|---|
| R0-E4M3-128K-SEMANTIC-BASELINE | SUPPORTED | frozen C1 eager E4M3 baseline | no WBS5 candidate dispatch; revision receipt incomplete | resolved cache block alignment, 128K semantics/VRAM |
| R1-E4M3-128K-CUDAGRAPH-C1 | VERIFY_AT_RUNTIME | remove eager + graph capture sizes [1] within graph axis | runner override and resolved graph config must be recorded | actual capture/replay, compilation and TP2 collectives |
| R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL | VERIFY_AT_RUNTIME | ORIGINAL_PREFILL 0 -> 1 only | no nvcc on current PATH/CUDA_HOME; existing runner resets env0 | JIT availability/cache and exact route execution |
| R3-E5M2-128K-KV-ROUTE | SUPPORTED | explicit fp8_e4m3 -> fp8_e5m2 only | existing Qwen runner resets E4M3 | exact native decode route and correctness |

SUPPORTED here means parser/source capability, not measured PASS or an integrated WBS5 runner.

## A. Runtime receipt

Authoritative installed root: `/home/loopwhile/qwen3.8-bench-runtime/venv/lib/python3.12/site-packages/`. Inspected installed files directly via SSH and copied those same bytes to /tmp for text/binary inspection; no upstream source substituted.

| Item | Observed |
|---|---|
| Python | 3.12.14; /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python |
| 1Cat | distribution 1cat-vllm 1.5.0, cp312 wheel; direct_url points to /home/loopwhile/1cat-vllm-wheel/1cat_vllm-1.5.0-cp312-cp312-linux_x86_64.whl |
| Wheel SHA | 2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b, independently recomputed in this review sequence on P520 |
| torch | metadata2.10.0; actual torch/version.py 2.10.0+cu128, cuda12.8; no torch import/CUDA invocation |
| CUDA userspace | nvidia-cuda-runtime-cu12 12.8.90, cublas12.8.4.1, nccl2.27.5 |
| Flash-V100 | flash_attn_v100/__init__.py 1.2.0; no separate flash-attn-v100 distribution metadata, package exists |
| FlashQLA | flash_qla/__init__.py 0.1.0; no separate flash-qla distribution metadata, package exists |
| TileLang | 0.1.10, tilelang-0.1.10.dist-info and source files present |
| GPU | P520 2 x V100-SXM2-16GB, 16384MiB each, SM70; driver580.178.04; nvidia-smi CUDA13.0 is driver compatibility, not userspace version |

Native files (relative to installed root), independently hashed:

| File | SHA256 |
|---|---|
| flash_attn_v100/flash_attn_v100_cuda.cpython-312-x86_64-linux-gnu.so | 16812336d72bafdd09c6f6ad857412e07ef807602972946e848c469f7f9158e5 |
| flash_attn_v100/paged_kv_utils.cpython-312-x86_64-linux-gnu.so | bc81a9d7919f13a2997d654ae863d047c24e7e3c64ba4c05cb7a179de4ef35f5 |
| flash_qla/ops/gated_delta_rule/chunk/sm70/flash_qla_sm70_gdn_strided.so | b491df95a321a0b6a5cbacd114752021a5c56198c994de69f10f560393470f64 |

Installed source fingerprints (no claim that installed tree is untouched merely from wheel identity):

| Installed source | SHA256 |
|---|---|
| vllm/config/vllm.py | 42344a6fadeedc1ef3579c60594d1b18ee2ebdbc5c171b2772e9f4f941cc98a9 |
| vllm/v1/attention/backends/gdn_attn.py | 0fc725023e6c5435b480a2bf51c61d21a8f3562cd2bce52fdd869f447aa981a8 |
| vllm/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py | 5f62fa805fdb56502c54b34a5a59619911e7ecc0c199641e39dcbe3372e68202 |
| vllm/v1/attention/backends/flash_attn_v100.py | a783e55be54b1c71f403f647ec095367a6a978ee553e7471188738bf352c12b3 |

Model: `/srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4`. Config SHA `4a602978ea802d91171d3c5a8b99c5a23900ed474289133d9d0193a35ce3206b`; index SHA `eee26dbb894969febd90ea21f29c10adc660267c47eeff63e08ef45611761046`. Five shard files exist; index total tensor bytes20559281336. Config architecture Qwen3_5ForConditionalGeneration, model_type qwen3_5 / text qwen3_5_text; max_position_embeddings262144; text mtp_num_hidden_layers1. **Does config.json contain speculators_config? NO** (absent, not confused with MTP layers). Quantization compressed-tensors/nvfp4-pack-quantized, 4bit/group16 weights and input activation metadata. kv_cache_scheme=null; index has no k_scale/v_scale/kv_scale keys. Mamba SSM metadata float32.

Repo config pins QUASAR-QAT/Qwen3.8-27B-QUASAR-NVFP4 revision15d2e47bffe5d8ad23928879f8f7d2f74909e259. This directory has no HF download revision receipts found; queried provisioning files yielded no matching revision entry. Therefore exact revision association is UNKNOWN, not falsely certified from model path. Actual hashes below identify the current shards independently.

| Safetensors file | Actual P520 SHA256 |
|---|---|
| model-00001-of-00005.safetensors | 54d83c1d36631de231876217a8e0c2483eccee8746369a482b79442bdfc5d958 |
| model-00002-of-00005.safetensors | bb5c367ac5ba8b2ab68f07b9719f1c3ac528ada98c26523be6e2c07f82e299bc |
| model-00003-of-00005.safetensors | 6bfa358557579f538682984a667e243a72ab361d50c583fbf06ba3148653fda1 |
| model-00004-of-00005.safetensors | 260822c66711e7fbd9df0f96b0da0b54b01c2bd77612911885b33f88f18003d7 |
| model-00005-of-00005.safetensors | 08e4c9bcd8ca371240cae47c98e5e1a499a14caeab5ee2ca4a0a07c24c69a24b |

These were recomputed from full files; no trusted revision-bound expected shard hash was supplied, so identity is recorded without asserting MATCH to an unknown manifest.

## B. Frozen invariant receipt

TP2, CUDA_VISIBLE_DEVICES0,1, dtypehalf (overrides checkpoint bfloat16 activation metadata), FLASH_ATTN_V100, LM-only, max-len131072, max-seqs1, MBT2048, util0.92, partition256, target-only with no speculative CLI/config. Pinned CLI/source contains all these settings; `vllm/config/cache.py` supports explicit E4M3/E5M2. `engine/arg_utils.py:1955` calls maybe_override_with_speculators; `transformers_utils/config.py:637-642` returns unchanged values when speculators_config absent. This checkpoint cannot auto-enable speculation by that path merely because mtp_num_hidden_layers=1.

Defaults from actual source:

- parallel.py:192,198,200: disable_custom_all_reduce=False, enable_dbo=False, ubatch_size=0. Actual communicator admission can disable custom reduction if unsupported/P2P fails. TP2 PCIe is not the >2 PCIe restriction; NODE/P2P receipts are not collective execution proof.
- envs.py:3423: effective VLLM_SKIP_P2P_CHECK default **1**, despite type declaration False. VLLM_DISABLE_PYNCCL defaultFalse; NCCL overrides absent from inspected shell/services. No P2P tests or collectives executed.
- arg_utils.py:1776-1787: server + linear attention defaults prefix cachingTrue and mamba_cache_modealign. Launcher has no disable override. Frozen behavior retained.
- R1 graph CLI key: `--compilation-config '{"cudagraph_capture_sizes":[1]}'` (also --cudagraph-capture-sizes1 exists). CUDAGraphMode enum supports NONE/PIECEWISE/FULL/FULL_DECODE_ONLY/FULL_AND_PIECEWISE; these are not interchangeable choices for this frozen run. Under unchanged SM70 Flash-V100 default policy, removing eager selects CompilationMode.VLLM_COMPILE and **FULL_AND_PIECEWISE**, not arbitrary FULL. config/vllm.py:1640-1810 forces that policy; capture_sizes explicitly [1] is retained. GDN admits decode-only FULL plus PIECEWISE mixed/prefill. Its metadata backend declares UNIFORM_BATCH at gdn_attn.py:722.
- GDN decode_cudagraph_max_bs = max_num_seqs * (num_spec_state_tokens + 1), clamped to max_capture_size (gdn_attn.py:764-772). target-only C1 => 1*(0+1)=1, so [1] covers the uniform decode shape. Flash-V100 UNIFORM_BATCH metadata and CUDA graph wrapper/replay code exist; recurrent state capture guards exist (gdn_attn.py:1486,2147). TP2 custom reducer contains capture/IPC handling and PyNCCL graph lifecycle support; actual replay remains unproven.
- Removing eager induces graph/compile defaults: compile graph env1, VLLM_COMPILE/FULL_AND_PIECEWISE, max capture1, use_inductor_graph_partitionFalse, RMSNorm/fused RMSNorm priorities [vllm_c,native], eliminate_noops if default enabled, MQ chunks64, memory-profiler graph estimate0, LM_HEAD_TOP1=0, AOT compile1, disable compile cache1, combo_kernelsTrue/benchmark_combo_kernelTrue. These are **automatic downstream changes within graph axis**, not extra launch knobs. Future resolved config must preserve them; explicit FULL_DECODE_ONLY may be overwritten by this policy. Existing logs include compile graph policy/capture sizes; envs supports VLLM_CUDAGRAPH_INPUT_ADDR_DEBUG and Flash route summary/debug flags, but no debug env is added to candidates here.
- R2: qwen_gdn_linear_attn.py:1680-1736 selects flashqla_sm70 for CUDA SM70/75 + head_k_dim128 + requested auto/flashqla_sm70 + dtypefloat16 + importable SM70 wrapper. Current checkpoint linear_key_head_dim128 and frozen dtypehalf satisfy static shape/dtype conditions. Original selector defaultsTrue if both env names absent, uses VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL before FLASH_QLA_SM70_USE_ORIGINAL_TILELANG. Explicit0 selects native precompiled vlk_varlen; explicit1 selects chunk_gated_delta_rule_fwd_sm70_tilelang (qwen_gdn_linear_attn.py:1846-1998), with chunk metadata prepared in gdn_attn.py:1791.
- Original TileLang function/package files exist. tilelang/engine/lower.py and contrib/nvcc.py call nvcc compile paths. P520 current shell has no nvcc, CUDA_HOME/CUDA_PATH unset, no /usr/local/cuda*, and venv search finds no nvcc. This is a static prerequisite gap; no JIT attempt. Past results/preflight/1.3-onecat-stock/tp2-server.log records original route warmup failing TileLang target detection (No CUDA or HIP or MPS), while docs/WBS.md also records Ornith missing-nvcc failure. Those distinct failures are not conflated; current files exist but successful compiler execution is unproved.
- Adjacent defaults: INDEXED_PREFILL=False, DIRECT_OUTPUT=True, source helper DECODE_WARMUP=False when env absent (qwen_gdn_linear_attn.py:398-419), whereas envs.py lambda DECODE_WARMUP defaultTrue. Record per-consumer discrepancy; do not silently assume one global value. All three envs unset in inspected current shell.
- R3: arg_utils.py:140-164 leaves explicit E5M2 unchanged; generic fp8 alias resolves E5M2 on SM70 Flash-V100 but is not a candidate. flash_attn_v100.py includes E5M2 uint8 KV/XQA/paged routes and bridge wrapper at1732; installed extension strings include fp8_e5m2_paged_kv_to_fp16 kernel symbols and XQA code. Weight quantization remains NVFP4. CacheConfig.mamba_ssm_cache_dtype is a separate field; changing KV dtype does not itself change recurrent-state dtype. Exact selected route/scales require future runtime evidence.

## C. Candidate command diff

These are frozen **expected future** command strings, constructed without execution. They do not certify that the current runner implements them. Common environment: CUDA_VISIBLE_DEVICES=0,1; ORIGINAL_PREFILL=0; DECODE_PARTITION_SIZE=256. Any existing validated GDN_DECODE_FLASHQLA override and runtime hook PYTHONPATH must be fixed identically across all candidates and recorded at integration; source default versus runner0 must not change accidentally.

### R0

```sh
CUDA_VISIBLE_DEVICES=0,1 VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256 /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e4m3 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --enforce-eager --language-model-only --host 127.0.0.1 --port 18080
```

### R1

```sh
CUDA_VISIBLE_DEVICES=0,1 VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256 /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e4m3 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --language-model-only --host 127.0.0.1 --port 18080 --compilation-config '{"cudagraph_capture_sizes":[1]}'
```

### R2

```sh
CUDA_VISIBLE_DEVICES=0,1 VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=1 VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256 /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e4m3 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --enforce-eager --language-model-only --host 127.0.0.1 --port 18080
```

### R3

```sh
CUDA_VISIBLE_DEVICES=0,1 VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256 /home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --enforce-eager --language-model-only --host 127.0.0.1 --port 18080
```

Normalized diff:

| Pair | Only explicit axis delta | Unchanged |
|---|---|---|
| R1/R0 | remove --enforce-eager; set graph capture_sizes[1] | E4M3, seq1, MBT2048, TP2, prefill0, no spec |
| R2/R0 | ORIGINAL_PREFILL0 -> 1 | eager, E4M3, seq1, MBT2048, graph config absent |
| R3/R0 | KV fp8_e4m3 -> fp8_e5m2 | eager, seq1, MBT2048, prefill0, no spec |

## D. Pre-inference blockers

1. Current runtime_launcher uses MBT4096; run_c2_onecat changes Qwen MBT2048 but is C2/WBS3, adds reasoning/tool/chat settings and overrides sampling. It also forces E4M3, ORIGINAL_PREFILL0 and GDN_DECODE_FLASHQLA0. Consequently direct reuse cannot preserve R1/R2/R3 deltas or C1 frozen experiment identity. Candidate dispatch and exact effective config/env receipts are absent; do not launch it as WBS5.
2. R2 compiler/toolchain discovery remains incomplete/absent on selected host shell. No installation or environment change performed. Resolve before any original route launch; preserve all other axes.
3. Confirm selected checkpoint revision against trusted provenance; hashes identify bytes but are not a revision assertion.
4. Future startup must record resolved graph mode/sizes, cache alignment (align block must not exceed MBT2048), route selection, actual graph hit and memory. No semantic evidence is promoted to new WBS5 PASS here. Historical capacity and FAIL_OUTPUT are distinct; this report does not impose a blanket semantic revalidation blocker beyond the frozen task.

## E. Unexpected findings

Environment audit scope: current P520 noninteractive SSH shell, readable /etc/systemd/system and ~/.config/systemd/user, .bashrc/.profile/.zshrc; matching requested env prefixes yielded no entries. No active vLLM/llama model server found. This does not prove every possible interactive shell or uninspected launcher is clean. Project scripts/config were fully searched for VLLM_SM70_/VLLM_FLASH_V100_/VLLM_DFLASH_/FLASH_QLA_/NCCL_/CUDA_. Findings: launcher CUDA_VISIBLE_DEVICES + ORIGINAL_PREFILL0; Qwen model config partition256; run_c2_onecat/run_b200recipe_onecat ORIGINAL_PREFILL0/GDN_DECODE_FLASHQLA0/partition256; recovery runner GDN0/partition256. Gemma-specific envs are confined to its model config. No NCCL override found in these scopes. Runtime hooks inspected: Gemma compatibility patches, no matching performance env override.

The forced E4M3 and ORIGINAL_PREFILL0 would directly erase R3/R2 if the existing Qwen runner were reused; source eligibility alone is insufficient. No new candidate/optimization/source mutation proposed or performed.

GPU MEASURED INFERENCE EXECUTED: NO

## 8B~8D remediation result — 2026-09-28

8A 관찰/과거 verdict는 위에 보존한다. 아래는 새 runner 구현 이후의 준비 상태이며 measured PASS를 뜻하지 않는다.

- Runner readiness: **READY_FOR_PRE_RUN_VALIDATION**. `scripts/run_wbs5.py` 명시적 track/candidate dispatch; 기본 동작은 dry-plan이다. 기존 WBS3 runner의 concurrency/v2 기본값은 유지한다.
- Frozen guard: pinned input SHA와 normalized effective argv/env OFAT allowlist, final worker config/command drift를 검사하며 위반은 `FROZEN_DELTA_MISMATCH`로 중단한다. context 131072/request, independent A/B, reserve4096/min1024, temp0/top_p1/seed520을 유지한다.
- Identity/evidence: candidate ID/run label/workload SHA/model+runtime+artifact hash, exact argv 및 host/container environment receipt; fresh raw exclusive creation, telemetry/post-health/output integrity/total output tokens 경로를 연결했다. 반복/confirm/실패 retry를 자동 실행하지 않는다.
- Metric remediation: 기존 TTFT/prefill/per-request decode/mean decode/aggregate decode/end-to-end TPS/batch wall 산식 유지. 새 WBS5 run만 graph-evidence.json, slot-progress JSONL/JSON, speculative counters/ratio를 저장한다. missing/ambiguous/reset counters와 unavailable slot fields는 UNKNOWN/null; raw server log는 보존한다.
- Remaining runtime-only unknown: **VERIFY_AT_STARTUP / VERIFY_DURING_MEASURED_RUN** — capture/replay/TP2 collective, E5M2 route/scales, actual Original Prefill route, VRAM fit 및 output integrity.
- Remaining blocker/gate: R2만 BLOCKED_BY_HOST_TOOLCHAIN: nvcc/완전한 CUDA 개발 toolkit 부재. 다른 후보는 차단하지 않는다.
- BLOCKED_BY_HARNESS: **없음**. Pre-run ChatGPT Ready: **YES** (host approval/gate가 남아 있는 후보는 measured admission 금지).
- Tests: 전체 `pytest` **146 passed, 25 subtests passed**; WBS5 offline 24 tests 포함. `scripts/validate_repo.py`: **Repository contract: PASS**. Python AST/JSON validation 및 git diff --check PASS. 실제 HTTP/GPU를 쓰는 inference test는 실행하지 않았다.
- Measured inference executed: **NO**. GPU server startup/model load/G0/128K request/benchmark/설치/host 설정 변경도 실행하지 않았다.

| Candidate | Run label | 8C state | Dry plan |
|---|---|---|---|
| `R0-E4M3-128K-SEMANTIC-BASELINE` | `screening-1` | `STATIC_READY` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-QWEN-ONECAT-R0-PERF-20260928-001/candidate-plan.json) |
| `R1-E4M3-128K-CUDAGRAPH-C1` | `screening-1` | `STATIC_READY` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-QWEN-ONECAT-R1-PERF-20260928-001/candidate-plan.json) |
| `R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL` | `screening-1` | `BLOCKED_BY_HOST_TOOLCHAIN` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-QWEN-ONECAT-R2-PERF-20260928-001/candidate-plan.json) |
| `R3-E5M2-128K-KV-ROUTE` | `screening-1` | `STATIC_READY` | [JSON](../results/plans/wbs5-preparation-20260928/EXP-V100-WBS5-QWEN-ONECAT-R3-PERF-20260928-001/candidate-plan.json) |

공통 구현/guard/evidence 및 8D receipt 설명: [WBS5 preparation report](WBS-5-preparation-readiness.md). 다음 단계는 ChatGPT의 pre-run final validation이며 자동 measured 실행으로 이어지지 않는다.

Qwen artifact provenance gap은 pinned HF revision의 upstream LFS/metadata hash manifest를 새 state receipt에 저장해 해소했다. 8A의 실제 shard hash와 일치한다. model tensor 다운로드/교체는 없으며 installed bytes/metadata는 future pre-run identity guard에서 다시 확인한다. CUDA userspace12.8.90과 nvcc는 별개다. `nvidia-cuda-nvcc-cu12`12.9.86 설치만으로 nvcc 존재를 주장하지 않는다; TileLang source가 해당 패키지는 ptxas만 제공한다고 명시한다. [8D receipt](../state/wbs5-toolchain-receipt.json).

Frozen max-num-seqs=1 및 MBT2048을 유지하면서 performance A/B 두 독립 client request를 보낸다. 이 계획만으로 C2 ACTIVE라고 주장하지 않으며 실제 queue-only/overlap evidence를 저장한다. graph C1 axis를 seq2로 변경하지 않았다.

## Qwen GDN decode baseline 추가 static audit — 2026-09-28

판정: **ADD_BASELINE_INVARIANT**. pinned 1Cat-vLLM 1.5.0은 GDN_DECODE_FLASHQLA 생략 시 default/SM70 auto-config가 **1**이며 explicit 0과 같지 않다. 과거 B200 C1 128K config/planned config는 0을 전달하고 server log167행은 exact mixed-QKV GDN decode, 170행은 해당 Triton JIT를 기록한다. 따라서 Qwen WBS5 R0~R3 모두 `VLLM_SM70_GDN_DECODE_FLASHQLA=0`을 공통 invariant로 고정했다. 위 8A 명령 예시는 당시 관찰로 보존하며 현재 명령/환경은 재생성된 네 dry plan이 기준이다.

후보 간 OFAT delta, deterministic sampling, performance/v1, thinking/tool 계약은 유지했다. diagnostic parser/sampling은 복사하지 않았다. normalized baseline/config SHA 및 Qwen plan/manifest를 갱신했고 input lock/model/runtime pin/다른 track/기존 raw/report는 변경하지 않았다. R0/R1/R3 STATIC_READY, R2 BLOCKED_BY_HOST_TOOLCHAIN 상태는 그대로다.

이 설정은 known-good serving route 재현 invariant(A)이며 모든 128K decode 성공에 필수라는 인과 증명은 아니다. flag1에서도 과거 decode 완료 사례가 있었고 B200의 semantic FAIL_OUTPUT도 유지한다. future startup/measured에서 worker별 effective flag/resolved route/kernel hit를 확인해야 한다.

검증: 관련 pytest **33 passed, 25 subtests passed**, 전체 pytest **149 passed, 25 subtests passed**, validate_repo **Repository contract: PASS**, AST/JSON/보존 검사 및 diff --check PASS. GPU inference/server startup/model load/benchmark executed: **NO**. [비교/도입 이력/근거 및 새 SHA](WBS-5-Qwen-1Cat-GDN-decode-audit.md), [source/raw receipt](../state/wbs5-qwen-gdn-route-audit.json). 다음 단계는 ChatGPT pre-run final validation이다.
