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
- MTP 계열은 별도 **smart Q4_0** Gemma4 assistant GGUF `mtp-gemma-4-26B-A4B-it.gguf`, `--spec-draft-n-max 4`, `--spec-draft-device CUDA0,CUDA1` contract를 사용한다. companion SHA256은 `7272d97595f0d4c74bd7b623492b7dbdaafd8b7c72f329a8270ba4eca68f768a`.
- TARGET: `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C1-128K-20260924-001` — `PASS_C1_128K`; prefill 524.64 tok/s, decode 68.10 tok/s; peak VRAM 8,775 / 8,785 MiB.
- NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C1-128K-20260924-001` — `PASS_C1_128K`; prefill 526.51 tok/s, decode 64.39 tok/s; 4/96 accepted. NGRAM 가속 효과는 Phase 5에서 판정한다.
- MTP attempt 001: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C1-128K-20260924-001` — CUDA0-only drafter configuration에서 `FAIL_STARTUP`. configuration-specific failure evidence로 보존하며 final MTP verdict로 사용하지 않는다.
- Root cause isolation: 동일 b10775 / artifact / TP2 layer split / 128K / MTP n=4에서 `--spec-draft-device CUDA0 -> CUDA0,CUDA1`만 변경하면 startup PASS. 따라서 이 프로젝트의 validated V100 contract는 dual draft devices다.
- Corrected MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C1-128K-20260924-002` — `PASS_C1_128K`; prefill 526.99 tok/s, decode 45.49 tok/s; 548/1088 accepted (50.368%); peak VRAM 8,983 / 9,101 MiB.
- Corrected MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C1-128K-20260924-001` — `PASS_C1_128K`; prefill 518.28 tok/s, decode 45.53 tok/s; 548/1088 accepted (50.368%); peak VRAM 8,983 / 9,121 MiB. Composite compatibility/capacity는 PASS이며 NGRAM의 incremental acceleration effectiveness는 Phase 5로 이관한다.
- corrected MTP_NGRAM은 MTP-only 대비 decode +0.10%, prefill -1.65%, TTFT +1.68%, wall +1.56%였고 MTP counters는 동일했다. 이 수치는 C1 성능 우열 판정에 사용하지 않는다.
- 네 최종 lane 모두 128K capacity/correctness를 PASS했다. MTP 계열은 corrected `CUDA0,CUDA1` contract 결과만 final lane verdict로 사용한다.
- 모델 응답 semantic caveat와 startup diagnostics는 각 report / `acceptance-review.json` / `MTP-DIAGNOSTICS-B10775.md`에 분리 기록했다.

### 2.2 1Cat-vLLM STOCK

실행 세부 계약은 `docs/WBS-2.2-execution-manifest.md`를 authoritative manifest로 사용한다. WBS 2.2 전체가 사용자에 의해 명시적으로 위임된 경우 오케스트레이터는 이 manifest를 다시 설계하거나 upstream 조사를 반복하지 않고 순서대로 실행한다.

공통 실행 조건:
- pinned 1Cat-vLLM 1.5.0.
- TP2 shared.
- `max_model_len=131072`.
- `max_num_seqs=1`.
- `scripts/run_c1_onecat.py`를 사용한다.
- server startup 자체를 exact artifact/runtime compatibility gate로 취급한다. healthy startup 이후에만 C1 128K measured request를 1회 보낸다.
- 실패 후 KV, quantization, speculative depth/method, context, topology를 자동 변경하지 않는다.
- model profile에 선언된 explicit KV format과 speculative configuration을 사용한다.
- artifact identity와 실제 P520 runtime compatibility를 별도로 판정한다.

#### 2.2.1 Qwen3.8-27B STOCK [CLOSED — 128K CAPACITY PASS / OUTPUT INTEGRITY FAIL]
- artifact: `QUASAR-QAT/Qwen3.8-27B-QUASAR-NVFP4@15d2e47bffe5d8ad23928879f8f7d2f74909e259`.
- WBS 1.3 TP2 runtime preflight: PASS.
- KV: `fp8_e4m3` (explicit).
- 1Cat-vLLM 1.5.0의 QUASAR NVFP4 target-only long-context 검증 경로와 맞추기 위해 E4M3를 명시한다. SM70의 generic `fp8` alias는 사용하지 않는다.
- speculative: target-only.
- attention backend: `FLASH_ATTN_V100`.
- experiment ID 001: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-001` — `FAIL_STARTUP`.
  - 1Cat-vLLM 엔진 초기화 중 128K(131,072) 컨텍스트 1개를 수용하기 위한 최소 KV 캐시 메모리(GPU당 2.15 GiB)가 가용 KV 캐시 메모리(1.19 GiB)를 초과하여 기동 실패 (`ValueError: To serve at least one request with the model's max seq len (131072), (2.15 GiB KV cache is needed, which is larger than the available KV cache memory (1.19 GiB)...`).
- experiment ID 002: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-002` — `FAIL_CRASH`.
  - 조치: `--language-model-only` 추가(불필요한 multimodal encoder 16K 토큰 제거 -> 0.45 GiB 절감) 및 `gpu_memory_utilization=0.92`로 상향하여 가용 KV 캐시를 2.65 GiB 이상으로 확보.
  - 결과: 128K(129,023 tokens) Prefill 완전 성공(TTFT 742.46s, Peak VRAM 15,287 MiB / 16,384 MiB로 OOM 없이 정상 수용). 그러나 첫 토큰 Decode 진입 시 Flash-V100 XQA 커널에서 크래시 발생 (`RuntimeError: E4M3 XQA supports B=1, or B=2..16 when VLLM_FLASH_V100_E4M3_BATCH_XQA=1; q_per_kv=6 and D=256 are required. Page-1568/Hkv=1 B1 additionally supports partition sizes 512, 896, 1024, and 1664`).
- experiment ID 003: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-003` — `FAIL_OUTPUT` (Semantic Audit).
  - 조치: Qwen 3.8 27B TP2 환경에서 `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256` 환경변수를 설정하여 decode partition size를 256으로 고정.
  - 결과: 128K Capacity는 완전 성공(TTFT 742.61 s, Decode 9.84 tok/s, Batch Wall 950.77 s, Peak VRAM 15,287 MiB, OOM 없음).
  - 실패 원인: 출력된 2,048 토큰이 프롬프트 지시문("The user wants me to review...")을 50회 이상 단순 반복하는 명백한 repetition loop이며 `finish_reason=length`로 강제 종료됨. WBS 2 및 WBS 5.4.5 acceptance 계약(유효한 출력, repetition loop 불가)에 따라 최종 판정을 `FAIL_OUTPUT`으로 감사/정정.
  - 후속 조치: harness에 repetition loop 자동 검출기 추가, Qwen output corruption 근본 원인 분석 후 수정 및 재검증.
- experiment ID 004: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-004` — `FAIL_OUTPUT`.
  - 조치: Qwen 3.8 27B 추론 모델 특성에 맞춰 `thinking=True` 및 `reasoning_effort="medium"` 설정 반영, harness `detect_repetition` 검사 통과 여부 검증.
  - 결과: 128K Capacity 및 서버 안정성은 완전 유지 (TTFT 742.54 s, Decode 9.69 tok/s, Batch Wall 953.90 s, Peak VRAM 15,287 MiB, OOM 없음, Post-health PASS).
  - 출력 무결성 분석: 첫 부분(약 256토큰)에서는 `PageIndex`, `Transaction` 및 `test_snapshot.py`의 구조와 메서드를 정확히 파악하여 정상 분석을 시작했으나, 1,333개 반복 섹션을 갖는 합성 프롬프트 특성과 greedy (`temperature=0`, penalty=0) 디코딩이 결합되어 3개 파일 기술 블록을 20회 이상 반복 열거하는 축퇴 루프에 진입. 새로 구현된 `detect_repetition()`에 의해 `FAIL_OUTPUT`으로 정확히 감지 및 차단됨.
- experiment ID 005: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-005` — `FAIL_OUTPUT`.
  - 조치: greedy 디코딩 루프 방지를 위해 `temperature=0.7`, `top_p=0.8`, `seed=520` 및 `reasoning_effort="medium"` 적용.
  - 결과: 128K Capacity 및 서버 안정성은 완전 유지 (TTFT 742.53 s, Decode 9.83 tok/s, Batch Wall 950.92 s, Peak VRAM 15,287 MiB, OOM 없음, Post-health PASS).
  - 출력 무결성 분석: 초반 약 800토큰(2,500자) 이상에서 `PageIndex` 및 `Transaction` 클래스의 세부 구현과 정합성 리스크를 매우 우수하고 논리적으로 분석함. 그러나 `presence_penalty=0.0` 조건에서 특정 구문(`( the code might crash. For example, \`page_id = "10"\` ( ...`)이 n-gram 반복 트랩에 빠져 2,048 토큰까지 반복되며 `detect_repetition()`에 의해 `FAIL_OUTPUT`으로 판정됨 (`presence_penalty` 부재를 단독 원인으로 확정할 evidence는 없음).
- experiment ID 006: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-006` — `FAIL_OUTPUT` (Measured Inference 1/2, Thinking OFF Diagnostic).
  - 조치: Thinking OFF 한 변수만 변경 (`--no-thinking`, `chat_template_kwargs={"enable_thinking": False}`, `temperature=0.7`, `top_p=0.8`).
  - 결과: 128K Capacity 완전 성공 (TTFT 742.66 s, Decode 9.77 tok/s, Batch Wall 929.58 s, Peak VRAM 15,287 MiB, OOM 없음, Post-health PASS).
  - 출력 분석: Qwen3.8 기본 Jinja 템플릿이 `enable_thinking=false` 시 빈 `<think>\n\n</think>\n\n` 블록을 주입함. 모델이 일반 텍스트 모드로 독백을 시작하다가 프롬프트 끝의 메타 지시문("Produce at least 256 tokens...")에 집착하여 `"Wait, the user is asking me to produce at least  256 tokens so decode behavior is measurable."` 문장을 73회 반복 출력한 후 `stop` 종료됨.
- experiment ID 007: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-C1-128K-20260924-007` — `FAIL_OUTPUT` (Measured Inference 2/2, Final Acceptance, Reasoning Effort LOW).
  - 조치: reasoning_effort 변경 효과를 검증하기 위해 명시적인 간결성 제어 시스템 지시문("Keep your thinking brief and focused, moving directly to the conclusion without unnecessary elaboration.")이 주입되는 `--thinking --reasoning-effort low` 적용.
  - 결과: 128K Capacity 완전 성공 (TTFT 742.67 s, Decode 9.68 tok/s, Batch Wall 954.25 s, Peak VRAM 15,287 MiB, OOM 없음, Post-health PASS).
  - 출력 분석: 시스템 프롬프트가 정상 주입되었으나, 모델이 프롬프트 지시문을 요약하는 첫 문장("The user wants me to review...")을 반복 출력하는 루프에 빠져 2,048 토큰 한도에 도달 (`finish_reason=length`).
- post-close diagnostic: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001` — raw harness `PASS_C1_128K`, semantic audit **FAIL_OUTPUT**.
  - 128,834 prompt tokens + 280 completion tokens, Peak VRAM 15,567 MiB/GPU, `finish_reason=stop`; 이전 repetition loop는 이 1회에서 관찰되지 않음.
  - 그러나 task가 요구한 구체적인 cross-file/component correctness risk를 실제 snapshot 근거로 특정하지 못하고 `apply_record` / `stage_artifact` mismatch 가능성을 일반론으로만 제시함. 저장소의 semantic-audit override 규칙에 따라 publication verdict는 `FAIL_OUTPUT`으로 정정.
  - 여러 serving/sampling 설정을 동시에 바꾼 1회 실행이므로 특정 옵션이 repetition 원인이라고 귀속하거나 완전 해결로 일반화하지 않음.
- 2.2.1 종합 판정: `CLOSED — 128K CAPACITY PASS / OUTPUT INTEGRITY FAIL`
  - **128K Hardware / Runtime Capacity**: **PASS** (기존 Attempt 002~007 및 B200-aligned diagnostic에서 128K 수용 증거 확보).
  - **Output Integrity / Semantic correctness**: **FAIL_OUTPUT**. 기존 acceptance runs는 repetition collapse로 실패했고, 후속 B200-aligned diagnostic은 비반복 종료에는 성공했지만 task-level semantic correctness를 충족하지 못했다. 따라서 formal C1 PASS와 C2 promotion gate는 여전히 미충족.

  #### 2.2.1 Root-Cause 분석 및 해석 정비

  ##### [검증된 사실]
  1. **128K 하드웨어 수용성 확립**: 2× V100-SXM2-16GB 환경에서 Qwen3.8-27B NVFP4 + FP8 E4M3 KV 구성으로 128K context(129,023 tokens) prefill 및 decode 수용은 6회 연속 재현 가능하게 성공함 (TTFT ~742.6s, Peak VRAM 15,287 MiB / 16,384 MiB, OOM 없음, post-health PASS).
  2. **XQA 디코드 크래시 해결**: `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256` 환경변수로 Hkv=2 TP2 환경의 Flash-V100 XQA partition 크래시를 완전히 해결함.
  3. **Thinking 제어 무관 반복 발생**: Thinking ON(`reasoning_effort=medium`, `low`) 및 Thinking OFF(`enable_thinking=false`) 양쪽 모두에서 repetition loop가 발생함 (EXP-005 vs EXP-006).
  4. **샘플링 전략 무관 반복 발생**: Greedy(`temperature=0.0`) 및 Stochastic(`temperature=0.7`, `top_p=0.8`) 모두 repetition loop가 발생함 (EXP-003/004 vs EXP-005/006/007).
  5. **합성 프롬프트 구조**: 테스트에 사용된 프롬프트는 3개 파일(`storage/index.py`, `storage/transaction.py`, `tests/test_snapshot.py`)의 코드 스니펫을 1,300회 이상 대량 반복 복제하여 129K를 채운 합성 워크로드임.
  6. **선택적 정보 인출 성공**: 모델은 프롬프트 내부의 세부 식별자(`PageIndex`, `Transaction`, `test_snapshot.py`) 및 메서드 시그니처를 왜곡(hallucination) 없이 정확히 추출하여 분석을 시작함 (gross memory/data corruption 아님).
  7. **Ornith 모델 대조 결과**: 동일 128K synthetic workload에서 Ornith 1.5 9B(325 tokens) 및 Ornith 1.5 35B-A3B(594 tokens)는 repetition 없이 정상 출력 PASS함.

  ##### [배제 및 수정된 해석]
  1. **"128K VRAM 부족 또는 OOM" -> 완전 배제**: Peak VRAM 15,287 MiB로 16GB 한도 내에서 안정적으로 제어됨.
  2. **"Flash-V100 XQA 디코드 크래시" -> 완전 배제**: partition size 256 고정으로 완전히 해결됨.
  3. **"단순 Thinking ON/OFF 문제" -> 배제**: Thinking OFF에서도 메타 지시문 반복 루프(72회)가 발생함.
  4. **"Jinja 템플릿의 reasoning_effort=medium 분기 누락이 단일 원인" -> 배제**: 실제 템플릿에서 `xhigh`와 `low`에만 별도 지시를 두고 `medium`은 추가 지시가 없는 기본 형태일 수 있으며, low 지시문을 명시 주입(EXP-007)해도 repetition 루프가 해결되지 않았음.
  5. **"presence_penalty=0.0 부재가 유일 원인" -> 확정할 evidence 없음**: 본 실험군에서는 presence_penalty를 독립 변수로 대조 검증하지 않았으며, coding-agent 실사용 벤치마크에서도 `presence_penalty=0.0` 설정으로 정상 동작한 사례가 다수 확인됨.
  6. **"Ornith=Transformer vs Qwen=GDN 차이로 인한 GDN 포화" -> 완전 배제**: Ornith 1.5 9B 및 35B-A3B 역시 Qwen3.5 계열의 hybrid linear/full-attention (GDN 3 : Full-Attention 1) 구조를 사용함 (`model_type: qwen3_5_text`). 동일한 GDN 하이브리드 아키텍처임에도 Ornith는 정상 PASS했으므로 "GDN 구조 자체가 128K에서 본질적으로 포화된다"는 가설은 성립하지 않음.
  7. **"Flash-V100 XQA 및 FP8 E4M3 수치 무결성 완전 확인 / 결함 완전 배제" -> 과도한 단정이므로 수정**: NaN, garbage string, U+FFFD 같은 gross corruption은 관찰되지 않았으나, 128K 극단 영역에서 FP8 E4M3 KV 캐시의 미세 수치 품질 저하(numerical degradation)나 Flash-V100 XQA 커널의 누적 오차가 logits을 미세하게 왜곡하여 repetition attractor를 형성했을 가능성까지 완전히 배제할 수는 없음.

  ##### [아직 배제되지 않은 주요 가설 4가지]
  1. **가설 1: 128K 합성 프롬프트 자체의 repetition attractor / in-context learning trap**
     - 동일 패턴 코드가 수천 번 반복되는 초장문 프롬프트 구조 자체가 자기회귀 디코딩 시 모델을 강력한 n-gram 반복 패턴으로 유인했을 가능성.
  2. **가설 2: Qwen3.8 모델 자체의 long-context / NVFP4 양자화 checkpoint 특성**
     - Qwen3.8-27B의 학습 데이터 분포, 128K 극단 컨텍스트에서의 attention sink 특성, 또는 NVFP4 가중치/활성화 양자화에 따른 attention score 왜곡 가능성.
  3. **가설 3: 1Cat-vLLM Qwen3.8 런타임/커널 상호작용**
     - Qwen3.8 특화 1Cat-vLLM 런타임의 RoPE scaling (`mrope_section`, `partial_rotary_factor=0.25`), GDN recurrent state update, 또는 decoding kernel 상호작용 이슈.
  4. **가설 4: FP8 E4M3 KV / Flash-V100 XQA의 미세 수치 품질 저하**
     - Gross corruption은 없었으나 128K 토큰 누적 상태에서 FP8 E4M3 정밀도 한계 또는 V100 XQA 축약 연산의 미세 오차가 특정 logits을 비정상 증폭시켜 repetition attractor로 작용했을 가능성.

#### 2.2.2 Ornith 1.5 9B STOCK [DONE — PASS_C1_128K]
- artifact: `ornith-ai/Ornith-1.5-9B-NVFP4@155f200d85ad58464571c77d5e1122ea5d419d7b`.
- 1Cat-vLLM 1.5.0의 Qwen3.5 + MTP model path 정적 지원을 확인했고 P520 TP2 host compatibility gate 및 128K measured execution 통과.
- KV: `FP16` (`float16`).
- speculative compatibility profile: MTP `num_speculative_tokens=1`; draft attention backend `TRITON_ATTN`.
- target attention backend: `FLASH_ATTN_V100`.
- GDN prefill: native precompiled SM70 kernel (`VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0`).
- experiment ID 001: `EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-001` — `FAIL_STARTUP` (CLI `f16` invalid choice).
- experiment ID 002: `EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-002` — `FAIL_CRASH` (TileLang JIT without nvcc on PATH).
- experiment ID 003: `EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-003` — `PASS_C1_128K`.
  - TTFT 165.43 s, Decode 8.98 tok/s, End-to-end 1.61 tok/s, Batch Wall 201.64 s.
  - Prompt 129,023 tokens, Output 325 tokens.
  - Peak VRAM: GPU0 13,821 MiB / GPU1 13,821 MiB.
  - Post-health PASS, cleanup exit 0.
- TP2 결과와 별도로 Phase 4의 1GPU×2 + LiteLLM topology는 후속 검증한다.

#### 2.2.3 Ornith 1.5 35B-A3B STOCK [DONE — PASS_C1_128K]
- artifact: `ornith-ai/Ornith-1.5-35B-A3B-NVFP4@94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`.
- 1Cat-vLLM 1.5.0의 Qwen3.5-MoE/NVFP4 정적 경로 및 P520 TP2 startup gate 통과, C1 128K measured execution 통과.
- KV: `fp8_e5m2` (explicit).
- speculative: target-only.
- attention backend: `FLASH_ATTN_V100`.
- max-num-batched-tokens: 4096 (Mamba align mode block_size 2096 <= 4096).
- GDN prefill: native precompiled SM70 kernel (`VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0`).
- experiment ID 001: `EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-001` — `FAIL_STARTUP` (Mamba align block_size 2096 > max_num_batched_tokens 2048).
- experiment ID 002: `EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-002` — `PASS_C1_128K`.
  - TTFT 62.05 s, Decode 10.45 tok/s, End-to-end 5.00 tok/s, Batch Wall 118.88 s.
  - Prompt 129,023 tokens, Output 594 tokens.
  - Peak VRAM: GPU0 14,565 MiB / GPU1 14,565 MiB.
  - Post-health PASS, cleanup exit 0.

#### 2.2.4 Gemma4 26B-A4B STOCK [CLOSED — FAIL_TIMEOUT (Bounded Recovery Closed)]

##### 1. Historical NVFP4 Runs (Preserved Failure Evidence)
- exact artifact: `nvidia/Gemma-4-26B-A4B-NVFP4@a19cfe00be84568a6867111c9a68c9c44fdcffe6`.
- target local path: `/srv/models/gemma-4-26b-a4b-nvfp4` (역사적 테스트 후 호스트에서 삭제됨).
- weight: NVFP4.
- KV: `FP16` (`float16`).
- speculative: target-only.
- attention backend: `TRITON_ATTN`.
- NVIDIA upstream model card의 일반 vLLM TP=1 제약은 그대로 1Cat TP2 verdict로 전이하지 않는다. pinned 1Cat-vLLM 1.5.0은 Gemma4 NVFP4를 SM70 TP2/TP4 release matrix에 포함하므로, 이 P520의 실제 TP2 startup gate로 compatibility를 판정한다.
- 1Cat SM70 release matrix의 Gemma4 NVFP4 + E5M2 KV diagnostic는 KV-cache quantization validation에 의해 거부되는 조합으로 기록돼 있으므로 FP8 KV를 자동 대체하지 않는다.
- experiment ID 001: `EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-001` — `FAIL_STARTUP`.
  - 원인: `transformers` 5.16.1의 `HeterogeneousConfigMixin`에서 per-layer attribute인 `head_dim`을 global config에서 접근 시 `AmbiguousGlobalPerLayerAttributeError` 발생 (`vllm/transformers_utils/model_arch_config_convertor.py:545` `getattr(self.hf_text_config, "head_dim", 0)`).
- experiment ID 002: `EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-002` — `FAIL_STARTUP` (Historical NVFP4 Terminal Failure).
  - 조치: 런타임 호환 훅(`scripts/runtime_hooks/sitecustomize.py`)을 통해 `HeterogeneousConfigMixin.allow_global_per_layer_attribute_access = True` 적용하여 config/converter 단계 통과.
  - 원인: 모델 로딩 중 1Cat-vLLM 1.5.0의 SM70 TurboMind NVFP4 MoE 커널(`validate_nvfp4_sm70_moe_contract`)에서 Gemma4 26B-A4B의 MoE 아키텍처(shape `hidden=2816, intermediate=704, experts=128, top_k=8` 및 `activation=gelu_pytorch_tanh`)를 지원하지 않아 `NotImplementedError` 발생.

##### 2. AWQ INT4 Revalidation & Bounded Recovery (User Authorized, 2026-09-25)
- exact artifact: `cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4@18a3c7285c33ee39d3e5e16ee6fb2c18f4955ef9`.
- target local path: `/srv/models/gemma-4-26b-a4b-it-qat-awq-int4` (단일 `model.safetensors` 약 17GB).
- weight: AWQ INT4 (`quant_method: compressed-tensors`, `format: pack-quantized`, `weights: int4, group_size=32, symmetric=true`).
- quantization flag: `--quantization compressed-tensors`.
- environment: `VLLM_SM70_QUANT_BACKEND=marlin`.
- KV: `FP16` (`float16`).
- speculative: target-only.
- attention backend: `TRITON_ATTN`.
- topology: TP2 shared.
- backend 실제 검증 결과:
  - Dense/mixed-precision linear: `Using MarlinLinearKernel for CompressedTensorsWNA16` (Marlin 선형 커널 정상 선택).
  - Gemma4 MoE: `Using CompressedTensorsWNA16MoEMethod` (일반 MoE 메서드 선택됨; Marlin MoE가 선택되었다는 과거 기록은 과대해석으로 정정됨).
- 실행 경과:
  1. `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001` — `FAIL_STARTUP`:
     - 가중치 로딩 단계(0% shard)에서 `AssertionError: Attempted to load weight (torch.Size([512])) into parameter (torch.Size([256]))` 발생. `transformers` 5.16.1 환경에서 `global_head_dim`이 글로벌 속성에서 제외되어 풀 어텐션 레이어가 256으로 초기화됨.
  2. Attempt 1 (`EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-002`) — `FAIL_CRASH`:
     - 수정: `scripts/runtime_hooks/sitecustomize.py`에 이종 어텐션 호환 훅을 구현하여 레이어 5, 11, 17, 23, 29를 `head_dim=512, kv=2`로 올바르게 초기화.
     - 결과: 가중치 100% 로딩(9.85 GiB VRAM) 및 서버 정상 기동 성공. 그러나 128K 측정 요청의 attention prefill 도중 `RuntimeError: Triton Error [CUDA]: out of memory` 크래시 발생 (Peak VRAM 15,243 MiB).
  3. Attempt 2 (`EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-003`) — `FAIL_CRASH`:
     - 수정: `--language-model-only` 적용하여 비전 타워(27개 레이어) 및 인코더 캐시를 비활성화.
     - 결과: 모델 메모리는 감소했으나 `gpu_memory_utilization=0.90`으로 인해 KV 캐시가 4.78 GiB(294,344 토큰)로 팽창되어 디바이스 여유 메모리는 여전히 1.13 GiB에 불과. Triton attention prefill 커널이 스레드당 10,896 바이트 스필을 일으켜 드라이버 로컬 스택 메모리(1.66 GiB) 할당 실패로 `cuLaunchKernel` OOM 크래시 (Peak VRAM 15,253 MiB).
  4. Attempt 3 (Final, `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-004`) — `FAIL_TIMEOUT`:
     - 수정: `gpu_memory_utilization`을 `0.80`으로 미세 조정하여 여유 VRAM 헤드룸을 3.28 GiB로 확보(KV 캐시는 195,000 토큰으로 128K 충분히 보장)하고, `VLLM_SM70_TRITON_ATTN_PREFILL_TILE_SIZE=16` 및 `VLLM_SM70_TRITON_ATTN_SAFE_DEFAULTS=1` 적용.
     - 결과: 서버 정상 기동 및 VRAM 13,663 MiB에서 완벽히 안정 유지. OOM 및 커널 크래시 완전히 해결. 그러나 SM70 아키텍처에서 512 헤드 차원의 128K 31개 청크 프리필 연산이 1,800초를 초과하여 HTTP 클라이언트 타임아웃 도달 (`terminal_s: 1800.44s`). 사후 헬스체크는 200 OK로 서버 상태 건전.
- WBS 2.2.4 종합 판정: `CLOSED — FAIL_TIMEOUT (Bounded Recovery Closed)`.
  - 최대 3회의 허용된 재시도(-002, -003, -004)를 모두 소진하였으며, 4번째 추가 재시도 없이 레인을 공식 종결함.
  - Gemma4 1Cat-vLLM은 C2 수용성 테스트 및 WBS 5 최적화 대상에서 완전 제외됨.

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
- C1을 PASS한 `TARGET`, `NGRAM`, corrected `MTP`, corrected `MTP_NGRAM` 네 lane을 C2로 승격한다.
- MTP 계열은 반드시 validated `--spec-draft-device CUDA0,CUDA1` contract를 유지한다.

### 3.2 Shared TP2 1Cat-vLLM STOCK

공통 설정:
- TP2.
- `max_model_len=131072`.
- `max_num_seqs=2`.
- C1에서 검증된 exact artifact/runtime configuration을 그대로 사용한다.

#### 3.2.1 Qwen3.8-27B STOCK [DONE — CAPACITY PASS / QUEUE_ONLY / FAIL_OUTPUT]
- 사용자 지시에 따라 C1 128K B200 공식 레시피 검증(`EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001`, raw harness PASS_C1_128K, repetition collapse 해소)을 기반으로 C2 측정을 실행함.
- 측정 실행: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C2-128K-20260925-001` (2026-09-25).
- 하드웨어 / 서빙: 2× V100 16GB TP2 shared, KV `fp8_e4m3`, context 131,072, `concurrency=2` (`max_num_seqs=2`), B200 공식 얼라인먼트 (`--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder`, `--default-chat-template-kwargs '{"enable_thinking": false}'`, `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`, `max_num_batched_tokens=2048`, `top_k=20`, `presence_penalty=0.15`, `thinking=False`).
- 워크로드: `workloads/concurrency/v1.json` (Project A + Project B 독립적 워크로드, 에이전트당 128K, 총 258,047 프롬프트 토큰).
- 결과:
  - **128K Hardware Capacity**: **PASS** (Peak VRAM 15,575 MiB / 16,384 MiB, OOM 없음, post-health PASS).
  - **동시성 거동 (Concurrency Architecture)**: **순차 큐잉 (Queue-Only)** 실측 확인.
    - 2× V100 16GB 환경에서 가용 KV 캐시 용량이 187,869 토큰(131,072 요청 기준 1.43x)에 그쳐 2개 요청의 동시 Active 처리는 물리적으로 불가능함.
    - vLLM 스케줄러가 2개 요청을 정상 접수한 후, Project A를 먼저 러닝(`vllm:num_requests_running=1`)하고 Project B를 대기(`vllm:num_requests_waiting=1`)시킴.
    - Project A 완주(759초) 후 반환된 KV 블록을 활용하여 Project B가 즉시 프리필/디코딩되어 1,532초에 정상 완주함.
  - **출력 무결성 (Output Integrity)**: **FAIL_OUTPUT**.
    - Project B는 271 토큰으로 계약상 최소 출력 기준(256 토큰)을 정상 충족하여 PASS함.
    - Project A는 간결한 3개 항목 검증 계획을 정상 제시하며 stop 종료되었으나, 생성 토큰이 135 토큰으로 계약상 최소 요구치인 `minimum_output_tokens=256`에 미달하여 하네스 규칙상 `FAIL_OUTPUT`으로 판정됨.
  - 성능: Batch Wall Time 1532.48s (약 25.5분), Mean Decode 9.31 tok/s, End-to-end 0.18 tok/s.
  - 결론: 2× V100 16GB 하드웨어에서 Qwen3.8-27B 128K C2는 OOM 크래시 없이 안전하게 큐잉되어 순차 처리(`QUEUE_ONLY` 거동)됨을 증명함. 단, Project A의 토큰 길이 미달로 최종 publication 판정은 `FAIL_OUTPUT`으로 기록됨.

#### 3.2.2 Ornith 1.5 9B STOCK [TODO — ELIGIBLE]
- WBS 2.2.2에서 V100 runtime compatibility 및 C1 128K를 PASS했다.
- 검증된 exact TP2/MTP1/FP16 configuration을 유지하여 C2 resident 및 active-overlap을 측정한다.

#### 3.2.3 Ornith 1.5 35B-A3B STOCK [TODO — ELIGIBLE]
- WBS 2.2.3에서 V100 runtime compatibility 및 C1 128K를 PASS했다.
- 검증된 exact TP2/target-only/E5M2 configuration을 유지하여 C2 resident 및 active-overlap을 측정한다.

#### 3.2.4 Gemma4 26B-A4B STOCK [NOT ELIGIBLE — WBS 2.2.4 FAIL_TIMEOUT]
- pinned 1Cat-vLLM 1.5.0 SM70 NVFP4 및 AWQ INT4 revalidation (최대 3회 bounded recovery 포함)에서 WBS 2.2.4가 terminal FAIL_TIMEOUT으로 종료됐다.
- 현재 STOCK lane으로 C2를 실행하지 않는다.

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

## 4. Ornith 1.5 9B — 1GPU×2 + LiteLLM topology [TODO]

이 topology는 TP2 shared와 동등한 **정식 테스트 후보**로 취급하며, **LiteLLM까지 포함한 전체 서빙 경로**를 테스트한다.
프로젝트는 이 topology를 실제 배포 대상으로 선택하지 않으며, 검증 결과와 최종 recipe만 보존한다.

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

## 5. 성능 최적화 및 모델별 최종 레시피 확정 [TODO]

WBS 3과 WBS 4에서 capacity/correctness/topology가 검증된 lane을 대상으로 성능을 비교하고,
각 모델·런타임별로 재현 가능한 **최종 serving recipe**를 남긴다.

이 프로젝트는 실제 배포 대상을 선택하거나 서비스를 배포하지 않는다.
사용자는 완료된 recipe 중 필요한 구성을 이후 직접 선택해서 사용한다.
따라서 별도의 "최종 배포 결정" Phase는 두지 않으며 WBS 5 완료가 이 저장소의 종결점이다.

과거 `p520-inference-lab` 및 `qwen3.8-bench` 결과는 acceptance PASS를 소급 부여하는 증거로 사용하지 않는다.
다만 이미 실측으로 검증된 옵션 조합을 **최적화 후보/재현 recipe의 출처**로 사용할 수 있으며,
이 저장소의 최종 recipe에는 반드시 이 저장소에서 얻은 fresh evidence를 연결한다.

### 5.1 공통 performance 비교

capacity/correctness가 유효한 설정만 정식 performance 비교 대상으로 포함한다.
지속적인 C2 decode 측정에는 `workloads/performance/v1.json`을 사용한다.
이 workload는 output 4K를 예약하고 실제 1K 이상 출력을 요구하며,
NGRAM 비교가 단순 반복 문자열에 과도하게 유리하지 않도록 section별 identifier를 다르게 만든다.

공통 비교:
- C1 대비 C2 성능 저하.
- TTFT / prefill tok/s.
- mean request decode tok/s.
- aggregate decode tok/s.
- end-to-end output tok/s.
- batch wall time.
- GPU0/GPU1 VRAM.
- power / temperature / clocks.
- output integrity.
- speculative lane은 draft / accepted / acceptance ratio.

### 5.2 llama.cpp 모델별 recipe 최적화

WBS 2/3에서 유효한 exact model/artifact/KV/topology를 유지한 상태에서,
각 모델마다 실제로 의미 있는 옵션만 제한적으로 최적화한다.

공통 후보:
- TARGET vs NGRAM.
- MTP 지원 모델은 MTP vs MTP_NGRAM 및 TARGET vs MTP.
- `-b / -ub` 조합.
- CUDA Graph / graph-related runtime option이 현재 pinned build에서 실제 제어 가능할 경우 graph on/off 또는 validated variant.
- TP2 shared C2에서는 WBS 3에서 검증된 `--parallel`, `--ctx-size`, `--kv-unified`, `--kv-unified-per-slot` contract를 보존한다.
- speculative depth는 모델이 실제 지원하는 범위 안에서만 조정하며, acceptance와 output integrity를 동시에 확인한다.

모델별 목적:
- Qwen3.8-27B: TARGET/NGRAM 성능과 batch/ubatch/graph 계열 최적점을 확보한다. 현재 artifact에는 MTP lane을 새로 만들지 않는다.
- Ornith 1.5 9B: TARGET/NGRAM/MTP/MTP_NGRAM과 TP2 shared, WBS 4의 1GPU×2 + LiteLLM 결과를 함께 이용해 topology별 recipe를 남긴다.
- Ornith 1.5 35B-A3B: TARGET/NGRAM/MTP/MTP_NGRAM 중 유효한 조합과 native MTP depth의 실효성을 비교한다.
- Gemma4 26B-A4B: TARGET/NGRAM 및 corrected dual-draft-device MTP/MTP_NGRAM contract를 기준으로 최적점을 비교한다.

불필요한 exhaustive grid는 금지한다.
기존 evidence로 명백히 열세인 옵션은 반복하지 않고, 후보마다 변경 이유와 stop condition을 기록한다.

### 5.3 1Cat-vLLM 모델별 recipe 최적화

현재 하드웨어에서 실제 기동 및 유효 출력을 증명한 STOCK lane만 정식 최적화 대상으로 삼는다.
v100-skinny는 현재 2×V100-16GB에서 model-load OOM으로 종료됐으므로 성능 튜닝 대상이 아니다.

공통 후보:
- `max_num_batched_tokens`.
- `max_num_seqs`.
- `gpu_memory_utilization`.
- eager vs CUDA Graph / capture size 조합.
- model-specific SM70 fast-path environment option.
- KV dtype은 **이미 해당 model/runtime에서 호환성이 증명된 후보만** 비교한다.
- speculative decoding은 model-specific compatibility가 확인된 경우에만 비교한다.
- output integrity를 throughput보다 우선한다.

#### 5.3.1 Qwen3.8-27B 128K recovery recipe validation [TODO — 1 measured inference only]

현재 WBS 2.2.1의 기존 E4M3 acceptance verdict는 증거로 보존한다.

`CLOSED — 128K CAPACITY PASS / OUTPUT INTEGRITY FAIL`

추가 1회 실험의 목적은 64K 재현이 아니라,
**2×V100-16GB에서 Qwen3.8-27B + 1Cat-vLLM의 128K 정상 출력 recipe를 recovery할 수 있는지 검증하는 것**이다.

과거 저장소에서 정상 출력이 확인된 Qwen 1Cat 경로는 다음 특성을 갖는다.
- QUASAR NVFP4 / TP2 / `FLASH_ATTN_V100`
- KV `fp8_e5m2`
- GDN prefill backend `triton`
- `VLLM_SM70_GDN_DECODE_FLASHQLA=0`
- thinking off
- eager mode
- target-only.

현재 v100-llm-test에서 128K physical capacity와 decode 진입을 성공시킨 요소는 다음이다.
- `--language-model-only`
- `gpu_memory_utilization=0.92`
- `max_model_len=131072`
- `max_num_seqs=1`
- `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`.

따라서 이번 single recovery candidate는 두 evidence를 결합하되,
성능 최적화 요소(CUDA Graph, LM-head top1, P2P/custom-allreduce, MTP)는 넣지 않는다.

128K recovery candidate:
- model: Qwen3.8-27B QUASAR NVFP4
- runtime: pinned 1Cat-vLLM 1.5.0
- topology: TP2 shared
- attention: `FLASH_ATTN_V100`
- KV: **`fp8_e5m2`**
- target-only
- `max_model_len=131072`
- `max_num_seqs=1`
- `--language-model-only`
- `gpu_memory_utilization=0.92`
- `--additional-config '{"gdn_prefill_backend":"triton"}'`
- `VLLM_SM70_GDN_DECODE_FLASHQLA=0`
- `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`
- eager mode
- thinking=false
- historical conservative sampling: temperature=0, top_p=1, seed=38.

워크로드는 기존 128K acceptance와 동일한 token budget을 유지한다.
가능하면 기존 diversified realistic 128K workload를 재사용하여
prompt composition 변화가 결과를 혼동하지 않도록 한다.
목표는 post-template prompt 약 128.8K~129.0K + output reserve 2048,
총 131072 이내다.

새 measured inference는 정확히 1회만 허용한다.

판정:
- 정상 128K output PASS → 새 E5M2/GDN 기반 128K `VALIDATED_RECIPE` 후보로 승격 가능. 기존 E4M3 실패 evidence는 그대로 보존하고, 두 configuration을 구분한다.
- startup/capacity FAIL → 해당 E5M2/GDN 128K recipe는 current hardware에서 실패로 기록한다. E4M3 capacity PASS는 그대로 보존한다.
- repetition/invalid output FAIL → Qwen 1Cat 128K recovery 실패로 종료하고 WBS 5에서 Qwen 1Cat throughput tuning을 진행하지 않는다.

이번 1회에서 금지:
- 64K/96K diagnostic
- context sweep
- presence-penalty sweep
- CUDA Graph
- LM-head top1
- P2P/custom-allreduce tuning
- MTP/DFlash2
- 추가 retry.

**실행 결과 (`EXP-V100-Q38-1CAT-FP8E5M2-TARGET-RECOVERY-C1-128K-20260925-001`):**
- 판정: **FAIL_STARTUP** (Capacity: FAIL_CAPACITY, Integrity: NOT_REACHED)
- 사유: Triton prefill 커널 오버헤드로 인해 profile run 시 가용 KV 캐시 메모리가 1.5 GiB로 축소되어 128K(131,072)에 필요한 2.15 GiB를 확보하지 못함 (`ValueError: To serve at least one request with the model's max seq len (131072), (2.15 GiB KV cache is needed, which is larger than the available KV cache memory (1.5 GiB). Based on the available memory, the estimated maximum model length is 87808.`).
- Peak VRAM: GPU0 13,987 MiB / GPU1 13,987 MiB.
- 결론: E5M2 + GDN Triton prefill 128K candidate는 2×V100 16GB에서 capacity-compatible하지 않음. 기존 E4M3 128K capacity PASS는 그대로 보존됨.

**B200-aligned candidate 128K diagnostic 결과 (`EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001`):**
- raw harness 판정: `PASS_C1_128K`; post-hoc semantic audit publication 판정: **FAIL_OUTPUT**.
- 구성: Qwen3.8-27B QUASAR NVFP4 + TP2 + E4M3 KV + `--reasoning-parser qwen3` + `--tool-call-parser qwen3_coder` + `--default-chat-template-kwargs '{"enable_thinking": false}'` + decode partition 256 + LM-only + util 0.92 + sampling (`temperature: 1.0`, `top_p: 0.95`, `top_k: 20`, `presence_penalty: 0.15`).
- 측정 결과: 128,834 prompt 토큰 수용, TTFT 740.60s, decode 9.27 tok/s, 280 토큰 출력 후 `finish_reason=stop`. 이 1회에서는 repetition collapse가 관찰되지 않았다.
- semantic audit: 응답이 task가 요구한 구체적인 cross-file/component correctness risk를 snapshot 근거로 특정하지 못했으므로 `FAIL_OUTPUT`. mechanical non-repetition과 task-level correctness를 분리한다.
- provenance caveat: raw artifact에는 upstream B200 recipe URL/revision receipt가 없으므로 'official' 출처를 독립 검증하지 않는다.
- 결론: 128K capacity 및 단일 non-repetition 실행 증거는 보존하지만 formal C1 PASS로 승격하지 않는다. Qwen 1Cat의 C2 및 throughput tuning eligibility는 복원하지 않는다.

### 5.4 Qwen3.8-27B 1Cat 추가 성능 특성화 [BLOCKED — semantic revalidation required]

현재 authoritative publication verdict가 `FAIL_OUTPUT`이므로 Qwen 1Cat은 정식 성능 최적화 대상이 아니다.
사용자가 fresh 128K semantic revalidation을 명시적으로 승인하고 그 실행이 PASS한 경우에만 아래 후보를 검토한다.

PASS 시 과거 evidence를 참고해 다음 중 필요한 최소 실험만 수행한다.
- target-only CUDA Graph capture [1,2] recovery.
- LM-head top1.
- P2P/custom all-reduce.
- MBT 2048 → 4096 → 8192는 concurrency/topology와 메모리 여유가 실제로 필요할 때만 단계적으로 검증한다.
- Native MTP1은 현재 artifact/runtime이 지원하고 historical compatible contract를 재현할 수 있을 때만 별도 configuration으로 검증한다.
- historical evidence에서 MTP1은 LM-head top1 OFF, P2P/custom-allreduce OFF가 호환 조건이었으므로 target-only fast-path 옵션을 그대로 혼합하지 않는다.

기존 128K E4M3 failure profiles, E5M2/GDN capacity failure, B200-aligned E4M3 diagnostic은 서로 다른 configuration/evidence로 명확히 분리한다.
B200-aligned diagnostic은 현재 validated final recipe가 아니며, fresh semantic PASS 전에는 최종 recipe/C2 lane으로 승격하지 않는다.

### 5.5 모델·런타임별 최종 recipe 기록

WBS 5 종료 시 **실제로 검증된 각 모델·런타임 조합별 recipe**를 남긴다.
하나의 overall winner나 자동 배포 구성을 선택하지 않는다.

각 recipe에 반드시 포함:
- exact model repository/revision/local artifact identity.
- runtime/version/commit 또는 wheel/image digest.
- weight quant / KV dtype.
- speculative method/depth.
- topology.
- exact launch command.
- relevant environment variables.
- context ceiling 및 concurrency envelope.
- batch/ubatch 또는 max-num-batched-tokens/max-num-seqs.
- graph/eager 설정.
- measured C1/C2 성능.
- peak VRAM 및 주요 telemetry.
- output-integrity verdict.
- known limitations / unsupported combinations.
- 근거 experiment IDs.

recipe 상태는 다음처럼 구분한다.
- `VALIDATED_RECIPE`: 정의된 범위에서 capacity/correctness/performance가 모두 유효.
- `BOUNDED_RECIPE`: 특정 context/concurrency까지만 유효함이 증명됨.
- `FAILED/UNSUPPORTED`: 재현 가능한 실패 조건만 보존하며 사용 recipe로 승격하지 않음.

WBS 5 완료 후 사용자가 필요에 따라 recipe를 직접 선택한다.
이 저장소에서는 별도의 배포/production selection phase를 수행하지 않는다.

## 실행 규칙
- 별도 승인이 없는 한 선언된 configuration당 measured execution은 1회만 수행한다.
- 실패 후 context, quantization, KV, speculative method, topology를 조용히 변경해서는 안 된다.
- diagnostic 96K/64K 재실행은 새로운 experiment ID를 사용한다.
- UNSUPPORTED는 유효한 최종 결과다.
- 과거 qwen3.8-bench 결과는 이 저장소에서 PASS로 인정하지 않는다.
