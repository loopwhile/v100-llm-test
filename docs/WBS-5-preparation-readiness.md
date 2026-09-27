# WBS5 8B~8D preparation readiness — 2026-09-28

시작 main SHA: `a78f0a8762b22724051e0d095eb48bb2de9b9b03`. 작업 시작 clean tree에서 원격 main을 `git pull --ff-only`와 `git ls-remote`로 다시 확인했다.

**READY_FOR_PRE_RUN_VALIDATION**. 7개 track의 runner/harness integration과 offline validation을 완료했다. **Measured inference executed: NO**. GPU server/model startup, short probe, G0 inference, 128K request, performance benchmark, CUDA JIT/kernel/compiler smoke는 실행하지 않았다. 서브에이전트도 사용하지 않았다.

## Readiness gate

| Track | Runner Ready | Dry Plan | Static Tests | Toolchain | Remaining Runtime Unknown | Pre-run ChatGPT Ready |
|---|---|---|---|---|---|---|
| Qwen3.8 llama.cpp | YES | 3 candidates / 6 plans PASS | PASS | 새 host change 없음 | VRAM, graph reuse, NGRAM acceptance | YES |
| Ornith9 llama.cpp | YES | 3 / 3 PASS | PASS | 새 host change 없음 | gateway routing/overlap, graph, NGRAM | YES |
| Ornith35 llama.cpp | YES | 4 / 4 PASS | PASS | 새 host change 없음 | embedded MTP, slot progress, graph, VRAM | YES |
| Gemma4 llama.cpp | YES | 4 / 4 PASS | PASS | 새 host change 없음 | batch1024 VRAM/graph; R3 Gate B pending | YES |
| Qwen3.8 1Cat-vLLM | YES | 4 / 4 PASS | PASS | R2만 BLOCKED_BY_HOST_TOOLCHAIN | graph C1, E5M2/Original route, VRAM/output | YES |
| Ornith9 1Cat-vLLM | YES | 4 / 4 PASS | PASS | 새 host change 없음 | G0 pending; target/drafter graph/MTP | YES |
| Ornith35 1Cat-vLLM | YES | 3 / 3 PASS | PASS | 새 host change 없음 | graph auto, MBT8192 VRAM/output | YES |

YES는 ChatGPT의 pre-run 검토에 필요한 구현/evidence plan이 준비됐다는 뜻이다. 측정 승인이나 startup/성능 PASS가 아니다. R2 host change 승인, G0 및 Gate B는 해당 candidate의 실행 admission을 계속 차단한다. `BLOCKED_BY_HARNESS`, `BLOCKED_BY_CONFIG`, `INVALID`가 남아 있는 후보는 없다.

## Candidate states / 8C

25개 frozen candidate, 28개 dry plans (Qwen llama R0 repetition-2 및 R1/R2 optional confirm-1의 3개 추가 계획). 모든 계획은 exact argv/env, model path/hash/revision, runtime lock, topology/context/concurrency, R0 normalized diff/config SHA, output reserve/minimum, labels, fresh ID pattern/raw destination, overwrite refusal, evidence 경로와 hard stops를 포함한다. `STATIC_READY` 19개, `CONDITIONAL_PENDING_GATE` 5개, `BLOCKED_BY_HOST_TOOLCHAIN` 1개다.

[8C manifest](../results/plans/wbs5-preparation-20260928/manifest.json)의 각 링크에서 전체 계획을 확인한다. Raw directory는 생성하지 않았다. Dry-plan의 artifact hash는 기대값이며 실제 installed bytes가 이번 8C에서 검증됐다는 주장이 아니다.

| Track | Candidate ID | Final state |
|---|---|---|
| qwen-llama | `Q38-LLAMA-WBS5-R0-TARGET-B512-UB128` | `STATIC_READY` |
| qwen-llama | `Q38-LLAMA-WBS5-R1-NGRAM-DEFAULT` | `STATIC_READY` |
| qwen-llama | `Q38-LLAMA-WBS5-R2-TARGET-UB256` | `STATIC_READY` |
| ornith9-llama | `TARGET_BASELINE` | `STATIC_READY` |
| ornith9-llama | `TARGET_UB256` | `STATIC_READY` |
| ornith9-llama | `NGRAM_DEFAULT` | `STATIC_READY` |
| ornith35-llama | `ORN35-LLAMA-WBS5-R0-TARGET` | `STATIC_READY` |
| ornith35-llama | `ORN35-LLAMA-WBS5-R1-MTP1` | `STATIC_READY` |
| ornith35-llama | `ORN35-LLAMA-WBS5-R2-UB256` | `STATIC_READY` |
| ornith35-llama | `ORN35-LLAMA-WBS5-R3-QUEUE4X` | `STATIC_READY` |
| gemma-llama | `G4-LCPP-WBS5-R0-TARGET-B512-UB128` | `STATIC_READY` |
| gemma-llama | `G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128` | `STATIC_READY` |
| gemma-llama | `G4-LCPP-WBS5-R2-TARGET-B1024-UB128` | `STATIC_READY` |
| gemma-llama | `G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF` | `CONDITIONAL_PENDING_GATE` |
| qwen-onecat | `R0-E4M3-128K-SEMANTIC-BASELINE` | `STATIC_READY` |
| qwen-onecat | `R1-E4M3-128K-CUDAGRAPH-C1` | `STATIC_READY` |
| qwen-onecat | `R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL` | `BLOCKED_BY_HOST_TOOLCHAIN` |
| qwen-onecat | `R3-E5M2-128K-KV-ROUTE` | `STATIC_READY` |
| ornith9-onecat | `ORN15-9B-1CAT-WBS5-R0-BASELINE` | `CONDITIONAL_PENDING_GATE` |
| ornith9-onecat | `ORN15-9B-1CAT-WBS5-R1-MBT8192` | `CONDITIONAL_PENDING_GATE` |
| ornith9-onecat | `ORN15-9B-1CAT-WBS5-R2-TARGET-GRAPH` | `CONDITIONAL_PENDING_GATE` |
| ornith9-onecat | `ORN15-9B-1CAT-WBS5-R3-MTP2` | `CONDITIONAL_PENDING_GATE` |
| ornith35-onecat | `R0-BASELINE-EAGER-MBT4096` | `STATIC_READY` |
| ornith35-onecat | `R1-GRAPH-AUTO-MBT4096` | `STATIC_READY` |
| ornith35-onecat | `R2-EAGER-MBT8192` | `STATIC_READY` |

계획 재현용 offline command (같은 destination은 거부; 새로운 output directory 사용):

```sh
python3 scripts/validate_wbs5_plans.py --output /tmp/wbs5-review-plans --date 20260928
python3 scripts/run_wbs5.py --track qwen-llama --candidate R0 --experiment-id EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001 --run-label repetition-1
```

두 command 모두 default dry-plan이다. Host/GPU/HTTP 호출이 없다. 계획의 raw/hook absolute path는 현재 checkout 경로 기준이다. Future P520 실행은 해당 checkout에서 동일 committed inputs로 계획을 재생성하고 pre-run receipt를 확인한다. Python executable, model /srv path, image digest, wheel identity는 pinned 값이다.

## Runner / frozen guards

- `scripts/run_wbs5.py`: 7개 track의 명시적 WBS5 dispatch, default dry-plan, 별도 explicit future measured opt-in. Sweep/retry/repetition loop 없음. Ornith9 llama는 `prepare_wbs5_plan.py`와 `run_1gpu_litellm.py`의 기존 gateway/routing-settled lifecycle을 재사용한다.
- `scripts/wbs5_contract.py`: 25개 ID mapping, 기존 input SHA 및 lock SHA 검증, independent frozen OFAT allowlist. Final launch plan, worker config/sampling/template/context, effective argv/host env/container env drift는 `FROZEN_DELTA_MISMATCH` hard stop. Config 저장 이후 source 변경도 source SHA 비교로 거부한다.
- Qwen 1Cat R2 ORIGINAL_PREFILL=1 및 R3 explicit fp8_e5m2가 WBS3 forced override에 의해 지워지지 않는다. R1은 eager 제거+capture sizes[1] graph 축만 변경한다. Frozen max-num-seqs1/MBT2048을 유지하며 independent A/B client requests=2; plan만으로 C2 ACTIVE를 주장하지 않고 actual queue/overlap을 저장한다.
- Ornith35 llama MTP는 embedded n=1, companion draft 없음. R3 CUDA_SCALE_LAUNCH_QUEUES=4x 및 Gemma R3 GGML_CUDA_DISABLE_GRAPHS=1은 Docker --env로 container 내부에 전달한다. Pinned image의 inherited env와 explicit override도 future pre-launch inspect receipt에 저장한다.
- Fresh experiment/raw directory exclusive creation. Candidate/run label과 config SHA/workload SHA가 영수증에 포함된다. Qwen llama R0 repetition-1/-2, R1/R2 optional confirm-1은 각각 별도 fresh ID 및 동일 normalized config. 다른 track에 승인되지 않은 repetition/confirm을 추가하지 않는다.
- Ornith9 1Cat G0 및 Gemma Gate B: matching track/R0 config hash, separate raw experiment의 hash-bound evidence 및 PASS decision 필요. G0는 concurrency/v2 workload/oracle SHA와 Project A/B semantic PASS를 요구한다. Gate B는 graph-support PASS 및 frozen trigger만 허용한다.
- WBS3 run_c2_llama/run_c2_onecat 및 runtime_launcher, model/runtime/profile pins, workload 원문은 변경하지 않았다. bench_harness 보강은 phase=WBS5 경로로 분리한다. 기존 LiteLLM lifecycle peak 함수의 JSON GPU index key 표현 불일치는 숫자/산식 변경 없이 수정했다.

## Evidence / metrics

새 WBS5 run에만 생성:

- runtime/pre-run-receipt.json: GPU name/total/free/used VRAM, processes, temperature/power/SM-memory clocks/utilization, host RAM/swap, model/runtime/artifact expectation. Missing observations 또는 busy/wrong GPUs는 실행 전 중단.
- runtime/candidate-plan.json 및 planned-config.json: full candidate identity/config/workload/source SHA. runtime/effective-environment.json: exact subprocess env, Docker image defaults+overrides. Shared runner는 startup snapshot, artifact-check, runtime-version, server-process/cleanup/exit receipts를 보존한다. Ornith9는 기존 plan/config, routing receipts를 재사용한다.
- metrics.json/requests.json: TTFT, prefill TPS, each request decode TPS, mean request decode TPS, aggregate decode TPS, end_to_end_output_tps, batch wall, actual output tokens/request 및 total_output_tokens. UNKNOWN token count는 total=null; missing counter를 0으로 만들지 않는다.
- gpu-peak.json: 기존 measured-window 0.5s nvidia-smi peak sampler. runtime/gpu-telemetry.jsonl: 2s power/temp/SM clock/memory clock/utilization 및 monotonic time; wbs5-evidence.json에 GPU별 observed min/max/sample count와 UNKNOWN 상태를 추가한다.
- graph-evidence.json: raw server log에서 slot/task terminal graphs reused count; duplicate는 합산하지 않고 conflicting/unassigned/missing count는 UNKNOWN/null. 원문 server log 보존. Lifecycle count를 measured-window hit로 주장하지 않는다.
- runtime/slot-progress-N.jsonl 및 slot-progress.json: per-slot/task ID, monotonic timestamp, n_prompt_tokens_processed/n_past/n_decoded/is_processing. /slots unavailable fields는 null; resident count로 prompt progress를 대체하지 않는다.
- speculative-evidence.json: llama MTP/NGRAM 및 1Cat MTP의 before/after /metrics draft tokens, accepted tokens, draft count, acceptance ratio. Missing/reset/ambiguous labels는 UNKNOWN/null. Counter를 제공하지 않는 runtime은 route가 구현됐어도 실제 count는 UNKNOWN이다.
- health-after.json, overlap-evidence.json, output integrity 및 completion/verdict는 기존 harness 정의를 유지한다. WBS5 evidence receipt가 이를 연결한다.

기존 aggregate decode 정의는 **runtime-completed output tokens / (latest completion − earliest first token)**, end_to_end_output_tps는 **output tokens / batch wall**이다. Mean request decode는 개별 decode TPS의 평균이며 aggregate와 같다고 가정하지 않는다. 1Cat에서 server timing이 없을 때 기존 token/TTFT 기반 prefill fallback은 queue delay를 포함하는 추정치다. 이번에 metric 의미를 재정의하지 않았다.

VRAM 샘플 사이 순간 peak, 실제 graph/cache/MTP routes, output semantics와 /slots/counter availability는 future startup/measured evidence로만 확정한다. `VERIFY_AT_STARTUP` / `VERIFY_DURING_MEASURED_RUN`을 static PASS로 바꾸지 않았다.

## 8D Original FlashQLA / nvcc

[Read-only P520 receipt](../state/wbs5-toolchain-receipt.json).

- nvcc PATH discovery: NONE; absolute path/version: UNKNOWN/null. /usr, /opt, /home/loopwhile file search도 nvcc 없음. CUDA_HOME/CUDA_PATH unset, /usr/local/cuda* 및 /usr/include/cuda_runtime.h 없음.
- pinned runtime: 1Cat-vLLM1.5.0, CUDA userspace `nvidia-cuda-runtime-cu12=12.8.90`, TileLang0.1.10. `nvidia-cuda-nvcc-cu12=12.9.86`가 있지만 TileLang env.py의 설명대로 이 패키지는 ptxas만 제공하며 nvcc toolkit과 같지 않다.
- TileLang env.py는 CUDA_HOME/CUDA_PATH -> PATH nvcc -> pip nvidia-cuda-nvcc>=13 discovery -> default toolkit roots 순으로 탐색하고 import 때 CUDA_HOME을 정한다. contrib/nvcc.py / engine/lower.py는 discovered nvcc/compiler subprocess를 사용한다. Env는 TileLang import 전 child process에 필요하다.
- Installed Qwen GDN Original Prefill route는 flash_qla의 SM70/SM75 wrapper를 import한다. Wrapper는 shared TileLang JIT backend를 호출한다. Python package/source 존재는 nvcc/compiler 실행 가능성을 증명하지 않는다. source inspection에서 compiler의 정확한 최소/최대 버전 범위는 확정하지 못했다.
- **R2 only BLOCKED_BY_HOST_TOOLCHAIN**. compiler discovery/compile-only smoke를 할 nvcc가 없어 실행하지 않았다. JIT 실패를 inference로 확인하지 않았다. R0/R1/R3에 toolchain env를 섞지 않았다.
- 사용자가 승인해야 할 정확한 host change: **driver/기존 runtime/model을 보존하고 SM70 및 pinned CUDA12.8 userspace와 호환될 isolated CUDA12.8 development toolkit (nvcc+headers+development libraries)을 예컨대 /opt/cuda-12.8에 provision**. 설치/승인은 이번 작업에서 수행하지 않았다.
- 승인 후 검증할 값: 실제 toolkit root/nvcc absolute path/version; CUDA_HOME=<verified root>, PATH=<verified root>/bin:<recorded base PATH>를 R2 child에만 전달. Compile-only discovery를 통과하고 new operational toolchain receipt/delta review를 갱신하기 전 R2 guard를 해제하지 않는다. 현재 존재하지 않는 CUDA_HOME을 만들어 기록하지 않는다.

## Verification / next step

- Whole offline pytest suite: **146 passed, 25 subtests passed** (new WBS5 24 tests). Real GPU inference tests not run; harness executions in tests use synthetic adapters/mocked receipts/GPU probes.
- `scripts/validate_repo.py`: **Repository contract: PASS**.
- Python AST / JSON validation: PASS. Git diff --check: PASS.
- All 7 reviews retain 8A observations and append 8B~8D results. All 7 frozen inputs, performance/v1, runtime/model/profile pins and existing results/raw/measured reports remain unchanged.
- No measured experiment verdict or historical metric rewritten. No package/system/driver/clock/governor change, new optimization candidate, automatic tuning/retry or model download/replacement.

다음 단계는 **ChatGPT 10번 pre-run final validation**이다. 이 작업은 commit/push 이후 중단하며 measured test를 자동 시작하지 않는다.
