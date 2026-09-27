## A. 현재 main / relevant file 상태

Review parent HEAD: `fbb4bda30c950445fb9823c5489da240a532529d`, branch main, clean before this new report; origin/main was independently read with git ls-remote as fbb4bda30c950445fb9823c5489da240a532529d. Hardware/runtime/artifact checks performed on `ssh p520` -> `p520-llm`, not laptop. No model server/startup/inference/kernel/benchmark or fresh measured raw run executed.

Relevant files: docs/WBS.md; docs/WBS-5 - Qwen 3.8 27B - llama.cpp.md; config/models/qwen3.8-27b.json; config/runtime-lock.json; config/profiles/runtime-lanes.json; config/profiles/topologies.json; scripts/runtime_launcher.py; scripts/run_c2_llama.py; scripts/prepare_wbs5_plan.py; scripts/run_1gpu_litellm.py; scripts/bench_harness.py; scripts/build_128k_workload.py; workloads/performance/v1.json. Task/source/config/historical raw and measured reports unchanged.

Config pins unsloth/Qwen3.8-27B-GGUF revision4ca720788d1e01f1bff70c033e0d0028fd02e502; UD-Q4_K_M, Q8_0KV. Actual artifact checksum receipt recorded in sectionD. SharedTP2 is layer split1,1, not an alternative topology.

## B. Frozen candidate별 실행 가능성

| Candidate | Verdict | Static command support | Blocker |
|---|---|---|---|
| Q38-LLAMA-WBS5-R0-TARGET-B512-UB128 | BLOCKED | TARGET plan generated exactly | no Qwen shared-TP2 WBS5 performance runner/graph count report |
| Q38-LLAMA-WBS5-R1-NGRAM-DEFAULT | BLOCKED | only none ->ngram-simple verified; no overrides/draft | same integration gap; actual spec metric values untested |
| Q38-LLAMA-WBS5-R2-TARGET-UB256 | BLOCKED | expected transform only ub128 ->256 verified | runtime_launcher hardcodes ub128; no candidate selector |

READY requires integrated runner/workload/metric path as well as binary and artifact. BLOCKED here does not mean the binary/model failed a run: no run occurred.

## C. 각 candidate의 예상 exact command와 R0 대비 diff

R0/R1 were generated in memory from runtime_launcher.build_plan. R2 is the exact frozen expected transformation; existing launcher cannot emit it through a candidate option. All commands share empty planned environment. GGML_CUDA_P2P and GGML_CUDA_DISABLE_GRAPHS were unset in inspected P520 shell and neither is set by these commands. No command below executed.

### R0

```sh
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### R1

```sh
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type ngram-simple --jinja --reasoning off --metrics --slots --no-warmup
```

### R2

```sh
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

Normalized deltas: R1/R0 only spec-type none->ngram-simple. R2/R0 only ubatch-size128->256; batch512 retained. Fixed for all: target artifact/image, q8_0 K/V, -nglall, layer1,1, totalctx262144, parallel2, unified pool/per-slot131072, FAon, jinja/reasoningoff/metrics/slots/no-warmup. No MTP/draft companion, explicit NGRAM N/M/hits, P2P, GraphOFF or other candidate added. Current launcher hardcodes ub128 on reconstruction; merely editing a saved plan would not create valid R2 dispatch.

## D. pinned binary/source capability 확인 결과

Actual P520 target `/srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf` exists, size16464440224 bytes. Full-file SHA256 independently recomputed: `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`, **MATCH** to frozen expected checksum. HF download metadata at the conventional path was absent; exact revision is pinned in repository config, while content identity is established by the expected SHA match. No separate download revision receipt claimed.

P520 image inspect confirmed local exact digest `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`. Actual model-free llama-server --version:0.3.0-dev/build10775/commit67a17c17c, consistent with full pin67a17c17caa95742186f8b1ecadd1b5abd6d5ebb. --help with `--gpus all` (needed to expose libcuda) verified:

| Feature | Result | Evidence |
|---|---|---|
| spec-type none/ngram-simple | SUPPORTED | actual pinned help choices |
| batch/ubatch | SUPPORTED | actual options; explicit candidate args override binary defaults |
| kv-unified/per-slot | SUPPORTED | actual --help |
| flash-attn/layer/tensor-split | SUPPORTED | actual --help |
| context/parallel/cache types/Jinja/reasoning/metrics/slots/no-warmup | SUPPORTED | actual --help |
| NGRAM defaults | MATCH | actual help N12/M48/min-hits1, no explicit tuning |
| CUDA Graph compiled code | PRESENT | actual /usr/local/lib/libggml-cuda.so strings USE_GRAPHS/cudaGraphInstantiate/graph calls |
| Exact numeric USE_GRAPHS=1 | UNKNOWN static metadata | symbols alone do not certify numeric feature print; no model loaded to obtain it |

Historical actual graph reuse evidence remains unchanged in `results/raw/EXP-V100-Q38-LLAMA-Q80-TARGET-C2-128K-20260925-001/runtime/server-0.log`: line741 slot0/task8 graphs reused1382; line753 slot1/task6 graphs reused1588. Existing NGRAM C2 log also records reuse1280/1833. These are WBS3 evidence, not newly measured WBS5 counts. No graph env/option added.

## E. WBS5 workload/metric capture 준비 상태

Formal workload `workloads/performance/v1.json`, SHA256 `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`: IDV100-PERFORMANCE-C2-128K-v1, performance, context131072/request, reserve4096, minimum1024/request, independent2 projectsA/B, deterministic temperature0/top_p1/seed520, diversified identifiers. `build_128k_workload` can materialize it through future live tokenizer, but no materialization/tokenizer endpoint was invoked now.

`run_c2_llama.py` hardcodes concurrency/v2 manifest+semantic oracle (WBS3), with no WBS5 workload selector. `prepare_wbs5_plan.py` and `run_1gpu_litellm.py` are specialized to Ornith9B llama 1GPUx2; they do not implement this Qwen sharedTP2 track.

| Required output | Existing path | Readiness/gap |
|---|---|---|
| TTFT | requests.json/metrics.json | supported, first streamed content - stream start |
| prefill tok/s | runtime timings or prompt_tokens/TTFT fallback | supported; fallback includes request/first-token overhead |
| mean request decode tok/s | summarize arithmetic mean | supported |
| aggregate decode tok/s | total completed tokens/(latest end - earliest first content) | supported; preserve formula |
| end-to-end output tok/s | total completed tokens/batch_wall | supported |
| total output tokens | per-request actual_output_tokens in requests.json | raw supported; explicit aggregate total field absent from summarize |
| batch wall | max terminal_s - min submitted_s | supported |
| GPU0/GPU1 peakVRAM | gpu-peak.json/.5s nvidia-smi memory.used probe | supported, between-sample peaks may be missed |
| power/temp/clocks/GPU-util | runtime/gpu-telemetry.jsonl every2s | supported |
| integrity/context/minimumoutput | requests/tokenization/health-after/mechanical verdict | supported once performance workload selected |
| graph reuse count | complete raw runtime/server-0.log | raw retained; no structured parser/report field currently |
| R1 draft/accepted/acceptance | speculative-evidence.json/metrics.json | NGRAM path invokes before/after /metrics counter delta; actual non-null availability is future check |

Spec counter names: llamacpp:spec_decode_num_draft_tokens_total, llamacpp:spec_decode_num_accepted_tokens_total, llamacpp:spec_decode_num_drafts_total. Delta after-before; acceptance accepted/draft when draft>0, otherwiseNone. Missing counters remainNone, not fake0/PASS. This R1 is NGRAM, so current NGRAM capture condition is satisfied; unrelated pure-MTP gap does not apply to this track.

### Hardware/preflight

P520 read-only receipt during this review:

| GPU | Model | TotalMiB | FreeMiB | UsedMiB | TempC | PowerW | SM/MemMHz | Util |
|---|---|---|---|---|---|---|---|---|
|0|Tesla V100-SXM2-16GB|16384|16145|0|43|26.04|135/877|0%|
|1|Tesla V100-SXM2-16GB|16384|16145|0|41|27.00|135/877|0%|

Compute process query empty. Host memory free-h: total61Gi/used1.3Gi/available59Gi; swap total4Gi/used3.5Gi/free545Mi. Snapshot is preflight evidence, not benchmark telemetry. Current runner host-before captures nvidia-smi/process/ports and later2s telemetry, but does not explicitly record freeVRAM or hostRAM/swap in structured start receipt. These fields should be added to the WBS5 preflight only; no swap/clocks/power changes made. Topology previously observed NODE, inactive NVLink, read/writeP2P OK; no P2P candidate/test kernel.

### Repetition/confirm policy

Runner creates raw directory with exist_okFalse; harness rejects existing artifacts outside runtime subdirectory. Fresh experiment IDs can safely support R0 two repetitions and R1/R2 screening1 + optional same-config confirm1. Existing CLI has retry metadata for invalid-run replacement, which is **not** a valid repetition/confirm label. WBS5 policy dispatch/metadata for these prescribed counts is absent. No runs/automatic retries created here. Confirm must preserve candidate/config/workload hash and use a fresh ID; no new candidate or forced automatic confirm.

## F. measured inference 전에 해결해야 하는 blocker

- Qwen shared-TP2 WBS5 candidate dispatch and performance manifest selection are absent.
- R2 ub256 must be applied after base command construction and asserted against rebuild overwrite; exact OFAT diff/env must be frozen in receipts.
- Structured graph reuse extraction/report and aggregate output-total field missing; raw server log must remain preserved. Real R1 spec counters and graph hits must be verified during future run without assuming absence means0.
- Start receipt must include GPU name/total/free/used/temp/power/clocks/util/process and hostRAM/swap, alongside runtime/model identity and workloadSHA.
- R0 fresh repetitions2 and optional R1/R2 fresh confirm policy need explicit record labels, bounded execution and no overwrite.

## G. 필요한 최소 코드 수정안

Proposal only, no implementation/source edit in this static review:

1. Add a WBS5 Qwen shared-TP2 dispatch/runner (or explicit separate branch in run_c2_llama.py), selecting only frozen R0/R1/R2 and performance/v1. Keep WBS3 default concurrency/v2/oracle/lane behavior unchanged. Reuse existing launcher and bounded single-run lifecycle.
2. Candidate dispatch maps R0TARGET512/128, R1NGRAM512/128, R2TARGET512/256, validates exact command/env diffs and emits candidate/repetition/workload identity. Apply R2 after llama_plan's hardcoded default; do not change global WBS2/WBS3 ubatch.
3. Extend WBS5 preflight snapshot with explicit nvidia-smi fields plus /proc/meminfo or free output. Preserve process/port refusal and artifact/image checks.
4. Preserve full server log, then parse slot/task graphs reused lines after clean shutdown into a new WBS5 graph-evidence.json and report references. Missing/ambiguous counts must stay unknown; don't sum duplicated logs or claim a new measured pass. Add total_output_tokens as an explicit WBS5 summary field computed from existing per-request counts, retaining all TPS formulas.
5. Reuse NGRAM /metrics deltas and existing fresh directory refusal; add bounded repetition/confirm labels linked to identical candidate config+workload hash. R0 has2 planned executions, R1/R2 optional confirm1. No performance parameter change or additional candidate.

## H. 최종 결론

**BLOCKED**: pinned binary and frozen command syntax are supported; artifact receipt is in section D. Required integrated Qwen WBS5 workload/candidate/structured evidence/repetition path is incomplete. This report does not equate static capability with executed performance or semantic success.

GPU MEASURED INFERENCE EXECUTED: NO
