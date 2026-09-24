# WBS — 2× Tesla V100 16GB 최종 LLM 서빙 검증

## 0. 프로젝트 계약 [DONE]

### 0.1 저장소 기반 구성 [DONE]
- qwen3.8-bench에서 검증된 증거 수집 및 보고 구조를 재사용한다.
- 과거 raw 결과를 현재 acceptance 근거로 가져오지 않는다.
- C1/C2 용어, 에이전트당 128K 목표, 변경 불가능한 experiment ID 규칙을 고정한다.

### 0.2 측정 하네스 [DONE]
- C1/C2 barrier 동시 실행.
- 런타임 측 C2 overlap 샘플링: llama.cpp processing/deferred + slots, vLLM running/waiting metrics.
- live tokenizer receipt 기반 128K 예산 검증.
- 독립적인 Project A/B prompt hash 검증.
- raw evidence → report → summary/comparison CSV 발행 파이프라인.
- C1, C2 resident/active overlap, queue-only, OOM/capacity/runtime/output 실패에 대한 명시적 판정.

### 0.3 런타임 lane [DONE]
- llama.cpp: TARGET / NGRAM / MTP / MTP_NGRAM.
- 1Cat-vLLM: STOCK.
- v100-skinny: 필수 SKINNY 결과 row. 현재 2×V100-16GB에서는 WBS 1.4의 `FAIL_OOM_MODEL_LOAD`가 terminal preflight 결과다.
- Shared TP2 및 Ornith 9B 1GPU×2 topology 정의.
- Ornith 9B 1GPU×2는 LiteLLM 단일 gateway endpoint를 포함한 실제 배포 topology로 고정한다. backend 직접 분배는 진단용일 뿐 정식 acceptance 경로가 아니다.

## 1. 신규 환경 및 artifact 검증 [DONE]

### 1.1 호스트 스냅샷 [DONE]
다음을 수집한다.
- NVIDIA driver 및 CUDA compatibility.
- V100 2장의 identity 및 VRAM.
- 전력 제한, clock, persistence 상태.
- CPU/RAM/kernel.
- GPU 사용 중인 process와 listening port.
- 런타임 stdout/stderr를 experiment runtime log 디렉터리에 보존한다.

벤치마크 자동화는 하드웨어 정책을 변경해서는 안 된다.

### 1.2 llama.cpp 런타임 검증 [DONE]
고정된 image/build/commit을 검증하고 다음 기능 지원 여부를 확인한다.
- kv-unified
- kv-unified-per-slot
- spec-type none
- ngram-simple
- draft-mtp
- composite draft-mtp,ngram-simple

### 1.3 1Cat-vLLM STOCK 및 LiteLLM gateway 검증 [DONE]
다음을 검증한다.
- 1Cat-vLLM 1.5.0 exact wheel identity.
- FLASH_ATTN_V100.
- TP2 startup.
- exact STOCK artifact가 확정된 경우 Ornith 9B의 GPU별 TP1 독립 server startup.
- LiteLLM v1.101.0 exact image/version.
- gateway 자체 상태 확인은 inference를 유발할 수 있는 `/health`가 아니라 `/health/liveliness`를 사용할 것.
- Ornith 9B 1GPU×2에서 두 backend를 동일 model group으로 등록하고, least-busy + backend별 max_parallel_requests=1 설정으로 단일 client endpoint를 제공할 것.
- 각 모델 profile의 tokenizer/template/tool/parser 요구사항.

### 1.4 v100-skinny 검증 [DONE — FAIL_OOM_MODEL_LOAD]
확인 결과:
- exact skinny commit `5b589c0dc81223e0ba65bcb3e755874723f8b515`: PASS.
- exact 1Cat-vLLM 1.2.2 wheel 및 SHA256: PASS.
- TileLang / apache-tvm-ffi 0.1.10 SM70 bootstrap: PASS.
- SM70 skinny kernel JIT 및 entry-point 확인: PASS.
- exact `RadixArk/Qwen3.8-27B-NVFP4@554ebba9b5f1b79dc11246341960360e6ef05ef4`: PASS.
- TP2 experimental launcher adaptation: PASS.
- 현재 P520 `2× Tesla V100-SXM2-16GB` model load: `FAIL_OOM_MODEL_LOAD`.
- 실패 위치: `process_weights_after_loading -> _qpn_stash -> _qpn_prepack`.
- 실패 시 각 GPU는 약 15.21 GiB PyTorch allocation 상태였고 18 MiB 추가 allocation에서 OOM.
- server boot 및 TP2 depth-3 skinny gate: NOT_REACHED.

따라서 현재 2×16GB 하드웨어에서는 Qwen3.8-27B SKINNY lane을 C1/C2 측정 대상으로 예약하지 않는다. 공개된 TP4 결과나 Issue #1의 2×V100-32GB TP2 성공 결과를 2×16GB PASS로 대체하지 않는다.

### 1.5 모델 artifact 확정 [DONE]

확정 결과:

- Qwen3.8-27B llama.cpp:
  - `unsloth/Qwen3.8-27B-GGUF`
  - exact revision/path/SHA256 확인.
  - benchmark scope는 `TARGET` + `NGRAM`만 사용한다.
- Qwen3.8-27B STOCK 1Cat:
  - `QUASAR-QAT/Qwen3.8-27B-QUASAR-NVFP4`
  - exact revision/path 확인.
  - WBS 1.3 TP2 runtime preflight PASS.
- Qwen3.8-27B SKINNY:
  - exact RadixArk artifact/revision 확인.
  - WBS 1.4에서 현재 2×V100-16GB에 `FAIL_OOM_MODEL_LOAD`.
  - local RadixArk checkpoint는 preflight 종료 후 삭제.
- Ornith 1.5 9B llama.cpp:
  - exact local path/SHA256/revision 확인.
  - source repository identity는 unresolved로 명시하며 추정하지 않는다.
- Ornith 1.5 9B STOCK:
  - `ornith-ai/Ornith-1.5-9B-NVFP4`
  - exact revision/path 확인.
  - artifact는 확정했으나 V100 runtime compatibility는 PENDING.
- Ornith 1.5 35B-A3B llama.cpp:
  - base GGUF repository/revision/path/SHA256 확인.
  - MTP companion revision/path/SHA256 확인.
  - MTP companion repository identity는 unresolved로 유지.
- Ornith 1.5 35B-A3B STOCK:
  - `ornith-ai/Ornith-1.5-35B-A3B-NVFP4`
  - exact revision/path 확인.
  - artifact는 확정했으나 V100 runtime compatibility는 PENDING.
- Gemma4 26B-A4B llama.cpp:
  - `unsloth/gemma-4-26B-A4B-it-qat-GGUF`
  - base 및 MTP companion exact revision/path/SHA256 확인.
- Gemma4 26B-A4B STOCK:
  - exact local NVFP4 artifact가 없으므로 PENDING.
- non-Qwen v100-skinny:
  - pinned v1.1 model contract가 없으므로 `UNSUPPORTED`.

repository identity가 검증되지 않은 항목은 unresolved 상태를 유지하며 추정값으로 채우지 않는다.
## 2. C1 — 128K capacity 및 correctness [TODO]

`workloads/capacity/v1.json`을 사용하며, 정확한 live tokenizer 기준으로 materialize한다.

공통 규칙:
- 처음부터 128K로 테스트한다.
- 96K/64K는 128K capacity 실패 이후 원인 확인용 diagnostic으로만 사용한다.
- TARGET vs NGRAM 비교는 모든 llama.cpp 모델에서 필수다.
- C1/C2의 NGRAM lane 목적은 `ngram-simple`이 활성화된 상태에서 해당 context/concurrency를 정상 수용하고 output integrity를 유지하는지 확인하는 것이다. C1/C2 PASS에 draft/accepted token 발생이나 TARGET 대비 속도 향상을 요구하지 않는다.
- NGRAM의 실제 가속 효과는 Phase 5의 performance workload에서 TARGET vs NGRAM, MTP vs MTP_NGRAM으로 판정한다. Capacity workload에서 draft counter가 0이거나 성능 향상이 관측되지 않아도 NGRAM acceptance 실패로 해석하지 않는다.
- MTP 대상 모델에서는 MTP vs MTP_NGRAM pair를 유지한다.
- MTP 대상 모델에서 MTP 또는 MTP_NGRAM이 지원되지 않으면 해당 결과를 `UNSUPPORTED`로 명시한다.
- C1 PASS는 요청한 output 정상 완료, 유효한 출력, OOM/truncation/corruption 없음, 실행 후 server 정상 상태를 모두 요구한다.

### 2.1 llama.cpp

#### 2.1.1 Qwen3.8-27B [DONE]
- artifact: `UD-Q4_K_M`.
- KV: `Q8_0`.
- 실행 lane: `TARGET`, `NGRAM`.
- Qwen3.8-27B에는 `MTP`, `MTP_NGRAM`을 계획하지 않는다.
- 각 lane에서 C1 128K capacity/correctness를 판정한다.
- TARGET: `EXP-V100-Q38-LLAMA-Q80-TARGET-C1-128K-20260923-002` — `PASS_C1_128K`.
- NGRAM: `EXP-V100-Q38-LLAMA-Q80-NGRAM-C1-128K-20260923-002` — `PASS_C1_128K`. 실제 slot에서 `ngram-simple` 활성 확인; draft 토큰은 0이었으나 C1은 가속 효과가 아니라 NGRAM-on capacity/correctness를 판정하므로 PASS에 영향이 없다.
- TARGET/NGRAM의 `20260923-001` 시도는 inference 전 사전 검사 종료(`INCONCLUSIVE`)이며 capacity 실패나 measured repetition으로 계산하지 않는다.

#### 2.1.2 Ornith 1.5 9B [DONE]
- artifact: `Q6_K`.
- KV: `FP16`.
- 실행 lane: `TARGET`, `NGRAM`, `MTP`, `MTP_NGRAM`.
- TARGET: `EXP-V100-ORN15-9B-LLAMA-F16-TARGET-C1-128K-20260923-001` — `PASS_C1_128K`; prefill 918.69 tok/s, decode 49.23 tok/s.
- NGRAM: `EXP-V100-ORN15-9B-LLAMA-F16-NGRAM-C1-128K-20260923-001` — `PASS_C1_128K`; prefill 918.66 tok/s, decode 48.13 tok/s. `ngram-simple` 활성 상태에서 128K capacity/correctness를 통과했다. Draft/accepted-token 발생 및 속도 향상은 C1 acceptance 기준이 아니며 Phase 5에서 평가한다.
- MTP: `EXP-V100-ORN15-9B-LLAMA-F16-MTP-C1-128K-20260923-001` — `PASS_C1_128K`; prefill 725.93 tok/s, decode 52.12 tok/s; draft 645, accepted 291, acceptance 45.116%.
- MTP_NGRAM: `EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C1-128K-20260923-001` — `PASS_C1_128K`; prefill 726.00 tok/s, decode 52.16 tok/s; composite `draft-mtp,ngram-simple` 상태에서 128K capacity/correctness를 통과했다. MTP counters는 645/291이며 NGRAM의 추가 성능 기여 여부는 C1에서 판정하지 않고 Phase 5로 이관한다.
- 네 lane 모두 prompt 129,023 + output reserve 2,048 = 131,071 / 131,072 token budget을 사용했고, 정상 stop / post-health / cleanup / exit 0을 확인했다.
- 출력 의미 품질 caveat: TARGET/NGRAM의 일부 verification assertion은 live state와 snapshot state를 혼동했고, MTP 계열은 `dict(self.pages)`를 live reference로 오인했다. 이는 serving/output-integrity acceptance와 분리해 각 `acceptance-review.json`에 기록한다.

#### 2.1.3 Ornith 1.5 35B-A3B [DONE]
- artifact: `Q4_K_M`.
- KV: `Q8_0`.
- 실행 lane: `TARGET`, `NGRAM`, `MTP`, `MTP_NGRAM`.
- base GGUF SHA256: `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`.
- native MTP는 target GGUF에 내장된 1-layer NextN predictor를 사용하며 `--spec-draft-n-max 1`로 검증했다. 별도 `mtp_companion` artifact는 이 native-MTP lane에 주입하지 않았다.
- TARGET: `EXP-V100-ORN15-35B-LLAMA-Q80-TARGET-C1-128K-20260924-001` — `PASS_C1_128K`; prefill 267.01 tok/s, decode 49.83 tok/s.
- NGRAM: `EXP-V100-ORN15-35B-LLAMA-Q80-NGRAM-C1-128K-20260924-001` — `PASS_C1_128K`; prefill 265.95 tok/s, decode 49.14 tok/s; draft 96 / accepted 49. NGRAM 성능 효과는 Phase 5에서 판정한다.
- MTP: `EXP-V100-ORN15-35B-LLAMA-Q80-MTP-C1-128K-20260924-001` — `PASS_C1_128K`; prefill 255.13 tok/s, decode 58.26 tok/s; draft 505 / accepted 401, acceptance 79.406%.
- MTP_NGRAM: `EXP-V100-ORN15-35B-LLAMA-Q80-MTP-NGRAM-C1-128K-20260924-001` — `PASS_C1_128K`; prefill 255.27 tok/s, decode 56.21 tok/s; draft 512 / accepted 364, acceptance 71.094%. NGRAM의 추가 성능 효과는 Phase 5에서 판정한다.
- 네 lane 모두 prompt 129,023 + output reserve 2,048 = 131,071 / 131,072 token budget을 사용했고, 정상 stop / post-health / cleanup / exit 0을 확인했다.
- 모델 응답의 semantic caveat는 serving/output-integrity acceptance와 분리해 각 `acceptance-review.json`에 기록했다.

#### 2.1.4 Gemma4 26B-A4B [DONE]
- artifact: `UD-Q4_K_XL`.
- KV: `FP16`.
- 실행 lane: `TARGET`, `NGRAM`, `MTP`, `MTP_NGRAM`.
- base GGUF SHA256: `a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891`.
- MTP 계열은 별도 **smart Q4_0** Gemma4 assistant GGUF `mtp-gemma-4-26B-A4B-it.gguf`, `--spec-draft-n-max 4`, `--spec-draft-device CUDA0` contract로 검증했다. companion SHA256은 `7272d97595f0d4c74bd7b623492b7dbdaafd8b7c72f329a8270ba4eca68f768a`.
- TARGET: `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C1-128K-20260924-001` — `PASS_C1_128K`; prompt 129,024 + reserve 2,048 = 131,072 / 131,072; prefill 524.64 tok/s, decode 68.10 tok/s; peak VRAM 8,775 / 8,785 MiB.
- NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C1-128K-20260924-001` — `PASS_C1_128K`; prefill 526.51 tok/s, decode 64.39 tok/s; draft 96 / accepted 4. NGRAM 가속 효과는 Phase 5에서 판정한다.
- MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C1-128K-20260924-001` — `FAIL_STARTUP`. preflight와 target/companion SHA256 검증은 PASS했으나 Gemma4 assistant speculative draft 초기화 중 native backtrace가 발생했고 server exit code 139로 종료됐다. measured request는 시작되지 않았다. OOM 또는 artifact identity 실패로 분류하지 않는다.
- MTP_NGRAM: `UNSUPPORTED` on the pinned runtime. composite lane도 동일한 Gemma4 assistant draft initialization을 선행 조건으로 가지므로 MTP의 terminal startup blocker를 NGRAM이 우회할 수 없다. 중복 crash replay는 실행하지 않았고 가짜 experiment ID도 만들지 않았다.
- MTP startup failure signature는 ggml-org/llama.cpp issue #25828의 보고와 유사하지만, 동일 root cause라고 단정하지 않는다.
- C2 승격 대상은 C1을 PASS한 `TARGET`, `NGRAM` 두 lane뿐이다.
- 모델 응답의 semantic caveat와 startup failure 분석은 각 report / `acceptance-review.json`에 분리 기록했다.
- **Supplemental diagnostic D2.1.4A [DONE — FAIL_STARTUP]**: 동일 pinned b10775 / 동일 target+smart-Q4_0 drafter / 동일 TP2 / MTP n=4에 `--fit off`만 추가했다. server startup은 다시 exit 139로 실패했고 measured request는 없었다. 따라서 device-memory fitting 자체가 baseline crash의 원인이라는 가설은 기각한다.
- **Supplemental diagnostic D2.1.4B [DONE — DIAGNOSTIC TOPOLOGY UNSUPPORTED]**: TP2 128K를 유지하고 `split-mode layer -> row`, `main-gpu=0`만 바꿔 KV placement를 진단하려 했으나 target model load 단계에서 `device CUDA0 does not support split buffers`로 종료됐다. 따라서 V100 CUDA backend의 row split 자체가 이 pinned runtime에서 사용할 수 없어 MTP 원인 판정에는 쓰지 않는다.
- **Supplemental diagnostic D2.1.4C [DONE — INCONCLUSIVE]**: CUDA0 단일 GPU, context 8192, target `-ngl 20`, draft GPU offload `all`로 실행했으나 exit 132(SIGILL)로 종료됐다. CUDA1은 제거됐지만 target의 대규모 CPU partial-offload 경로를 동시에 새로 열었으므로 이 결과만으로 TP2/MTP placement 가설을 판정하지 않는다.
- **Supplemental diagnostic D2.1.4D [IN_PROGRESS]**: baseline TP2/full-offload/128K/layer split을 그대로 유지하고, 유일한 변경으로 draft device를 `CUDA0`에서 `CUDA0,CUDA1`로 확장한다. b10775의 speculative params가 target context를 `ctx_other`로 참조하고 draft context의 n_ctx를 target과 동일하게 사용하는 구조에서, target과 draft device placement를 정렬했을 때 startup crash가 사라지는지 확인한다.

### 2.2 1Cat-vLLM STOCK

공통 실행 조건:
- TP2.
- `max_model_len=131072`.
- `max_num_seqs=1`.
- model profile에 선언된 KV format과 speculative configuration을 사용한다.
- artifact identity와 runtime compatibility를 별도로 판정한다.

#### 2.2.1 Qwen3.8-27B STOCK [TODO]
- artifact: `QUASAR-QAT/Qwen3.8-27B-QUASAR-NVFP4`.
- WBS 1.3 TP2 runtime preflight: PASS.
- KV: `fp8_e5m2`.
- speculative: target-only.
- 신규 C1 128K acceptance를 수행한다.

#### 2.2.2 Ornith 1.5 9B STOCK [BLOCKED — runtime compatibility pending]
- artifact: `ornith-ai/Ornith-1.5-9B-NVFP4` exact revision/path 확인 완료.
- artifact identity는 확정됐지만 V100 runtime compatibility는 아직 미검증이다.
- runtime compatibility를 먼저 검증하고 PASS한 경우에만 C1 128K로 진행한다.
- TP2 외에 Phase 4의 1GPU×2 + LiteLLM topology도 별도로 검증한다.

#### 2.2.3 Ornith 1.5 35B-A3B STOCK [BLOCKED — runtime compatibility pending]
- artifact: `ornith-ai/Ornith-1.5-35B-A3B-NVFP4` exact revision/path 확인 완료.
- artifact identity는 확정됐지만 V100 runtime compatibility는 아직 미검증이다.
- runtime compatibility를 먼저 검증하고 PASS한 경우에만 C1 128K로 진행한다.

#### 2.2.4 Gemma4 26B-A4B STOCK [BLOCKED — exact artifact pending]
- exact local NVFP4 artifact가 아직 확정되지 않았다.
- exact artifact를 확정하고 V100 runtime compatibility를 검증한 뒤 C1 128K 진행 여부를 결정한다.
- 검증되지 않은 repository/revision/path를 추정해서 채우지 않는다.

### 2.3 v100-skinny SKINNY

#### 2.3.1 Qwen3.8-27B SKINNY [CLOSED — FAIL_OOM_MODEL_LOAD]
- WBS 1.4에서 현재 P520 2×V100-16GB 구성의 model-load 단계에서 `FAIL_OOM_MODEL_LOAD`가 확정됐다.
- 실패 위치: `process_weights_after_loading -> _qpn_stash -> _qpn_prepack`.
- server boot 및 depth-3 boot gate: `NOT_REACHED`.
- 따라서 C1 128K를 실행하지 않는다.
- v100-skinny v1.1 / 1Cat 1.2.2 / RadixArk mixed NVFP4/FP8 / experimental TP2 / MTP k=3 identity는 evidence로만 보존한다.

#### 2.3.2 Ornith 1.5 9B SKINNY [UNSUPPORTED]
- pinned v100-skinny v1.1 standalone model contract가 없다.
- current project에서는 C1/C2 실행 대상으로 예약하지 않는다.

#### 2.3.3 Ornith 1.5 35B-A3B SKINNY [UNSUPPORTED]
- pinned v100-skinny v1.1 standalone model contract가 없다.
- current project에서는 C1/C2 실행 대상으로 예약하지 않는다.

#### 2.3.4 Gemma4 26B-A4B SKINNY [UNSUPPORTED]
- pinned v100-skinny v1.1 standalone model contract가 없다.
- current project에서는 C1/C2 실행 대상으로 예약하지 않는다.

## 3. C2 — 독립적인 128K 에이전트 2개 [TODO]

공통 선행 조건:
- 동일한 exact lane이 C1 128K를 PASS해야 한다.
- 단, C2 capacity 한계 자체를 확인하기 위한 의도적인 failure-boundary 실험은 예외로 한다.
- `workloads/concurrency/v1.json`을 사용한다.
- Project A와 Project B는 서로 무관한 프로젝트이며 prompt hash가 달라야 한다.
- 인위적으로 큰 shared prefix를 만들지 않는다.

### 3.1 Shared TP2 llama.cpp

공통 설정:
- `parallel=2`.
- `ctx-size=262144`.
- `kv-unified`.
- `kv-unified-per-slot=131072`.

#### 3.1.1 Qwen3.8-27B [TODO after 2.1.1]
- C1을 PASS한 `TARGET`, `NGRAM` lane만 C2로 승격한다.
- `MTP`, `MTP_NGRAM`은 범위 밖이다.

#### 3.1.2 Ornith 1.5 9B [TODO after 2.1.2]
- C1을 PASS한 `TARGET`, `NGRAM`, `MTP`, `MTP_NGRAM` lane만 C2로 승격한다.

#### 3.1.3 Ornith 1.5 35B-A3B [TODO after 2.1.3]
- C1을 PASS한 `TARGET`, `NGRAM`, `MTP`, `MTP_NGRAM` lane만 C2로 승격한다.

#### 3.1.4 Gemma4 26B-A4B [TODO after 2.1.4]
- C1을 PASS한 `TARGET`, `NGRAM` lane만 C2로 승격한다.
- `MTP`는 C1 `FAIL_STARTUP`, `MTP_NGRAM`은 pinned runtime에서 동일 draft-startup dependency 때문에 `UNSUPPORTED`이므로 C2 대상에서 제외한다.

### 3.2 Shared TP2 1Cat-vLLM STOCK

공통 설정:
- TP2.
- `max_model_len=131072`.
- `max_num_seqs=2`.
- C1에서 검증된 exact artifact/runtime configuration을 그대로 사용한다.

#### 3.2.1 Qwen3.8-27B STOCK [TODO after 2.2.1]
- C1 128K PASS 후 동일 STOCK lane을 C2로 승격한다.

#### 3.2.2 Ornith 1.5 9B STOCK [BLOCKED by 2.2.2]
- V100 runtime compatibility와 C1 128K를 먼저 PASS해야 한다.
- PASS 전에는 C2를 예약하지 않는다.

#### 3.2.3 Ornith 1.5 35B-A3B STOCK [BLOCKED by 2.2.3]
- V100 runtime compatibility와 C1 128K를 먼저 PASS해야 한다.
- PASS 전에는 C2를 예약하지 않는다.

#### 3.2.4 Gemma4 26B-A4B STOCK [BLOCKED by 2.2.4]
- exact artifact, V100 runtime compatibility, C1 128K를 순서대로 확정해야 한다.
- PASS 전에는 C2를 예약하지 않는다.

### 3.3 v100-skinny SKINNY

#### 3.3.1 Qwen3.8-27B SKINNY [CLOSED BY WBS 1.4]
- `FAIL_OOM_MODEL_LOAD`가 server boot 이전에 확정됐으므로 C2를 실행하지 않는다.

#### 3.3.2 Ornith 1.5 9B SKINNY [UNSUPPORTED]
- WBS 2.3.2의 unsupported verdict를 유지하며 C2를 실행하지 않는다.

#### 3.3.3 Ornith 1.5 35B-A3B SKINNY [UNSUPPORTED]
- WBS 2.3.3의 unsupported verdict를 유지하며 C2를 실행하지 않는다.

#### 3.3.4 Gemma4 26B-A4B SKINNY [UNSUPPORTED]
- WBS 2.3.4의 unsupported verdict를 유지하며 C2를 실행하지 않는다.

### 3.4 공통 C2 판정 및 측정

runnable한 3.1/3.2 lane에서 다음 항목을 각각 분리해서 기록한다.
- 두 request가 모두 admission 되었는가.
- 두 context가 동시에 resident 상태였는가.
- sampled runtime state 기준 실제 active decode overlap이 있었는가.
- queue/preemption 동작(llama.cpp requests_processing/requests_deferred + slots, vLLM num_requests_running/num_requests_waiting).
- request별 성능 및 aggregate 성능.

`QUEUE_ONLY`를 `PASS_C2_ACTIVE`로 판정해서는 안 된다.

## 4. Ornith 1.5 9B — 1GPU×2 + LiteLLM 실배포 topology [TODO]

이 topology는 단순 fallback이 아니라 정식 배포 후보로 취급하며, **LiteLLM까지 포함한 전체 서빙 경로**를 테스트한다.

1GPU에서 128K compatibility를 증명한 모든 런타임 lane(필수 llama.cpp lane 전체, exact Ornith 9B artifact가 확정된 STOCK 1Cat 포함)에 대해:
- GPU0 → Server A.
- GPU1 → Server B.
- Server A/B → 동일 LiteLLM model group.
- Project A/B의 measured request는 backend 주소를 직접 선택하지 않고 **동일한 LiteLLM endpoint**로만 전송한다.
- LiteLLM은 least-busy routing, backend별 max_parallel_requests=1, num_retries=0을 사용한다.
- backend 직접 호출은 tokenizer/health/diagnostic evidence 수집에만 허용한다.
- backend tokenizer receipt에 사용한 `chat_template_kwargs`를 LiteLLM 경로에서도 `extra_body`로 동일하게 전달해 실제 measured prompt와 token receipt가 어긋나지 않게 한다.

C1도 실제 운영 구조를 그대로 반영해 Server A/B와 LiteLLM을 모두 실행한 상태에서 단일 request를 gateway로 보낸다. C2는 독립적인 두 request를 같은 gateway endpoint로 동시에 release한다.

llama.cpp lane이 1GPU에 적재 가능한 경우 다음을 모두 평가한다.
- TARGET.
- NGRAM.
- MTP.
- MTP_NGRAM.

STOCK 1Cat은 TP1 server 2개를 GPU0/GPU1에 각각 격리하고, server당 max_model_len 131072 / max_num_seqs 1로 실행한 뒤 동일 LiteLLM gateway 뒤에 둔다.

C2 ACTIVE 판정에는 두 request의 overlapping decode lifetime과 함께 다음 중 하나 이상의 runtime-side routing evidence가 필요하다.
- backend A/B가 공통 decode window에서 각각 processing>=1.
- LiteLLM 응답의 x-litellm-model-id 또는 x-litellm-model-api-base가 두 request에서 서로 다른 deployment를 가리킴.

Shared TP2와 다음 항목을 비교한다.
- C1 128K end-to-end 성능(LiteLLM overhead 포함).
- 두 개의 128K session 동시 수용 여부.
- TTFT.
- 에이전트별 decode 성능.
- aggregate throughput.
- peak VRAM.
- failure isolation.
- 운영 단순성.
- raw config/report/CSV에 LiteLLM version/commit/image/routing identity가 보존되는지.

## 5. 성능 비교 및 lane 축소 [TODO]

capacity/correctness가 유효한 설정만 성능 비교 대상으로 포함한다. 지속적인 C2 decode 측정에는 workloads/performance/v1.json을 사용한다. 이 workload는 output 4K를 예약하고 실제 1K 이상 출력을 요구하며, NGRAM 비교가 단순 반복 문자열에 과도하게 유리하지 않도록 section별 identifier를 다르게 만든다.

### 5.1 llama.cpp
동일한 model/artifact/KV/topology 조건에서 비교한다.
- TARGET vs NGRAM.
- MTP vs MTP_NGRAM.
- 지원되는 경우 TARGET vs MTP.
- C1 대비 C2 성능 저하.

### 5.2 1Cat-vLLM

현재 하드웨어에서 성능 비교 대상으로 승격할 수 있는 것은 C1/C2를 PASS한 STOCK lane이다.

Qwen3.8 SKINNY는 WBS 1.4에서 `FAIL_OOM_MODEL_LOAD`로 종료됐으므로 현재 2×V100-16GB에서는 throughput A/B 대상으로 포함하지 않는다. SKINNY 결과는 runtime/kernel bootstrap PASS와 model-load OOM이라는 terminal preflight evidence로 보존한다.

향후 다른 하드웨어에서 SKINNY가 실제 서빙에 성공하더라도 checkpoint, KV, speculative, runtime identity 차이를 명시하며 STOCK과의 차이를 단순 kernel-only causal A/B로 해석하지 않는다.

### 5.3 Metrics
가능한 경우 다음 항목을 보존한다.
- TTFT.
- prefill tok/s.
- mean request decode tok/s.
- aggregate decode tok/s.
- end-to-end output tok/s.
- batch wall time.
- GPU0/GPU1 VRAM.
- power.
- temperature.
- clocks.
- speculative acceptance evidence.

### 5.4 Qwen3.8-27B 1Cat-vLLM 추가 최적화 특성화

이 섹션은 기존 C1/C2 acceptance scope를 변경하지 않는 supplemental experiment다.
WBS 2.2.1 및 3.2.1의 STOCK target-only 결과는 그대로 유지하며,
해당 결과가 완료된 이후 Qwen3.8-27B의 추가적인 speculative/runtime 최적화 가능성을 별도로 측정한다.

참고 사례:
- `skrodahl/qwen38-27B-dual-rtx5060`
- 2× RTX 5060 Ti 16GB / TP2 / Qwen3.8-27B NVFP4
- FP8 KV, MTP k sweep, long-context decode, KV-capacity 및 CUDA Graph 영향 측정

이 사례의 수치는 Blackwell 환경의 결과이므로 V100 성능 기대값으로 사용하지 않는다.
실험 설계 참고자료로만 사용한다.

#### 5.4.1 MTP sweep

기존 STOCK target-only 결과를 baseline(k=0)으로 보존한다.

1Cat-vLLM에서 현재 Qwen3.8-27B artifact/runtime 조합이 Native MTP를 지원하고
추가 VRAM budget 안에서 실행 가능한 경우에만 다음 supplemental configuration을 수행한다.

- MTP k=2
- MTP k=4

필요한 경우 최적점 확인을 위해 k=3을 추가할 수 있다.

측정:
- decode tok/s
- speculative acceptance
- accepted tokens/step
- peak VRAM
- KV capacity
- TTFT
- prefill tok/s
- output validity

MTP configuration은 기존 C1/C2 STOCK PASS/FAIL을 대체하거나 수정하지 않는다.

#### 5.4.2 Context-depth decode profile

target-only와 WBS 5.4.1에서 가장 유효했던 MTP configuration을 대상으로
live context 증가에 따른 decode degradation을 측정한다.

고정 checkpoint:
- near-empty / short context
- 32K live context
- 128K live context

각 depth에서 동일한 output workload를 사용한다.

측정:
- target decode tok/s
- effective speculative decode tok/s
- acceptance
- VRAM
- KV usage
- power / clocks

목적은 128K capacity PASS 여부를 다시 판정하는 것이 아니라,
실제 long-running coding-agent session에서 context 증가에 따른 성능 저하를 정량화하는 것이다.

#### 5.4.3 Runtime memory / KV budget characterization

각 추가 configuration의 server startup evidence에서 가능한 경우 다음을 기록한다.

- model weight allocation
- non-model/runtime allocation
- CUDA Graph allocation
- speculative decoding allocation
- available KV cache
- KV token capacity

최소 비교:
- target-only
- MTP k=2
- MTP k=4

`max_num_seqs`와 `max_model_len` 선언값만으로 동시 수용 capacity를 추정하지 않고,
실제 KV token capacity 및 measured C1/C2 결과와 구분한다.

#### 5.4.4 Batched-token sensitivity

현재 1Cat-vLLM runtime에서 대응 옵션이 지원되는 경우에만 수행한다.

baseline runtime configuration을 유지한 채:
- current/default value
- 4096

를 비교한다.

측정:
- startup VRAM
- KV capacity
- prefill tok/s
- decode tok/s
- 128K request viability

5060 Ti 사례의 4096 값을 V100의 정답으로 간주하지 않는다.

#### 5.4.5 Output integrity / CUDA Graph 확인

추가 speculative 또는 graph configuration에서는 throughput뿐 아니라
실제 출력 정상성을 함께 검증한다.

다음을 FAIL로 취급한다.
- empty response
- truncated response
- malformed tool call / structured output
- obvious repetition loop
- silent corruption
- server process는 생존했으나 요청 결과가 invalid한 경우

CUDA Graph mode 변경이 필요한 경우에는 새로운 experiment ID를 사용하고
기존 STOCK 결과와 별도 configuration으로 기록한다.

#### 5.4.6 Supplemental 결과 판정

이 섹션의 결과는 기존 C1/C2 verdict를 변경하지 않는다.

결과는 다음 용도로만 사용한다.
- production STOCK configuration의 후속 최적화 후보 선정
- long-context performance degradation 파악
- speculative decoding의 VRAM/throughput trade-off 파악
- 최종 배포 설정에서 target-only와 MTP 중 선택할 근거 제공

## 6. 최종 배포 결정 [TODO]

최종 보고서는 다음 세 가지 질문에 답해야 한다.
1. 단일 128K single-agent 프로젝트를 안정적으로 실행할 수 있는가?
2. 독립적인 128K 프로젝트 2개를 동시에 resident 상태로 유지하고 실제로 동시에 실행할 수 있는가?
3. PASS한 구성 중 일상적인 coding-agent 운영에 가장 실용적인 topology는 무엇인가?

다음을 반드시 포함한다.
- exact model/runtime/quant/KV/spec/topology.
- C1 결과.
- C2 resident 결과.
- C2 active 결과.
- 측정 성능.
- 운영상 제약 및 주의점.

먼저 서빙 가능성을 검증한다. 모델 품질과 coding-agent 실사용성은 그 이후 별도의 최종 판단 요소로 다룬다.

## 실행 규칙
- 별도 승인이 없는 한 선언된 configuration당 measured execution은 1회만 수행한다.
- 실패 후 context, quantization, KV, speculative method, topology를 조용히 변경해서는 안 된다.
- diagnostic 96K/64K 재실행은 새로운 experiment ID를 사용한다.
- UNSUPPORTED는 유효한 최종 결과다.
- 과거 qwen3.8-bench 결과는 이 저장소에서 PASS로 인정하지 않는다.
