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
## 2. C1 — 128K capacity 및 correctness [DONE]

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

## 3. C2 — 독립적인 128K 에이전트 2개 [DONE — authoritative v2 revalidation]

### 3.0 WBS 3 workload reset (2026-09-25)

기존 `workloads/concurrency/v1.json`은 raw/historical evidence로 보존하지만 WBS 3의 최종 acceptance에는 더 이상 사용하지 않는다.

v1의 구조적 결함:
- 소수 seed block을 약 128K까지 반복하여 long-context repetition bias를 만들었다.
- 실제 결함 존재가 보장되지 않은 코드에 "concrete risk 하나"를 강제하여 unsupported bug를 만들어낼 유인을 만들었다.
- "minimal plan"과 별개로 최소 256 output tokens를 강제하여 짧지만 정상적인 답변도 mechanical FAIL_OUTPUT이 될 수 있었다.
- 기존 harness는 output PASS와 runtime topology를 결합하여 output underfill 시 실제 queue evidence까지 잃을 수 있었다.

WBS 3 authoritative workload는 `workloads/concurrency/v2.json`이다.
- Project A/B 각각 non-padding anchor에 정확히 하나의 pre-registered seeded bug를 둔다.
- semantic oracle은 `workloads/concurrency/v2-ground-truth.json`에 사전 고정한다.
- anchor는 한 번만 포함하고 나머지 128K는 `{{SECTION}}` 기반 semantically-neutral padding으로 채운다.
- 응답은 Root Cause / Failure Trace / executable reproduction / Minimal Fix를 요구한다.
- runtime capacity/concurrency, mechanical output, semantic correctness를 별도 축으로 기록한다.
- 최종 acceptance에는 mechanical PASS와 oracle 기반 semantic PASS가 필요하다.
- `QUEUE_ONLY`를 `PASS_C2_ACTIVE`로 승격하지 않는다.

기존 v1 실험은 삭제하거나 소급 변경하지 않는다. Qwen v1 queue-only와 Ornith 9B v1 active-overlap은 historical diagnostic으로 유지한다.

### 3.1 Shared TP2 llama.cpp [DONE]
- 실행 runner: `scripts/run_c2_llama.py`.
- 공통: `parallel=2`, `ctx-size=262144`, `kv-unified`, `kv-unified-per-slot=131072`.

#### 3.1.1 Qwen3.8-27B [DONE]
- artifact: `UD-Q4_K_M`.
- KV: `Q8_0`.
- 실행 lane: `TARGET`, `NGRAM`.
- TARGET: `EXP-V100-Q38-LLAMA-Q80-TARGET-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 2개 독립 128K 세션(총 256K 컨텍스트) 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 925.17s, Prefill 177.23 tok/s, Mean Decode 4.87 tok/s, Aggregate Decode 1.83 tok/s, End-to-End Output 1.19 tok/s, Batch Wall 1,446.44s (~24.11분).
  - Peak VRAM: GPU0 13,159 MiB / GPU1 14,247 MiB (16GB 한도 내 안정적 수용, OOM 여유 ~2,137 MiB).
  - Output analysis:
    - Project A: 886 tokens 생성, `Transaction.commit` 루프 내 `pending.clear()` 조기 비움 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 842 tokens 생성, `JobQueue._sequence` 비원자적 RMW 및 tiebreaker 중복 문제 완벽 분석 및 재현/수정안 제시 (PASS).
- NGRAM: `EXP-V100-Q38-LLAMA-Q80-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 NGRAM 투기 디코딩 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 925.67s, Prefill 177.08 tok/s, Mean Decode 5.00 tok/s, Aggregate Decode 2.16 tok/s, End-to-End Output 1.43 tok/s, Batch Wall 1,489.30s (~24.82분).
  - NGRAM Speculative 통계: Project A (draft 288, accepted 86, 29.9%), Project B (draft 561, accepted 117, 20.9%).
  - Peak VRAM: GPU0 13,163 MiB / GPU1 14,249 MiB (16GB 한도 내 안정 수용, OOM 여유 ~2,135 MiB).
  - Output analysis:
    - Project A: 886 tokens 생성, `Transaction.commit` 루프 내 `pending.clear()` 조기 비움 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,249 tokens 생성, `JobQueue._sequence` 비원자적 RMW 및 tiebreaker 중복 문제 완벽 분석 및 재현/수정안 제시 (PASS).

#### 3.1.2 Ornith 1.5 9B [DONE]
- artifact: `Q6_K`.
- KV: `FP16`.
- 실행 lane: `TARGET`, `NGRAM`, `MTP`, `MTP_NGRAM`.
- TARGET: `EXP-V100-ORN15-9B-LLAMA-F16-TARGET-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 FP16 KV 캐시로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 264.40s, Prefill 620.03 tok/s, Mean Decode 19.71 tok/s, Aggregate Decode 9.17 tok/s, End-to-End Output 6.09 tok/s, Batch Wall 425.82s (~7.10분).
  - Peak VRAM: GPU0 7,789 MiB / GPU1 8,235 MiB (16GB 한도 내 여유 ~8,149 MiB).
  - Output analysis:
    - Project A: 1,190 tokens 생성, `Transaction.commit` 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,402 tokens 생성, `JobQueue._sequence` 비원자적 RMW 결함 완벽 분석 및 재현/수정안 제시 (PASS).
- NGRAM: `EXP-V100-ORN15-9B-LLAMA-F16-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 NGRAM 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 264.44s, Prefill 715.33 tok/s, Mean Decode 18.22 tok/s, Aggregate Decode 7.76 tok/s, End-to-End Output 5.11 tok/s, Batch Wall 417.21s (~6.95분).
  - NGRAM Speculative 통계: Project A (draft 288, accepted 76, 26.4%), Project B (draft 350, accepted 65, 18.6%).
  - Peak VRAM: GPU0 7,791 MiB / GPU1 8,311 MiB (16GB 한도 내 여유 ~8,073 MiB).
  - Output analysis:
    - Project A: 897 tokens 생성, `Transaction.commit` 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,235 tokens 생성, `JobQueue._sequence` 비원자적 RMW 결함 완벽 분석 및 재현/수정안 제시 (PASS).
- MTP: `EXP-V100-ORN15-9B-LLAMA-F16-MTP-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 native MTP 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 325.09s, Prefill 494.99 tok/s, Mean Decode 22.16 tok/s, Aggregate Decode 7.85 tok/s, End-to-End Output 5.06 tok/s, Batch Wall 509.80s (~8.50분).
  - MTP Speculative 통계: Project A (draft 1,023, accepted 552, **54.0%**), Project B (draft 1,911, accepted 1,048, **54.8%**; 단독 decode **41.29 tok/s** 달성).
  - Peak VRAM: GPU0 7,963 MiB / GPU1 10,009 MiB (16GB 한도 내 여유 ~6,375 MiB).
  - Output analysis:
    - Project A: 894 tokens 생성, `Transaction.commit` 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,686 tokens 생성, `JobQueue._sequence` 비원자적 RMW 결함 완벽 분석 및 재현/수정안 제시 (PASS).
- MTP_NGRAM: `EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 composite `draft-mtp,ngram-simple` 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 324.95s, Prefill 495.74 tok/s, Mean Decode 21.40 tok/s, Aggregate Decode 6.45 tok/s, End-to-End Output 4.11 tok/s, Batch Wall 498.39s (~8.31분).
  - Speculative 통계: Project A (draft 1,173, accepted 558, **47.6%**), Project B (draft 1,554, accepted 747, **48.1%**; 단독 decode **39.83 tok/s**).
  - Peak VRAM: GPU0 7,965 MiB / GPU1 10,071 MiB (16GB 한도 내 여유 ~6,313 MiB).
  - Output analysis:
    - Project A: 879 tokens 생성, `Transaction.commit` 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,168 tokens 생성, `JobQueue._sequence` 비원자적 RMW 결함 완벽 분석 및 재현/수정안 제시 (PASS).
  - 네 lane(TARGET, NGRAM, MTP, MTP_NGRAM) 모두 128K C2 Active Overlap 및 semantic oracle 검증을 완벽하게 통과함.

#### 3.1.3 Ornith 1.5 35B-A3B [DONE]
- artifact: `Q4_K_M`.
- KV: `Q8_0`.
- 실행 lane: `TARGET`, `NGRAM`, `MTP`, `MTP_NGRAM`.
- TARGET: `EXP-V100-ORN15-35B-LLAMA-Q80-TARGET-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 35B MoE 모델 Q8_0 KV 캐시로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 815.97s, Prefill 188.93 tok/s, Mean Decode 15.63 tok/s, Aggregate Decode 3.07 tok/s, End-to-End Output 1.80 tok/s, Batch Wall 1,183.89s (~19.73분).
  - Peak VRAM: GPU0 12,831 MiB / GPU1 12,309 MiB (16GB 한도 내 여유: GPU0 ~3.5 GiB, GPU1 ~4.0 GiB).
  - Output analysis:
    - Project A: 917 tokens 생성, `Transaction.commit` 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,217 tokens 생성, `JobQueue._sequence` 비원자적 RMW 결함 완벽 분석 및 재현/수정안 제시 (PASS, 단독 디코드 29.91 tok/s).
- NGRAM: `EXP-V100-ORN15-35B-LLAMA-Q80-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 NGRAM 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 816.17s, Prefill 188.90 tok/s, Mean Decode 14.56 tok/s, Aggregate Decode 2.83 tok/s, End-to-End Output 1.66 tok/s, Batch Wall 1,183.06s (~19.72분).
  - NGRAM Speculative 통계: Project A (draft 312, accepted 80, 25.6%), Project B (draft 272, accepted 68, 25.0%; 단독 decode 27.83 tok/s).
  - Peak VRAM: GPU0 12,831 MiB / GPU1 12,309 MiB (16GB 한도 내 안정적 수용).
  - Output analysis:
    - Project A: 867 tokens 생성, `Transaction.commit` 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,098 tokens 생성, `JobQueue._sequence` 비원자적 RMW 결함 완벽 분석 및 재현/수정안 제시 (PASS).
- MTP: `EXP-V100-ORN15-35B-LLAMA-Q80-MTP-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 native MTP 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 857.77s, Prefill 180.62 tok/s, Mean Decode 18.20 tok/s, Aggregate Decode 3.50 tok/s, End-to-End Output 2.07 tok/s, Batch Wall 1,251.11s (~20.85분).
  - MTP Speculative 통계: Project A (draft 574, accepted 455, **79.3%**), Project B (draft 888, accepted 677, **76.2%**; 단독 decode **34.97 tok/s**).
  - Peak VRAM: GPU0 12,897 MiB / GPU1 13,737 MiB (16GB 한도 내 여유: GPU0 ~3.4 GiB, GPU1 ~2.6 GiB).
  - Output analysis:
    - Project A: 1,030 tokens 생성, `Transaction.commit` 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,566 tokens 생성, `JobQueue.pop` 비원자적 race 결함 완벽 분석 및 재현/수정안 제시 (PASS).
- MTP_NGRAM: `EXP-V100-ORN15-35B-LLAMA-Q80-MTP-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 composite `draft-mtp,ngram-simple` 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 860.09s, Prefill 180.10 tok/s, Mean Decode 15.43 tok/s, Aggregate Decode 2.70 tok/s, End-to-End Output 1.59 tok/s, Batch Wall 1,240.18s (~20.67분).
  - Speculative 통계: Project A (draft 759, accepted 445, **58.6%**; 단독 decode **29.38 tok/s**), Project B (draft 858, accepted 463, **54.0%**).
  - Peak VRAM: GPU0 12,897 MiB / GPU1 13,737 MiB (16GB 한도 내 여유: GPU0 ~3.4 GiB, GPU1 ~2.6 GiB).
  - Output analysis:
    - Project A: 905 tokens 생성, `Transaction.commit` 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,065 tokens 생성, `JobQueue.pop` 비원자적 race 결함 완벽 분석 및 재현/수정안 제시 (PASS).
  - 네 lane(TARGET, NGRAM, MTP, MTP_NGRAM) 모두 128K C2 Active Overlap 및 semantic oracle 검증을 완벽하게 통과함.

#### 3.1.4 Gemma4 26B-A4B [DONE]
- artifact: `UD-Q4_K_XL`.
- KV: `FP16`.
- 실행 lane: `TARGET`, `NGRAM`, corrected `MTP`, corrected `MTP_NGRAM`; MTP는 validated `CUDA0,CUDA1` draft contract 유지. (참고: 실험 ID의 `20260925` 날짜 표기는 WBS 3 v2 사전 계획 ID 기준이며, 실제 호스트 측정 실행 및 완료 일시는 2026-09-26 UTC임)
- TARGET: `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 FP16 KV 캐시로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 447.02s, Prefill 359.05 tok/s, Mean Decode 21.66 tok/s, Aggregate Decode 4.77 tok/s, End-to-End Output 2.98 tok/s, Batch Wall 667.36s (~11.12분).
  - Peak VRAM: GPU0 10,039 MiB / GPU1 10,537 MiB (16GB 한도 내 여유: GPU0 ~6.0 GiB, GPU1 ~5.5 GiB).
  - Output analysis:
    - Project A: 924 tokens 생성, `Transaction.commit` 루프 내 `pending.clear()` 조기 비움 결함 완벽 분석 및 재현/수정안 제시 (PASS).
    - Project B: 1,068 tokens 생성, `JobQueue.pop` 비원자적 `await asyncio.sleep(0)` race condition 결함 완벽 분석 및 재현/수정안 제시 (PASS).
- NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 NGRAM 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 457.15s, Prefill 353.01 tok/s, Mean Decode 20.33 tok/s, Aggregate Decode 4.86 tok/s, End-to-End Output 3.08 tok/s, Batch Wall 689.16s (~11.49분).
  - NGRAM Speculative 통계: Project A (draft 527, accepted 186, 35.3%), Project B (draft 528, accepted 141, 26.7%; 전체 수락률 31.0%).
  - Peak VRAM: GPU0 10,039 MiB / GPU1 10,607 MiB (16GB 한도 내 안정적 수용).
  - Output analysis:
    - Project A: 1,066 tokens 생성, `Transaction.commit` 루프 내 `pending.clear()` 결함 분석 및 수정안 제시 (PASS).
    - Project B: 1,055 tokens 생성, `JobQueue.pop` 비원자적 race condition 결함 분석 및 수정안 제시 (PASS).
- MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 smart drafter(`mtp-gemma-4-26B-A4B-it.gguf`, `CUDA0,CUDA1`) 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 458.73s, Prefill 354.15 tok/s, Mean Decode 17.61 tok/s, Aggregate Decode 4.66 tok/s, End-to-End Output 2.98 tok/s, Batch Wall 697.62s (~11.63분).
  - MTP Speculative 통계: Project A (draft 1,160, accepted 777, **66.98%**), Project B (draft 1,112, accepted 738, **66.37%**; 전체 수락률 **66.68%**).
  - Peak VRAM: GPU0 10,345 MiB / GPU1 10,981 MiB (Dual draft 로딩에도 16GB 한도 내 여유 확보).
  - Output analysis:
    - Project A: 1,066 tokens 생성, `Transaction.commit` 루프 내 `pending.clear()` 결함 분석 및 수정안 제시 (PASS).
    - Project B: 1,016 tokens 생성, `JobQueue.pop` 비원자적 `await asyncio.sleep(0)` race condition 결함 분석 및 수정안 제시 (PASS).
- MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 composite drafter(`mtp-gemma-4-26B-A4B-it.gguf` + `ngram-simple`) 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
  - TTFT (Batch Mean): 462.43s, Prefill 352.54 tok/s, Mean Decode 17.96 tok/s, Aggregate Decode 4.59 tok/s, End-to-End Output 2.95 tok/s, Batch Wall 703.74s (~11.73분).
  - Speculative 통계: Project A (draft 1,564, accepted 800, **51.15%**), Project B (draft 1,557, accepted 748, **48.04%**; 전체 수락률 **49.60%**).
  - Peak VRAM: GPU0 10,345 MiB / GPU1 11,051 MiB (16GB 한도 내 안전 여유 유지).
  - Output analysis:
    - Project A: 1,058 tokens 생성, `Transaction.commit` 루프 내 `pending.clear()` 결함 분석 및 수정안 제시 (PASS).
    - Project B: 1,016 tokens 생성, `JobQueue.pop` 비원자적 race condition 결함 분석 및 수정안 제시 (PASS).
  - 네 lane(TARGET, NGRAM, MTP, MTP_NGRAM) 모두 128K C2 Active Overlap 및 semantic oracle 검증을 완벽하게 통과함.

### 3.2 Shared TP2 1Cat-vLLM STOCK [DONE — v2 revalidation]
- 공통: TP2, `max_model_len=131072`, `max_num_seqs=2`, C1에서 검증된 exact serving configuration 유지.
- `scripts/run_c2_onecat.py`는 v2 manifest와 semantic-oracle hash를 evidence에 고정한다.

#### 3.2.1 Qwen3.8-27B STOCK [DONE — QUEUE_ONLY / FAIL_OUTPUT]
- B200-aligned E4M3 serving recipe로 v2 experiment `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C2-128K-20260925-002` 실행 완료.
- 판정: `FAIL_OUTPUT` (Queue-only verified, Peak VRAM 15,575 MiB GPU0/1 symmetric, OOM 없음, Post-health PASS).
- Concurrency evidence: `resident: false`, `active_overlap: false`, `queue_only: true` (`peak_processing=1.0`, `peak_waiting=1.0`). 두 개의 128K 요청이 VRAM 한계로 인해 순차 처리됨이 하네스 독립 샘플러로 확정됨.
- Output analysis:
  - Project A: 570 tokens 생성, 최소 토큰 조건(>= 256) 및 포맷 충족하여 PASS.
  - Project B: 165 tokens 생성 후 반복 구문과 함께 조기 중단되어 최소 토큰 요구량(256 tokens) 미달 및 semantic 검증 실패로 `FAIL_OUTPUT`.
- 이 결과는 과거 C1 semantic FAIL 및 C2 queue-only 제약을 재확인함. Qwen3.8 1Cat은 C2 동시 상주(active overlap)가 불가능하며 WBS 5 최적화 대상에서 제외됨.

#### 3.2.2 Ornith 1.5 9B STOCK [DONE — PASS_C2_ACTIVE]
- 동일 TP2/MTP1/FP16 serving contract로 v2 experiment `EXP-V100-ORN15-9B-1CAT-F16-MTP1-C2-128K-20260925-003` 실행 완료.
- 판정: **`PASS_C2_ACTIVE`** (128K C2 capacity, active decode overlap, semantic output 모두 PASS).
- Concurrency evidence: `resident: true`, `active_overlap: true`, `queue_only: false` (`peak_processing=2.0`, `peak_waiting=0.0`). 두 개의 128K 요청이 2× V100 16GB TP2에서 완전히 동시 상주(Peak VRAM 13,901 MiB)하며 큐잉 없이 병렬 디코딩 수행.
- TTFT 310.90s, Mean Decode 9.94 tok/s, Aggregate Decode 15.60 tok/s, Batch Wall 458.71s.
- Output analysis:
  - Project A: 865 tokens 생성, `Transaction.commit` 루프 내 조기 clear 결함 완벽 분석/재현 (PASS).
  - Project B: 1,460 tokens 생성, `JobQueue._sequence` 비원자적 RMW 및 tiebreaker 중복 문제 정확 분석/재현 (PASS).
- Ornith 1.5 9B는 1Cat-vLLM STOCK 환경에서 C2 128K active overlap 및 semantic correctness를 완벽히 통과하여 WBS 5 최적화 자격을 유지함.

#### 3.2.3 Ornith 1.5 35B-A3B STOCK [DONE — PASS_C2_ACTIVE]
- 검증된 TP2/target-only/E5M2 configuration으로 v2 experiment `EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C2-128K-20260925-001` 실행 완료.
- 판정: **`PASS_C2_ACTIVE`** (128K C2 capacity, active decode overlap, semantic output 모두 PASS).
- Concurrency evidence: `resident: true`, `active_overlap: true`, `queue_only: false` (`peak_processing=2.0`, `peak_waiting=1.0` -> 동시 활성 디코드 진입 확인). 2× V100 16GB TP2에서 피크 VRAM 14,557 MiB로 두 개의 128K context 동시 수용.
- TTFT 113.71s, Mean Decode 7.45 tok/s, Aggregate Decode 9.57 tok/s, Batch Wall 284.18s (~4.74분).
- Output analysis:
  - Project A: 947 tokens 생성, `Transaction.commit` 루프 내 `pending.clear()` 조기 순회 중단 결함 완벽 분석 및 재현/수정안 제시 (PASS).
  - Project B: 1,181 tokens 생성, `JobQueue.pop()`의 `await asyncio.sleep(0)` check-then-act race condition 정확 분석 및 재현/수정안 제시 (PASS).
- Ornith 1.5 35B-A3B는 1Cat-vLLM STOCK 환경에서 C2 128K active overlap 및 semantic correctness를 통과하여 WBS 5 최적화 자격을 유지함.

#### 3.2.4 Gemma4 26B-A4B STOCK [NOT ELIGIBLE — C1 FAIL_TIMEOUT]
- 1Cat-vLLM C1 128K가 terminal FAIL_TIMEOUT이므로 v2 C2 대상이 아니다.

### 3.3 v100-skinny SKINNY
- Qwen3.8: CLOSED BY WBS 1.4 (`FAIL_OOM_MODEL_LOAD`).
- Ornith 9B / Ornith 35B / Gemma4: UNSUPPORTED.
- 현재 하드웨어에서 재실행하지 않는다.

### 3.4 공통 C2 판정 및 측정
각 runnable lane에서 API admission/completion, concurrent residency, active decode overlap, queue/preemption, mechanical output, oracle semantic correctness, per-request/aggregate 성능을 독립 기록한다.

runtime concurrency classification은 output PASS 여부와 결합하지 않는다. 한 응답이 FAIL_OUTPUT이어도 sampled evidence가 `peak_waiting>=1`, `peak_processing<=1`이면 scheduler topology는 `QUEUE_ONLY`로 보존한다.

## 4. Ornith 1.5 9B — 1GPU×2 + LiteLLM topology [DONE]

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

C1도 실제 운영 구조를 그대로 반영해 Server A/B와 LiteLLM을 모두 실행한 상태에서 단일 request를 gateway로 보낸다.

C2 measured admission은 `RoutingSettledAdmissionBarrier`를 사용한다:
- 두 measured request 모두 동일 LiteLLM gateway endpoint만 사용하며, backend 직접 선택은 금지한다.
- 첫 번째 request를 gateway에 release한 뒤, runtime probe로 backend 중 하나가 processing >= 1이 된 것을 확인한다.
- 이후 두 번째 request를 동일 gateway에 release한다.
- 두 backend가 각각 processing >= 1이 되는 것을 확인해야 measured C2 admission 성공이다.
- response header의 distinct `x-litellm-model-id` / `x-litellm-model-api-base`와 backend runtime probe를 routing evidence로 보존한다.
- overlapping decode lifetime을 PASS_C2_ACTIVE 조건으로 유지한다.

> **Caveat**: 최초 simultaneous admission diagnostic에서는 pinned LiteLLM 1.101.0의 least-busy 초기 tie timing으로 인해 두 request가 동일 deployment에 binding될 수 있음을 관찰했다. 따라서 authoritative WBS4 measurement에서는 routing-settled admission을 채택했다. 이 diagnostic을 별도의 measured benchmark 결과로 사용하지 않는다.

WBS4 수치는 topology/capacity evidence이며, 정식 performance ranking은 WBS5 performance workload에서 다시 측정한다.

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

> **Routing Preflight**: 각 C2 측정 직전에 `routing_preflight ping` (max_tokens=16, 2개 request)가 실행된다. 이것은 full-size benchmark warmup이 아니라 두 backend의 LiteLLM routing 가용성을 확인하는 짧은 inference이다. raw config의 "no warmup" 표현은 full-size benchmark warmup이 없었음을 의미하며, routing-preflight 자체는 실행되었다.

### 4.1 llama.cpp

- artifact: `Q6_K` (`/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf`).
- KV: `FP16`.
- Server 0: GPU0 (`127.0.0.1:18080`), Server 1: GPU1 (`127.0.0.1:18081`), Gateway: LiteLLM v1.101.0 (`127.0.0.1:18079`).
- 실행 runner: `scripts/run_1gpu_litellm.py`.

#### 4.1.1 TARGET [DONE]
- C1 attempt 001: `EXP-V100-ORN15-9B-LLAMA-F16-TARGET-1GPU2-C1-128K-20260926-001` — `INCONCLUSIVE` (harness CLI args bug on worker invocation; preflight/servers PASS, measured request not reached).
- C1 attempt 002: `EXP-V100-ORN15-9B-LLAMA-F16-TARGET-1GPU2-C1-128K-20260926-002` — **`PASS_C1_128K`**
  - TTFT: 190,008.28 ms (~190.01s), Prefill ~679.0 tok/s, Decode 43.34 tok/s, Aggregate Decode 43.34 tok/s, End-to-end 2.58 tok/s, Batch Wall 202.08s.
  - Prompt: 129,023 tokens, Output: 522 tokens (`finish_reason=stop`, mechanical & semantic PASS).
  - Peak VRAM: GPU0 10,891 MiB / GPU1 10,769 MiB (각 16GB 한도 내 안정적 수용).
  - Gateway routing: LiteLLM least-busy router를 통해 backend-0 (`http://127.0.0.1:18080/v1`)으로 정상 프록시 및 디코드 완료.
  - Post-health: LiteLLM `/health/liveliness` 및 Backend 0, 1 `/health` 모두 200 OK 정상 종료.
- C2: `EXP-V100-ORN15-9B-LLAMA-F16-TARGET-1GPU2-C2-128K-20260926-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false`.
  - Gateway routing: LiteLLM single gateway (`http://127.0.0.1:18079`) 경로로 단일 진입. Dual-backend preflight 통과 후 `RoutingSettledAdmissionBarrier`를 통해 backend-0 (`:18080`) 및 backend-1 (`:18081`)로 분산 안착 확인.
  - TTFT (Batch Mean): 186,447.92 ms (~186.45s; Req A 189.38s, Req B 183.51s).
  - Decode: Mean Request 43.51 tok/s, Aggregate Decode **77.40 tok/s**, End-to-End 12.69 tok/s, Batch Wall 220.01s.
  - Peak VRAM: GPU0 10,893 MiB / GPU1 10,893 MiB (완전 대칭 적재, 16GB 한도 내 각 ~5.5 GiB 여유).
  - Common decode window: `9659.31s ~ 9687.29s` (~28s) 구간 동시 병렬 디코드 완벽 증명.
  - Output analysis: Project A (1,201 tokens), Project B (1,591 tokens) 모두 seeded defect 분석/수정안 제시 완벽 통과 (PASS).

#### 4.1.2 NGRAM [DONE]
- C1: `EXP-V100-ORN15-9B-LLAMA-F16-NGRAM-1GPU2-C1-128K-20260926-001` — `SKIPPED` (사용자 승인: 4.1.1 TARGET C1에서 단일 요청 LiteLLM 경로 검증 완료 후 C2로 직행)
- C2: `EXP-V100-ORN15-9B-LLAMA-F16-NGRAM-1GPU2-C2-128K-20260926-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false`.
  - Gateway routing: LiteLLM single gateway (`http://127.0.0.1:18079`) 경로로 단일 진입. Dual-backend preflight 통과 후 `RoutingSettledAdmissionBarrier`를 통해 backend-0 (`:18080`) 및 backend-1 (`:18081`)로 분산 안착 확인.
  - TTFT (Batch Mean): 186,976.07 ms (~186.98s; Req A 190.18s, Req B 183.77s).
  - Prefill: **690.25 tok/s**.
  - Decode: Mean Request 44.31 tok/s, Aggregate Decode **77.66 tok/s**, End-to-End 12.92 tok/s, Batch Wall 220.96s.
  - NGRAM Speculative 통계: Backend 0 (Req A) 30.21% (116/384 accepted), Backend 1 (Req B) 21.91% (161/735 accepted), 전체 통합 **24.75%** (277/1,119 accepted).
  - Peak VRAM: GPU0 10,895 MiB / GPU1 10,895 MiB (16GB 한도 내 대칭 적재).
  - Common decode window: `10122.09s ~ 10149.70s` (~27.6s) 구간 동시 병렬 디코드 완벽 증명.
  - Output analysis: Project A (1,215 tokens), Project B (1,568 tokens) 모두 seeded defect 분석/수정안 제시 완벽 통과 (PASS).

#### 4.1.3 MTP [DONE]
- C1: `EXP-V100-ORN15-9B-LLAMA-F16-MTP-1GPU2-C1-128K-20260926-001` — `SKIPPED` (사용자 승인: 4.1.1 TARGET C1에서 단일 요청 LiteLLM 경로 검증 완료 후 C2로 직행)
- C2: `EXP-V100-ORN15-9B-LLAMA-F16-MTP-1GPU2-C2-128K-20260926-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false`.
  - Gateway routing: LiteLLM single gateway (`http://127.0.0.1:18079`) 경로로 단일 진입. Dual-backend preflight 통과 후 `RoutingSettledAdmissionBarrier`를 통해 backend-0 (`:18080`) 및 backend-1 (`:18081`)로 분산 안착 확인.
  - TTFT (Batch Mean): 208,551.16 ms (~208.55s; Req A 212.17s, Req B 204.93s).
  - Prefill: **618.85 tok/s** (Req A: 608.11, Req B: 629.59).
  - Decode: Mean Request **51.01 tok/s** (TARGET 대비 +17.2% 향상), Aggregate Decode **75.34 tok/s**, End-to-End 9.72 tok/s, Batch Wall 235.74s.
  - MTP Speculative 통계: Backend 0 (Req A) 54.75% (744/1,359 accepted, mean len = 2.64), Backend 1 (Req B) 51.71% (664/1,284 accepted, mean len = 2.55), 전체 통합 **53.27%** (1,408/2,643 accepted).
  - Peak VRAM: GPU0 11,903 MiB / GPU1 11,903 MiB (Drafter 적재 반영, 16GB 한도 내 대칭 적재, ~4.5 GiB 여유).
  - Common decode window: `10592.77s ~ 10607.28s` (~14.5s) 구간 동시 병렬 디코드 완벽 증명.
  - Output analysis: Project A (1,198 tokens), Project B (1,093 tokens) 모두 seeded defect 분석/수정안 제시 완벽 통과 (PASS).

#### 4.1.4 MTP_NGRAM [DONE]
- C1: `EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-1GPU2-C1-128K-20260926-001` — `SKIPPED` (사용자 승인: 4.1.1 TARGET C1에서 단일 요청 LiteLLM 경로 검증 완료 후 C2로 직행)
- C2: `EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-1GPU2-C2-128K-20260926-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false`.
  - Gateway routing: LiteLLM single gateway (`http://127.0.0.1:18079`) 경로로 단일 진입. Dual-backend preflight 통과 후 `RoutingSettledAdmissionBarrier`를 통해 backend-0 (`:18080`) 및 backend-1 (`:18081`)로 분산 안착 확인.
  - TTFT (Batch Mean): 208,742.99 ms (~208.74s; Req A 212.12s, Req B 205.36s).
  - Prefill: **618.26 tok/s** (Req A: 608.25, Req B: 628.27).
  - Decode: Mean Request 49.96 tok/s, Aggregate Decode **79.35 tok/s** (C2 최고 throughput 달성), End-to-End 9.84 tok/s, Batch Wall 234.89s.
  - Speculative 통계: Backend 0 (Req A) 50.92% (750/1,473 accepted, mean len = 2.80), Backend 1 (Req B) 40.43% (689/1,704 accepted, mean len = 2.56), 전체 통합 **45.30%** (1,439/3,177 accepted).
  - Peak VRAM: GPU0 11,905 MiB / GPU1 11,905 MiB (16GB 한도 내 대칭 적재).
  - Common decode window: `11062.15s ~ 11079.31s` (~17.2s) 구간 동시 병렬 디코드 완벽 증명.
  - Output analysis: Project A (1,171 tokens), Project B (1,140 tokens) 모두 seeded defect 분석/수정안 제시 완벽 통과 (PASS).

### 4.2 1Cat-vLLM STOCK

- artifact: `ornith-ai/Ornith-1.5-9B-NVFP4`.
- KV: `FP16`.
- speculative: MTP1.
- Server 0: GPU0 TP1 (`127.0.0.1:18080`), Server 1: GPU1 TP1 (`127.0.0.1:18081`), Gateway: LiteLLM v1.101.0 (`127.0.0.1:18079`).
- 실행 runner: `scripts/run_1gpu_litellm.py`.

#### 4.2.1 STOCK MTP1 [CLOSED — FAIL_STARTUP / 1GPU 128K CAPACITY LIMIT]
- C1: `EXP-V100-ORN15-9B-1CAT-F16-MTP1-1GPU2-C1-128K-20260926-001` — `SKIPPED` (사용자 승인: 4.1.1 TARGET C1에서 단일 요청 LiteLLM 경로 검증 완료 후 C2로 직행)
- C2: `EXP-V100-ORN15-9B-1CAT-F16-MTP1-1GPU2-C2-128K-20260926-001` — **`FAIL_STARTUP`**
  - 실패 원인: 1Cat-vLLM 1.5.0에서 단일 V100 16GB TP1으로 Ornith 1.5 9B MTP1 서빙 시, 128K(131,072) 컨텍스트 1개를 수용하기 위한 최소 KV 캐시 메모리(4.68 GiB)가 가용 KV 캐시 메모리(2.61 GiB)를 초과하여 기동 실패 (`ValueError: To serve at least one request with the model's max seq len (131072), (4.68 GiB KV cache is needed, which is larger than the available KV cache memory (2.61 GiB). Based on the available memory, the estimated maximum model length is 71280.`).
  - 이 exact pinned profile에서의 capacity 부족이 확인됨:
    - Runtime: 1Cat-vLLM 1.5.0
    - Model: Ornith 1.5 9B NVFP4
    - Speculative: STOCK MTP1
    - KV: FP16
    - Tensor Parallelism: TP1
    - GPU: V100 16GB 1장
    - max_model_len: 131,072
    - Required KV: 4.68 GiB, Available KV: 2.61 GiB, Estimated max model length: ~71,280
  - 다른 KV quantization (e.g. FP8), 다른 speculative configuration, 다른 runtime에서의 결과까지 물리적으로 불가능하다고 일반화하지 않는다.
  - 프로젝트 불변 규칙에 따라 설정을 임의 변경하는 자동 재시도는 수행하지 않고 closed 처리함.

## 5. 성능 최적화 및 모델별 최종 레시피 확정 [IN_PROGRESS — FROZEN / PARTIAL_MEASURED_RESULTS_PUBLISHED]

WBS 2/3/4에서 확보한 capacity/correctness/topology evidence와 WBS 5의 performance evidence를 분리한다.
WBS 5는 아래 7개 model/runtime track에 대해 이미 연구·선정이 끝난 frozen candidate만 실행하며,
새 candidate 자동 생성, exhaustive grid, 임의 tuning을 수행하지 않는다.

현재 단계는 **PARTIAL_MEASURED_RESULTS_PUBLISHED — 유효한 WBS5 measured raw 14건(Qwen llama.cpp 4건 + Ornith 1.5 9B llama.cpp 3건 + Ornith 1.5 35B llama.cpp 4건 + Gemma4 llama.cpp 3건)의 공식 report/CSV 반영 완료**이다. 8A 및 8B~8D runner/harness 구현·dry-plan·static/unit validation + ChatGPT pre-run final validation은 완료된 준비 이력이다.
25개 frozen candidate의 28개 dry-plan을 저장했다. Qwen 1Cat R2는 host toolchain BLOCKED, Ornith9 1Cat G0는 pending이며 Gemma R3 Gate B는 `NOT_TRIGGERED`로 판정해 R3를 SKIP했다. 준비 당시 harness validation은 통과했으며, 회수 raw의 sampler 오류와 evidence 한계는 5.3.1에 기록했다. [준비 결과](WBS-5-preparation-readiness.md).
2026-09-28~29 canonical `results/raw/`와 WBS experiment ID 대조 결과, 공식 publication 완료 raw는 Qwen llama.cpp `5.3.1.1`~`5.3.1.4` 4건, Ornith 1.5 9B llama.cpp `5.3.2.1`~`5.3.2.3` 3건, Ornith 1.5 35B llama.cpp `5.3.3.1`~`5.3.3.4` 4건, Gemma4 llama.cpp `5.3.4.1`~`5.3.4.3` 3건, 총 14건이다. 14건 모두 저장된 최종 verdict `PASS_C2_ACTIVE`로 publication했다. Ornith 9B R0의 최초 시도는 구 HEAD의 slot evidence parser 예외로 중단된 harness-invalid attempt였고 공식 performance evidence로 사용하지 않았다. Ornith 9B R2는 `ngram-simple` configuration이지만 이 workload에서 NGRAM draft activity가 관측되지 않았다. Ornith 35B R1의 최초 `-001` raw는 측정 전 포트 충돌로 `INCONCLUSIVE`; 보존하되 공식 performance report/CSV에서 제외하고, 사용자 지정 동일 설정 재실행 `-002`만 publication했다. Qwen llama.cpp `5.3.1.7`, Ornith 1.5 9B llama.cpp `5.3.2.4`, Ornith 1.5 35B llama.cpp `5.3.3.5`, Gemma4 llama.cpp `5.3.4.6` track review는 모두 완료됐다. Qwen R2와 Ornith9 R1은 final recipe 후보로 유지되고, Ornith35 R1/R2는 workload-oriented `VALIDATED_RECIPE`, Gemma4 R0는 WBS 5.5 승격 대상으로 유지한다. WBS 5.5 final recipe publication은 아직 미완료다.

### 5.1 authoritative planning input 및 진행 단계

WBS 5의 candidate 정의는 다음 7개 문서를 authoritative planning input으로 사용한다.

- `docs/WBS-5 - Qwen 3.8 27B - llama.cpp.md`
- `docs/WBS-5 - Ornith 1.5 9B - llama.cpp.md`
- `docs/WBS-5 - Ornith 1.5 35B-A3B - llama.cpp.md`
- `docs/WBS-5 - Gemma4 26B A4B - llama.cpp.md`
- `docs/WBS-5 - Qwen 3.8 27B - 1Cat-vLLM.md`
- `docs/WBS-5 - Ornith 1.5 9B - 1Cat-vLLM.md`
- `docs/WBS-5 - Ornith 1.5 35B-A3B - 1Cat-vLLM.md`

이 문서들은 measured result가 아니라 **실행 전 frozen candidate plan**이다.
candidate ID, 숫자, one-variable delta, invariant, conditional gate를 임의 변경하지 않는다.

WBS 5 단계 흐름:

1. 7개 candidate plan 연구/선정 완료.
2. 7개 frozen plan 문서화 완료.
3. `docs/WBS.md` 공식 반영 완료.
4. Codex CLI local validation / test preparation 완료 (8A~8D; measured inference 없음).
5. ChatGPT pre-run final validation 완료.
6. **현재 단계: 유효한 measured child 14건의 raw/report publication 완료. llama.cpp 네 track review(Qwen `5.3.1.7`, Ornith 9B `5.3.2.4`, Ornith 35B `5.3.3.5`, Gemma4 `5.3.4.6`)는 모두 DONE이다. Qwen R2와 Ornith9 R1은 final recipe 후보, Ornith35 R1/R2는 workload-oriented `VALIDATED_RECIPE`, Gemma4 R0는 WBS 5.5 승격 대상으로 유지한다. 다음 measured child를 자동 실행하지 않는다.**
7. 각 track measured 결과 분석 및 track review WBS 수행.
8. 필요 시 Claude independent review.
9. 모델별 final recipe 확정.
10. WBS 5 final publication / DONE.

5번까지는 준비/검증 lifecycle이고, 6번부터의 실제 작업 단위는 아래 `5.3.x.y` / `5.4.x.y` 번호를 authoritative execution WBS로 사용한다. 따라서 Codex CLI에는 다시 기존 프로젝트 방식대로 **“WBS 5.3.1.1 진행해.”**처럼 한 번호씩 지시한다.

### 5.2 공통 실행 계약

정식 WBS 5 performance workload는 `workloads/performance/v1.json`이다.

고정 workload contract:
- workload ID: `V100-PERFORMANCE-C2-128K-v1`.
- context target: **131072/request**.
- output reserve: 4096/request.
- minimum actual output: 1024/request.
- independent Project A/B 2 requests.
- deterministic sampling contract 유지.
- WBS 2의 C1 capacity, WBS 3의 shared-TP2 C2 topology, WBS 4의 1GPU×2 topology evidence는 WBS 5 performance result로 대체하거나 혼동하지 않는다.

실행 규칙:
- 아래 frozen candidate 외 자동 탐색 금지.
- exhaustive grid 금지.
- measured run 전에 **Codex CLI local validation이 필수**다.
- local binary/source/`--help` 검증 전에는 option 존재, default, route hit 가능 여부를 확정 사실로 쓰지 않는다.
- local validation에서 candidate exact command/config diff가 frozen plan과 다르면 measured run으로 진행하지 않는다.
- existing raw artifact를 overwrite하지 않는다.
- candidate/run마다 fresh experiment ID를 사용한다.
- 자동 retry 금지.
- 실패 결과도 evidence로 보존한다.
- 한 candidate의 실패를 이유로 다른 option을 임의 추가/변경하지 않는다.
- GPU measured run은 여러 track을 동시에 실행하지 않고 직렬 수행한다.
- `infra-invalid`, `workload-invalid`, artifact/runtime identity mismatch, frozen-delta mismatch는 해당 measured run 전/중 **hard stop**이다.
- 단순 성능 열세는 infra-invalid가 아니며 candidate failure/performance evidence로 보존할 수 있다.
- option이 static source에 존재하는 것과 future measured run에서 실제 route/capture/replay가 hit되는 것은 구분한다.
- `READY_FOR_PRE_RUN_VALIDATION` 또는 static READY는 measured PASS나 `VALIDATED_RECIPE`를 의미하지 않는다.

공통 evidence:
- TTFT.
- prefill tok/s.
- per-request decode tok/s 및 mean request decode tok/s.
- aggregate decode tok/s.
- end-to-end output tok/s.
- batch wall.
- actual output tokens.
- GPU0/GPU1 peak VRAM.
- power / temperature / clocks.
- output integrity.
- active overlap / queue status.
- post-health.
- speculative candidate의 draft / accepted / acceptance ratio.
- graph candidate에서 가능한 경우 graph eligibility와 실제 reuse/hit evidence를 분리 기록.


#### 5.2.1 WBS 번호 dispatch 규칙 — Luna/Codex CLI

WBS 5 measured child는 **한 번호 = 한 benchmark run**이다.

- 실행 가능한 measured 번호는 아래 실제 child 항목으로 정의된 `5.3.x.y`, `5.4.x.y`다.
- `5.3.1`, `5.3.2`, `5.4.1` 같은 3단계 번호는 **NON-EXECUTABLE PARENT SECTION**이다. parent만 지시받으면 child를 추론해 실행하지 않는다.
- 사용자가 `WBS 5.3.1.1 진행해.`라고 하면 **5.3.1.1의 benchmark 한 건만 실행하고 raw 결과를 ThinkPad로 회수한 뒤 종료**한다.
- 다음 WBS를 자동 실행하지 않는다.
- measured child 실행 중 report 생성, `docs/WBS.md` 수정, `state/current.md` 수정, summary/comparison CSV 수정, commit/push를 하지 않는다. 이런 분석/정리 작업은 별도 review WBS 또는 별도 사용자 지시에서 수행한다.
- automatic retry, automatic confirm, fallback, tuning, candidate 변경을 하지 않는다.

#### 5.2.2 WBS5 measured execution entry point [AUTHORITATIVE]

ThinkPad Codex/Luna는 remote orchestration을 직접 재구성하지 않는다. 모든 measured child는 **`scripts/run_wbs5_remote.py` 한 명령만 실행**한다.

이 wrapper가 내부에서 정확히 다음만 수행한다.

1. 현재 committed `HEAD`의 tracked source를 `git archive`로 P520의 commit-isolated snapshot에 전송.
2. P520에서 해당 benchmark runner를 **정확히 한 번** 실행.
3. 해당 `results/raw/<EXP_ID>/` 디렉터리만 ThinkPad의 `results/raw/<EXP_ID>/`로 회수.
4. raw의 verdict/error를 stdout에 요약하고 종료.

고정 contract:

- control host / Git checkout: ThinkPad `~/Data/Workspace_VSCode/v100-llm-test`
- measurement host SSH alias: `p520`; expected hostname: `p520-llm`
- remote snapshot: `/home/loopwhile/v100-llm-test-wbs5/<HEAD12>`
- source sync는 `git archive HEAD`를 사용한다. **`rsync --delete`를 사용하지 않는다.**
- wrapper는 tracked working-tree/index 변경이 있으면 benchmark를 시작하지 않는다. untracked 이전 raw 결과는 허용한다.
- 같은 HEAD snapshot에 같은 experiment ID의 remote raw가 이미 있으면 benchmark를 중복 실행하지 않고 그 raw만 회수한다.
- ThinkPad에 같은 experiment ID의 local raw가 이미 있으면 overwrite하지 않고 중단한다.
- benchmark process가 non-zero여도 raw가 생성되었다면 raw를 회수하고 wrapper 자체는 orchestration 성공으로 종료한다. benchmark PASS/FAIL은 `completion.json`의 verdict로 판단한다.
- 예전 `/home/loopwhile/v100-llm-test-wbs5-20260928-a` snapshot과 그 안의 pre-measurement residue는 **legacy/abandoned**다. 이 commit 이후 WBS5 measured execution에는 사용하지 않는다.
- generic benchmark-orchestrator의 subagent 방식은 WBS5 measured child에 사용하지 않는다.

따라서 measured child의 완료 조건은 단순하다.

```text
P520에서 지정 benchmark 1회 실행
        ↓
ThinkPad results/raw/<EXP_ID>/ 회수
        ↓
STOP
```

report/publication/WBS/state/Git closeout은 measured child의 책임이 아니다.

#### 5.2.3 현재 measured execution 수량

- frozen candidate: **25개**.
- dry-plan/run identity: **28개**. Qwen llama R0 repetition 1회와 R1/R2 optional confirm 2개가 추가되어 candidate 수보다 3개 많다.
- 현재 gate/toolchain을 건드리지 않고 진행 가능한 기본 measured invocation: **20회**.
- conditional: Gemma llama R3 1회, Ornith9 1Cat R0 ~ R3 4회.
- toolchain blocked: Qwen 1Cat R2 1회.
- optional confirm: Qwen llama R1/R2 각 1회.
- Ornith9 1Cat의 G0 semantic requalification은 WBS5 performance candidate와 별도 prerequisite measured experiment 1회다.

기본 20회도 한 프롬프트로 연속 실행하지 않는다. 아래 번호 하나씩 사용자 지시를 받아 실행한다.

### 5.3 llama.cpp frozen tracks

#### 5.3.1 Qwen3.8-27B / llama.cpp [NON-EXECUTABLE PARENT — FROZEN / R0-R2 MEASURED_PUBLISHED / REVIEW_DONE]

Frozen candidates:

| Candidate | Frozen configuration / R0 대비 exact delta |
|---|---|
| `Q38-LLAMA-WBS5-R0-TARGET-B512-UB128` | TARGET, `--spec-type none`, `--batch-size 512`, `--ubatch-size 128`. |
| `Q38-LLAMA-WBS5-R1-NGRAM-DEFAULT` | R0에서 **`--spec-type none -> ngram-simple`만 변경**. NGRAM pinned defaults `size_n=12`, `size_m=48`, `min_hits=1`; explicit override 금지. |
| `Q38-LLAMA-WBS5-R2-TARGET-UB256` | R0에서 **`--ubatch-size 128 -> 256`만 변경**. `--batch-size 512` 유지. |

보존 invariant:
- `unsloth/Qwen3.8-27B-GGUF@4ca720788d1e01f1bff70c033e0d0028fd02e502`.
- `Qwen3.8-27B-UD-Q4_K_M.gguf`, SHA256 `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`.
- weight `UD-Q4_K_M`, KV K/V `q8_0`.
- llama.cpp b10775 / `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb` / pinned OCI digest.
- shared TP2, layer split `1,1`, `ctx-size=262144`, `parallel=2`, unified KV, per-slot 131072, FA on, Jinja, reasoning off, metrics/slots/no-warmup.
- `GGML_CUDA_P2P` 및 `GGML_CUDA_DISABLE_GRAPHS`를 임의 설정하지 않는다.

LOCAL_VERIFY_REQUIRED:
- R0/R1/R2 exact command generation과 one-variable diff.
- pinned binary의 `spec-type`, `ngram-simple`, batch/ubatch, unified-KV, FA 지원.
- NGRAM default 12/48/1.
- graph-capable 여부와 graph reuse evidence 보존 가능 여부.
- WBS5 workload/telemetry 저장 경로와 fresh experiment ID/overwrite 방지.

실행 순서/stop:
- local validation은 R0 -> R1 -> R2 순서.
- measured phase에서 R0는 frozen plan대로 서로 다른 fresh experiment ID로 2회 계획된 repetition을 가질 수 있다. 이는 failure retry가 아니라 사전 등록된 repetition이다.
- R1/R2는 screening 1회가 기본이며 confirm run은 자동 실행하지 않는다. 필요성이 확인된 경우 동일 configuration/fresh ID로만 수행한다.
- exact command가 frozen delta 외의 변수를 바꾸거나 artifact/runtime/workload가 불일치하면 hard stop.
- 최종 recipe 승격에는 frozen configuration identity, valid `performance/v1.json` measured evidence, output integrity, telemetry/provenance가 모두 필요하다.


2026-09-28 publication evidence 주의사항:

- 아래 4건의 `completion.json`, `metrics.json`, `runtime/exit.json`은 모두 `PASS_C2_ACTIVE`이며, 이미 저장된 `overlap_reconciled_from: log-overlap-evidence.json`을 근거로 한다. 이번 publication에서 verdict를 재판정하거나 raw를 수정하지 않았다.
- 4건 모두 `runtime/measurement.log`에 slot sampler의 `AttributeError: 'list' object has no attribute 'get'`가 있다. live sampler는 2 samples / peak processing 0만 기록했으므로, active overlap 근거는 `runtime/server-0.log`의 decode interleaving과 `log-overlap-evidence.json`이다.
- R0 repetition-1의 `wbs5-evidence.json`에는 보정 전 `c2_active: null` / `UNKNOWN`이 남아 있다. 공식 reporter는 보정된 `completion.json`/`metrics.json`을 사용하며 이 snapshot 차이는 그대로 보존한다.
- Requests의 PASS와 `mechanical_output_verdict: PASS`는 raw에 기록된 판정이다. 별도 `acceptance-review.json`은 없으며, 새 semantic audit나 winner 선정은 수행하지 않았다.
- 5.3.1.5/5.3.1.6 optional confirm은 2026-09-28 사용자 결정으로 **SKIP**한다. 미실행 / raw 없음이며 measured DONE이나 PASS로 취급하지 않는다. 5.3.1.7 track review는 2026-09-29 완료했으며, 추가 confirm이나 새 candidate 없이 R2를 **final recipe candidate**로 유지한다.

##### 5.3.1.1 Qwen3.8 llama.cpp — R0 repetition-1 measured [DONE — PASS_C2_ACTIVE]

- 상태: **DONE — PASS_C2_ACTIVE** (measured child 실행/회수 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001`; 완료 UTC: `2026-09-28T08:49:27.088086+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001/) / [Report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001.md); `results/summary.csv`, `reports/comparison.csv` 반영 완료.
- Requests: project-a 2184 tokens / `PASS`, project-b 1711 tokens / `PASS`; post-health healthy.

목적: frozen baseline `Q38-LLAMA-WBS5-R0-TARGET-B512-UB128`의 첫 번째 사전 등록 repetition을 수행한다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-llama --candidate R0 --experiment-id EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001 --run-label repetition-1 --execute-measured
```

완료 조건: wrapper가 해당 experiment raw를 ThinkPad `results/raw/`로 회수하면 종료한다. 실패 verdict여도 자동 재시도하지 않는다.

##### 5.3.1.2 Qwen3.8 llama.cpp — R0 repetition-2 measured [DONE — PASS_C2_ACTIVE]

- 상태: **DONE — PASS_C2_ACTIVE** (measured child 실행/회수 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002`; 완료 UTC: `2026-09-28T09:40:21.082469+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002/) / [Report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002.md); `results/summary.csv`, `reports/comparison.csv` 반영 완료.
- Requests: project-a 2310 tokens / `PASS`, project-b 2008 tokens / `PASS`; post-health healthy.

목적: R0와 **동일 configuration**으로 두 번째 사전 등록 repetition을 fresh ID에서 수행한다. 5.3.1.1 실패 retry가 아니라 원래 계획된 독립 repetition이다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-llama --candidate R0 --experiment-id EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002 --run-label repetition-2 --execute-measured
```

##### 5.3.1.3 Qwen3.8 llama.cpp — R1 NGRAM screening [DONE — PASS_C2_ACTIVE]

- 상태: **DONE — PASS_C2_ACTIVE** (measured child 실행/회수 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001`; 완료 UTC: `2026-09-28T10:14:45.183800+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001/) / [Report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001.md); `results/summary.csv`, `reports/comparison.csv` 반영 완료.
- Requests: project-a 2214 tokens / `PASS`, project-b 2069 tokens / `PASS`; post-health healthy.

R0 대비 `--spec-type none -> ngram-simple`만 바뀌는지 runner guard를 통과한 뒤 1회 수행한다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-llama --candidate R1 --experiment-id EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.1.4 Qwen3.8 llama.cpp — R2 UB256 screening [DONE — PASS_C2_ACTIVE]

- 상태: **DONE — PASS_C2_ACTIVE** (measured child 실행/회수 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001`; 완료 UTC: `2026-09-28T10:43:47.163436+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/) / [Report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001.md); `results/summary.csv`, `reports/comparison.csv` 반영 완료.
- Requests: project-a 2653 tokens / `PASS`, project-b 1970 tokens / `PASS`; post-health healthy.

R0 대비 `--ubatch-size 128 -> 256`만 바뀌는지 확인하고 1회 수행한다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-llama --candidate R2 --experiment-id EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.1.5 Qwen3.8 llama.cpp — R1 optional confirm [SKIP — USER_DECISION]

상태: **SKIP — USER_DECISION** (2026-09-28). 사용자 지시로 R1 optional confirm을 실행하지 않는다. Raw/report 없음; 아래 명령은 frozen plan 이력으로만 보존한다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-llama --candidate R1 --experiment-id EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-002 --run-label confirm-1 --execute-measured
```

##### 5.3.1.6 Qwen3.8 llama.cpp — R2 optional confirm [SKIP — USER_DECISION]

상태: **SKIP — USER_DECISION** (2026-09-28). 사용자 지시로 R2 optional confirm을 실행하지 않는다. Raw/report 없음; 아래 명령은 frozen plan 이력으로만 보존한다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-llama --candidate R2 --experiment-id EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-002 --run-label confirm-1 --execute-measured
```

##### 5.3.1.7 Qwen3.8 llama.cpp — track result review [DONE — R2 FINAL RECIPE CANDIDATE]

상태: **DONE — TRACK REVIEW** (2026-09-29). 이번 review에서는 GPU inference를 추가 실행하지 않았고, 이미 publication된 R0 repetition 2건과 R1/R2 screening 각 1건의 raw artifact만 사용했다. R1/R2 optional confirm은 5.3.1.5/5.3.1.6의 사용자 결정대로 **SKIP** 상태를 유지하며, frozen candidate 밖의 새 tuning candidate를 추가하지 않는다.

검토 대상:
- R0 repetition-1: `EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001`
- R0 repetition-2: `EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002`
- R1 NGRAM screening: `EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001`
- R2 UB256 screening: `EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001`

| Metric | R0 rep-1 | R0 rep-2 | R1 NGRAM | R2 UB256 |
|---|---:|---:|---:|---:|
| Verdict | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` |
| TTFT | 901.97 s | 904.12 s | 904.45 s | **679.05 s** |
| Prefill | 206.12 tok/s | 178.23 tok/s | 178.17 tok/s | **264.11 tok/s** |
| Mean request decode | 5.269 tok/s | 5.385 tok/s | 5.559 tok/s | 5.593 tok/s |
| Aggregate decode | 3.693 tok/s | 3.958 tok/s | 3.998 tok/s | 4.514 tok/s |
| End-to-end output | 2.527 tok/s | 2.732 tok/s | 2.744 tok/s | 3.457 tok/s |
| Batch wall | 1541.28 s | 1580.35 s | 1560.73 s | **1337.27 s** |
| Total output | 3895 | 4318 | 4283 | 4623 |
| Peak VRAM GPU0 | 13159 MiB | 13159 MiB | 13161 MiB | 13447 MiB |
| Peak VRAM GPU1 | 14247 MiB | 14245 MiB | 14249 MiB | 14533 MiB |
| Graph reuse evidence | 5096 | 5521 | 5081 | 4339 |
| Speculative acceptance | N/A | N/A | **323 / 985 = 32.79%** | N/A |

Capacity / stability:
- 네 run 모두 `PASS_C2_ACTIVE`, `c2_resident=true`, `c2_active=true`, `queue_only=false`, post-health healthy다.
- R2는 `--ubatch-size 128 -> 256` 이후에도 OOM, allocator/runtime crash, queue-only 퇴행 없이 완료됐다.
- R2 peak VRAM은 R0 대비 GPU당 약 **+286~288 MiB** 증가했다. V100 16 GiB에서 GPU1 sampled peak는 14533 MiB였으며, 0.5 s sampler가 transient peak를 놓칠 수 있다는 기존 limitation은 유지한다.

Output integrity:
- 네 run 모두 두 request가 `minimum_output_tokens=1024`를 넘기고 `finish_reason=stop`, request verdict `PASS`, `mechanical_output_verdict=PASS`를 기록했다.
- 이 WBS5 performance lane에는 별도 task-level semantic oracle/acceptance review가 없으므로, 이번 review는 mechanical output integrity와 non-truncated completion까지만 확정한다. WBS3 semantic evidence를 WBS5의 새 semantic 판정으로 재사용하지 않는다.

TTFT / prefill:
- R2 평균 TTFT 679.05 s는 R0 901.97/904.12 s 대비 약 **24.7~24.9% 감소**했다. R0 두 repetition의 TTFT 자체는 약 0.24% 범위로 좁아, R2 TTFT 변화는 3% 수준의 미세 차이로 보지 않는다.
- R2 request-level llama.cpp prompt timing도 감소했다. 비교가 깨끗한 R0 rep-2 대비 project-a `prompt_ms 1318781.5 -> 1044847.8` (약 -20.8%), project-b `488036.3 -> 312211.5` (약 -36.0%)다.
- `prefill_tps`는 request별 server `prompt_per_second`의 산술평균이다. 따라서 `prompt_tokens / mean(prefill_tps)`를 평균 TTFT와 직접 비교해 별도 고정 overhead를 역산하지 않는다.
- R0 rep-1 project-b에는 server `prompt_ms≈839.95 s` 대비 client TTFT `≈1317.42 s`의 추가 지연이 관찰되므로, R0 rep-1의 평균 prefill 값만으로 noise floor를 단정하지 않는다.
- Intended effect 관점에서는 R2가 두 request의 실제 server prompt processing을 모두 단축했으므로, `ubatch=256`의 long-context prefill/TTFT 개선 신호는 직접 관찰됐다.

Decode / aggregate / end-to-end:
- R2 mean request decode 5.593 tok/s는 R0 5.269/5.385 tok/s 대비 약 +3.9~6.1%다. 이를 큰 decode optimization으로 해석하지 않고 **decode 유지 + 약한 개선 신호**로 취급한다.
- `scripts/bench_harness.py`의 `aggregate_decode_tps`는 pure decode-only window가 아니다. 구현은 `total output tokens / (max(end_abs) - min(first_abs))`이므로, 첫 request first-token 이후 다른 request의 prefill/scheduling overlap도 포함한다. 따라서 R2의 aggregate 4.514 tok/s를 GPU decode kernel 자체의 +18% 개선으로 해석하지 않는다.
- `end_to_end_output_tps = total_output_tokens / batch_wall_s`이며 R2 output length가 R0보다 길다. 관측값 3.457 tok/s의 상승은 유효한 run-level efficiency signal이지만, 전체 상승률을 `ubatch=256`의 순수 causal speedup으로 사용하지 않는다.
- 반면 R2는 R0보다 더 많은 output tokens(4623)를 생성하면서도 batch wall이 1337.27 s로 R0 1541.28/1580.35 s보다 약 **13.2~15.4% 짧았다**. TTFT/prompt-processing 개선이 batch completion time 개선으로 이어졌다는 근거로 사용한다.

Power / temperature / clocks / graph:
- raw telemetry에서 R2 power/temperature/clocks가 R0와 다른 성능 상태로 급변했다는 evidence는 없다. R2 sampled max temperature는 GPU0 72 C / GPU1 63 C, max SM clock은 양쪽 1200 MHz였고, post-health는 healthy다.
- CUDA Graph reuse는 네 run 모두 `OBSERVED`다. 다만 `graph-evidence.json`의 reuse count는 server lifetime 범위이며 startup/routing preflight를 포함할 수 있어 measured-window hit rate나 후보 간 성능 비율로 비교하지 않는다. R2에서 graph path가 깨졌다는 evidence는 없다.

Speculative / R1 판정:
- R1은 draft 985, accepted 323, draft_count 21, acceptance ratio **32.79%**로 ngram-simple activity가 실제 발생했다.
- accepted/output coverage는 323 / 4283 ≈ **7.54%**다. 그러나 verify cost, host-side history scan, accepted span을 포함한 speculative 비용은 비선형이므로 이 coverage에서 theoretical speedup upper bound를 계산하지 않는다.
- R1은 R0 rep-2 대비 TTFT +0.04%, prefill -0.03%, mean request decode +3.23%, aggregate +1.02%, E2E +0.44%, batch wall -1.24%로 대부분 3% 전후 또는 그 이하다. R0 반복 variability와 output-length 차이를 고려하면 **recipe-level 성능 이득이 입증됐다고 보지 않는다**.
- 결정: **R1 candidate branch 종료**. NGRAM mechanism이 동작했다는 evidence는 보존하지만, frozen plan 밖의 NGRAM parameter tuning으로 확장하지 않는다.

R2 판정:
- R2의 intended effect는 128K x2 long-context prefill/TTFT 개선이며, request-level server prompt timing, 평균 TTFT, batch wall에서 같은 방향의 큰 변화가 관찰됐다.
- 비용은 GPU당 약 +0.29 GiB VRAM이며 capacity/stability, mechanical output integrity, C2 active topology, post-health를 유지했다.
- 결정: **R2를 Qwen3.8-27B / llama.cpp WBS5 final recipe candidate로 유지**한다. 이는 이번 track review의 candidate selection이며, optional confirm을 다시 열거나 새 candidate를 추가하는 결정이 아니다.

한계 / 종료:
- R2와 R1은 각각 screening 1회(n=1)이며 optional confirm은 사용자 결정으로 SKIP했다. 이 limitation을 그대로 보존하고 추가 반복 실행을 자동 요구하지 않는다.
- `aggregate_decode_tps`와 end-to-end TPS는 각각 overlap window와 output length 영향을 포함하므로 pure decode speedup 근거로 사용하지 않는다.
- 추가 GPU inference 없음. 다음 frozen candidate는 없으며, 이 track review에서 새 candidate를 생성하지 않는다.

#### 5.3.2 Ornith 1.5 9B / llama.cpp [NON-EXECUTABLE PARENT — FROZEN / R0-R2 MEASURED_PUBLISHED / REVIEW_COMPLETE / RECIPE_PENDING]

Frozen candidates:

| Candidate | Frozen configuration / R0 대비 exact delta |
|---|---|
| `R0 = TARGET_BASELINE` | **1GPU×2 + LiteLLM**, TARGET, batch 512, ubatch 128. |
| `R1 = TARGET_UB256` | R0에서 **`--ubatch-size 128 -> 256`만 변경**. |
| `R2 = NGRAM_DEFAULT` | R0에서 **`--spec-type none -> ngram-simple`만 변경**. batch 512 / ubatch 128 유지, NGRAM parameter tuning 금지. |

보존 invariant:
- `/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf`, SHA256 `79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480`.
- Q6_K weights / FP16 KV / llama.cpp b10775 pinned runtime.
- GPU0 backend + GPU1 backend, backend별 ctx 131072 / parallel 1 / unified KV per-slot 131072.
- LiteLLM 1.101.0 single gateway, least-busy, backend `max_parallel_requests=1`, `num_retries=0`, routing-settled admission behavior.
- FA on, Jinja, reasoning off, no-warmup, cold-independent lane.

LOCAL_VERIFY_REQUIRED:
- `run_1gpu_litellm.py`와 launcher가 `performance/v1.json` 및 R0/R1/R2 exact override를 표현하는지.
- candidate ID, exact launch config, gateway/backend evidence가 raw/planned config/report에 보존되는지.
- ubatch 256과 ngram-simple/pinned defaults의 binary support.
- active overlap/queue-only, routing evidence, post-health 및 telemetry capture 가능 여부.

실행 순서/stop:
- R0 -> R1 -> R2.
- measured 실행 전 gateway와 두 backend의 frozen topology가 exact해야 한다.
- 다른 topology/KV/context/routing delta가 섞이면 hard stop.
- final recipe 승격은 1GPU×2 + LiteLLM 배포 topology에서 `performance/v1.json` valid run과 output integrity를 요구한다.


##### 5.3.2.1 Ornith 1.5 9B llama.cpp — R0 TARGET baseline [DONE — PASS_C2_ACTIVE]

- 상태: **DONE — PASS_C2_ACTIVE** (measured child 실행/회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001`; 완료 UTC: `2026-09-28T12:48:37.150851+00:00`.
- [Raw](../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001/) / [Report](../reports/ornith-1.5-9b/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001.md); `results/summary.csv`, `reports/comparison.csv` 반영 완료.
- Routing/overlap: project-a → backend-0 (`:18080`), project-b → backend-1 (`:18081`); distinct base/deployment true, `active_overlap: true`, `backend_active_in_common_decode_window: true`, `queue_only: false`, post-health healthy.
- Requests: project-a 1,204 tokens / `PASS`, project-b 1,610 tokens / `PASS`.
- Performance: TTFT 182,019.75 ms, Prefill 697.74 tok/s, Mean Decode 43.81 tok/s, Aggregate Decode 77.73 tok/s, End-to-End 13.03 tok/s, Batch Wall 215.90s.
- Peak VRAM: GPU0 10,893 MiB / GPU1 10,893 MiB.

1GPU×2 + LiteLLM frozen topology를 유지하고 R0를 1회 수행한다. 두 backend와 단일 LiteLLM endpoint, least-busy, backend max_parallel_requests=1, num_retries=0이 바뀌면 hard stop이다.

```bash
python3 scripts/run_wbs5_remote.py --track ornith9-llama --candidate R0 --experiment-id EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.2.2 Ornith 1.5 9B llama.cpp — R1 UB256 [DONE — PASS_C2_ACTIVE]

- 상태: **DONE — PASS_C2_ACTIVE** (measured child 실행/회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001`; 완료 UTC: `2026-09-28T13:01:31.199186+00:00`.
- [Raw](../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/) / [Report](../reports/ornith-1.5-9b/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001.md); `results/summary.csv`, `reports/comparison.csv` 반영 완료.
- Routing/overlap: project-a → backend-0 (`:18080`), project-b → backend-1 (`:18081`); distinct base/deployment true, `active_overlap: true`, `backend_active_in_common_decode_window: true`, `queue_only: false`, post-health healthy.
- Requests: project-a 1,438 tokens / `PASS`, project-b 1,370 tokens / `PASS`.
- Performance: TTFT 139,204.08 ms, Prefill 912.19 tok/s, Mean Decode 43.99 tok/s, Aggregate Decode 80.90 tok/s, End-to-End 16.20 tok/s, Batch Wall 173.34s.
- Peak VRAM: GPU0 10,945 MiB / GPU1 10,945 MiB.

R0 대비 두 backend 모두 ubatch 128 -> 256만 변경된 frozen plan을 1회 수행한다.

```bash
python3 scripts/run_wbs5_remote.py --track ornith9-llama --candidate R1 --experiment-id EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.2.3 Ornith 1.5 9B llama.cpp — R2 NGRAM [DONE — PASS_C2_ACTIVE]

- 상태: **DONE — PASS_C2_ACTIVE** (measured child 실행/회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260928-001`; 완료 UTC: `2026-09-28T13:21:39.114398+00:00`.
- [Raw](../results/raw/EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260928-001/) / [Report](../reports/ornith-1.5-9b/EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260928-001.md); `results/summary.csv`, `reports/comparison.csv` 반영 완료.
- Routing/overlap: project-a → backend-0 (`:18080`), project-b → backend-1 (`:18081`); distinct base/deployment true, `active_overlap: true`, `backend_active_in_common_decode_window: true`, `queue_only: false`, post-health healthy.
- Requests: project-a 1,204 tokens / `PASS`, project-b 1,610 tokens / `PASS`.
- Performance: TTFT 182,040.10 ms, Prefill 697.67 tok/s, Mean Decode 43.21 tok/s, Aggregate Decode 76.57 tok/s, End-to-End 13.00 tok/s, Batch Wall 216.41s.
- Peak VRAM: GPU0 10,893 MiB / GPU1 10,893 MiB.
- Speculative evidence: `status=OBSERVED`, `draft_tokens=0`, `accepted_tokens=0`, `draft_count=0`, `acceptance_ratio=None`. 즉 `ngram-simple` configuration은 실행됐지만 이 measured workload에서 NGRAM draft activity는 관측되지 않았다.

R0 대비 두 backend의 `--spec-type none -> ngram-simple`만 변경한다.

```bash
python3 scripts/run_wbs5_remote.py --track ornith9-llama --candidate R2 --experiment-id EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260928-001 --run-label screening-1 --execute-measured
```

완료 후 distinct backend routing, common decode-window active overlap/queue-only, post-health, backend별 speculative counter evidence를 확인한다.

##### 5.3.2.4 Ornith 1.5 9B llama.cpp — track result review [DONE — REVIEW_COMPLETE / RECIPE_PENDING]

GPU inference 없음. 공식 publication된 R0/R1/R2의 `performance/v1.json` measured evidence만 비교했다. 세 run 모두 exact Q6_K artifact/SHA, FP16 KV, llama.cpp b10775, 1GPU×2 + LiteLLM topology, 131072 context/request, C2 independent A/B, output reserve 4096 / minimum actual output 1024, temperature 0 / top_p 1 / seed 520을 유지했다.

공통 validity:
- R0/R1/R2 모두 최종 verdict `PASS_C2_ACTIVE`, 두 request `PASS`, `mechanical_output_verdict: PASS`, post-health healthy다.
- project-a → backend-0(`:18080`), project-b → backend-1(`:18081`)의 distinct routing이 유지됐고 `active_overlap=true`, `backend_active_in_common_decode_window=true`, `queue_only=false`다.
- `performance/v1.json`에는 WBS3 semantic oracle이 없으므로 이 review는 새 semantic PASS를 선언하지 않는다. output integrity는 저장된 mechanical/non-repetition 판정 범위로 제한한다.
- graph reuse는 세 run 모두 관측됐다. reuse count는 server lifetime 범위라 candidate ranking metric으로 사용하지 않는다.
- measured repetition은 candidate당 1회다. 3% 이하 차이는 별도 반복을 자동 요구하지 않고 measurement noise 가능성을 남긴다.

성능 비교:

| Metric | R0 TARGET / ub128 | R1 TARGET / ub256 | R1 vs R0 | R2 NGRAM / ub128 | R2 vs R0 |
|---|---:|---:|---:|---:|---:|
| TTFT | 182.020 s | **139.204 s** | **-23.52%** | 182.040 s | +0.01% |
| Prefill | 697.74 tok/s | **912.19 tok/s** | **+30.73%** | 697.67 tok/s | -0.01% |
| Mean request decode | 43.81 tok/s | 43.99 tok/s | +0.40% | 43.21 tok/s | -1.38% |
| Aggregate decode | 77.73 tok/s | **80.90 tok/s** | +4.08% | 76.57 tok/s | -1.49% |
| End-to-end output | 13.03 tok/s | **16.20 tok/s** | **+24.28%** | 13.00 tok/s | -0.24% |
| Batch wall | 215.90 s | **173.34 s** | **-19.71%** | 216.41 s | +0.24% |
| Peak VRAM / GPU | 10,893 MiB | 10,945 MiB | +52 MiB / +0.48% | 10,893 MiB | 0 |

Review decision:
- **R1 `TARGET_UB256`: final recipe 후보로 유지.** 의도한 128K prefill 병목 개선이 TTFT, prefill, E2E, batch wall에서 동시에 나타났고 mean decode는 사실상 유지됐다. measured-window peak VRAM 증가는 GPU당 52 MiB뿐이었다. telemetry의 observed max는 R0 대비 power가 소폭 높았지만(R0 GPU0/1 165.96/162.29 W, R1 171.23/168.75 W), 최고 온도는 72/66°C → 71/65°C였고 SM clock 135~1200 MHz / memory clock 877 MHz 범위는 동일해 thermal/clock regression 신호가 없다.
- **R2 `NGRAM_DEFAULT`: branch 종료.** measured-window speculative counter는 `draft_tokens=0`, `accepted_tokens=0`, `draft_count=0`, `acceptance_ratio=None`이다. R0 대비 TTFT/prefill/E2E/wall은 사실상 동일하고 mean/aggregate decode 차이도 -1.38%/-1.49%로 3% 미만이다. 따라서 이 workload에서 NGRAM의 intended effect가 관측되지 않았으며, 이 작은 차이를 성능 regression으로 확정하지 않는다. NGRAM N/M tuning으로 확장하지 않는다.
- **R0 `TARGET_BASELINE`: reference/control로 유지.** valid serving baseline이지만 R1의 prefill-side 개선을 대체할 근거는 없다.
- WBS5 frozen set 밖의 MTP/MTP_NGRAM, graph-off, 추가 ubatch sweep, 새 speculative parameter 후보를 이 review에서 다시 열지 않는다.

결론:
- **5.3.2.4 track review 완료.**
- **다음 frozen candidate 없음. 추가 GPU measured inference를 자동 실행하지 않는다.**
- 후속 final recipe recording 단계에서는 R1 `TARGET / batch 512 / ubatch 256 / 1GPU×2 + LiteLLM`만 승격 대상으로 검토한다.
- 이 단계 자체는 `VALIDATED_RECIPE` 승격이 아니며, WBS5 final recipe recording의 exact command/provenance/known-limitations 정리 전까지 parent 상태를 `RECIPE_PENDING`으로 유지한다.

#### 5.3.3 Ornith 1.5 35B-A3B / llama.cpp [NON-EXECUTABLE PARENT — FROZEN / MEASURED_RESULTS_PUBLISHED / REVIEW_DONE / R1+R2 VALIDATED_RECIPE]

R0/R1/R2/R3의 유효한 measured raw 4건을 공식 report/CSV에 반영했고 `5.3.3.5` track review를 완료했다. R1의 첫 `-001` 시도는 포트 점유로 서버 기동 전에 중단된 `INCONCLUSIVE` raw로 보존하며 성능 근거에서 제외한다. 최종적으로 R1 native MTP1을 decode-oriented `VALIDATED_RECIPE`, R2 UB256을 long-prefill/latency-oriented `VALIDATED_RECIPE`로 승격했다. R0는 canonical reference baseline으로 유지하고 R3 QUEUE4X는 measurable benefit이 없어 branch 종료했다. 상세: [WBS 5.3.3.5 result review](WBS-5.3.3.5-result-review.md).

Frozen candidates:

| Candidate | Frozen configuration / R0 대비 exact delta |
|---|---|
| `ORN35-LLAMA-WBS5-R0-TARGET` | TARGET, batch 512, ubatch 128, speculative disabled. |
| `ORN35-LLAMA-WBS5-R1-MTP1` | R0에서 **native MTP `--spec-type draft-mtp --spec-draft-n-max 1`만 활성화**. |
| `ORN35-LLAMA-WBS5-R2-UB256` | R0에서 **ubatch 128 -> 256만 변경**. batch 512 유지. |
| `ORN35-LLAMA-WBS5-R3-QUEUE4X` | R0에서 **`CUDA_SCALE_LAUNCH_QUEUES=4x`만 추가**. |

보존 invariant:
- `ornith-ai/Ornith-1.5-35B-A3B-GGUF@12393612fd4f730ff5aadc23e9b8f9648aa49ceb`.
- `Ornith-1.5-35B-Q4_K_M.gguf`, SHA256 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`.
- Q4_K_M weights / Q8_0 KV / llama.cpp b10775 pinned OCI.
- shared TP2 layer split 1,1 / ctx 262144 / parallel 2 / unified KV per-slot 131072.
- FA on, Jinja, reasoning off, metrics/slots/no-warmup.
- R1은 companion GGUF가 아니라 embedded native MTP를 사용한다.

LOCAL_VERIFY_REQUIRED:
- binary `draft-mtp`, `spec-draft-n-max`, b/ub, unified-KV 지원.
- R0~R3 exact command/env one-variable diff.
- R3 env 전달 여부.
- performance runner가 prompt-progress/per-slot evidence를 포함한 required metrics를 저장 가능한지.
- 기존 WBS3의 사실상 직렬 128K×2 prefill behavior는 관찰 대상으로만 남기고 이를 고치기 위한 새 candidate를 만들지 않는다.

실행 순서/stop:
- R0 -> R1 -> R2 -> R3.
- repetition >1은 자동으로 늘리지 않는다.
- companion artifact 주입, MTP n=2, NGRAM tuning, graph tuning, P2P 강제 등 frozen set 밖 변경 금지.
- one-variable diff 실패 또는 measured validity failure는 hard stop/invalid로 처리하고 candidate를 재설계하지 않는다.
- recipe 승격은 frozen candidate exactness + valid performance evidence + output integrity를 요구한다.


##### 5.3.3.1 Ornith 1.5 35B llama.cpp — R0 TARGET

- 상태: **DONE — PASS_C2_ACTIVE** (measured raw 회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-ORNITH35-LLAMA-R0-PERF-20260928-001`; 완료 UTC: `2026-09-28T14:08:19.500480+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R0-PERF-20260928-001/) / [Report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R0-PERF-20260928-001.md); summary/comparison CSV 반영 완료.
- 두 요청 1,930/1,856 output tokens 모두 PASS; resident/active overlap true, queue-only false, post-health healthy. TTFT 791.44s, prefill 191.42 tok/s, aggregate decode 5.40 tok/s, batch wall 1176.33s, peak VRAM 12,831/12,309 MiB.

```bash
python3 scripts/run_wbs5_remote.py --track ornith35-llama --candidate R0 --experiment-id EXP-V100-WBS5-ORNITH35-LLAMA-R0-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.3.2 Ornith 1.5 35B llama.cpp — R1 native MTP1

R0 대비 embedded native MTP1만 활성화한다. companion GGUF 또는 MTP n=2를 넣지 않는다.

- 최초 시도 `EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-001`: 측정 전 18080 포트 `Address already in use`로 `INCONCLUSIVE`. [Raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-001/) 보존; 공식 performance report/CSV에는 포함하지 않는다.
- 상태: **DONE — PASS_C2_ACTIVE** (사용자 지정 동일 설정 재실행의 measured raw 회수 및 공식 publication 완료; final recipe 승격 아님).
- 유효한 Experiment: `EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002`; 완료 UTC: `2026-09-28T14:39:25.455617+00:00`. [Raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002/) / [Report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002.md); summary/comparison CSV 반영 완료.
- 두 요청 2,313/1,952 output tokens 모두 PASS; resident/active overlap true, queue-only false, post-health healthy. TTFT 833.07s, prefill 182.78 tok/s, aggregate decode 5.71 tok/s, batch wall 1242.84s, peak VRAM 12,897/13,737 MiB.
- MTP counter `OBSERVED`: draft 2,426, accepted 1,838, acceptance ratio 0.7576. 이 값과 성능 비교의 해석은 `5.3.3.5`에서 수행한다.

```bash
python3 scripts/run_wbs5_remote.py --track ornith35-llama --candidate R1 --experiment-id EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-001 --run-label screening-1 --execute-measured
```

draft/accepted/acceptance ratio가 unavailable이면 UNKNOWN으로 남긴다.

##### 5.3.3.3 Ornith 1.5 35B llama.cpp — R2 UB256

- 상태: **DONE — PASS_C2_ACTIVE** (measured raw 회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001`; 완료 UTC: `2026-09-28T15:02:03.734261+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/) / [Report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001.md); summary/comparison CSV 반영 완료.
- 두 요청 1,832/2,849 output tokens 모두 PASS; resident/active overlap true, queue-only false, post-health healthy. TTFT 670.09s, prefill 229.75 tok/s, aggregate decode 7.23 tok/s, batch wall 1038.99s, peak VRAM 13,103/12,581 MiB.

```bash
python3 scripts/run_wbs5_remote.py --track ornith35-llama --candidate R2 --experiment-id EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.3.4 Ornith 1.5 35B llama.cpp — R3 CUDA_SCALE_LAUNCH_QUEUES=4x

R0 대비 container environment의 `CUDA_SCALE_LAUNCH_QUEUES=4x`만 추가된 plan을 사용한다.

- 상태: **DONE — PASS_C2_ACTIVE** (measured raw 회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-ORNITH35-LLAMA-R3-PERF-20260928-001`; 완료 UTC: `2026-09-28T15:26:54.539768+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R3-PERF-20260928-001/) / [Report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R3-PERF-20260928-001.md); summary/comparison CSV 반영 완료.
- 두 요청 1,930/1,856 output tokens 모두 PASS; resident/active overlap true, queue-only false, post-health healthy. TTFT 791.61s, prefill 191.38 tok/s, aggregate decode 5.40 tok/s, batch wall 1176.66s, peak VRAM 12,831/12,309 MiB. `CUDA_SCALE_LAUNCH_QUEUES=4x`는 effective environment에 기록됨.

```bash
python3 scripts/run_wbs5_remote.py --track ornith35-llama --candidate R3 --experiment-id EXP-V100-WBS5-ORNITH35-LLAMA-R3-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.3.5 Ornith 1.5 35B llama.cpp — track result review [DONE]

GPU inference 없이 published raw/report만 사용해 R0/R1/R2/R3의 frozen one-variable delta, 성능, VRAM, output integrity, overlap, telemetry, speculative evidence를 비교했다. 기존 WBS3/WBS5에서 관찰된 사실상 직렬 128K prefill behavior를 수정하기 위한 새 candidate는 추가하지 않았다.

- R0 TARGET: canonical measured reference baseline. 두 요청 PASS / active overlap true / queue-only false / post-health healthy.
- R1 native MTP1: **VALIDATED_RECIPE — DECODE_ORIENTED**. MTP 2,426 draft / 1,838 accepted = 75.76%; request-A runtime decode 28.13 -> 31.98 tok/s (+13.70%), mean request decode +12.49%. 반면 prefill -4.51%, TTFT +5.26%, batch wall +5.65%, GPU1 peak +1,428 MiB이므로 128K prefill latency winner로 해석하지 않는다.
- R2 UB256: **VALIDATED_RECIPE — LONG_PREFILL_LATENCY_ORIENTED**. R0의 `b=512`를 유지하고 `ub=128 -> 256`만 변경해 prefill +20.03%, TTFT -15.33%, batch wall -11.68%를 관찰했다. Peak VRAM은 +272 MiB/GPU. Request-level decode 변화는 serialized prefill/scheduling 영향을 포함하므로 decode speedup으로 주장하지 않는다.
- R3 QUEUE4X: **CLOSED — NO MEASURABLE BENEFIT**. `CUDA_SCALE_LAUNCH_QUEUES=4x`가 container effective environment에 실제 적용됐지만 R0 대비 핵심 metric이 약 ±0.1% 내이고 peak VRAM 및 실제 generated text도 R0와 동일했다.
- `aggregate_decode_tps`는 total output / (latest end - earliest first content)의 mixed system-throughput metric이며 pure decode-kernel metric이 아니다. per-request prefill/decode는 llama.cpp runtime timings를 사용한다.
- R1+R2 효과가 additive라는 evidence는 없다. combined recipe나 MTP n=2 등 새 candidate를 추가하지 않는다.
- WBS5 performance workload에는 WBS3 semantic oracle가 없으므로 이 승격은 serving/performance/mechanical output-integrity 범위다.

상세 metric semantics, candidate별 분석, exact measured launch command, telemetry 및 limitation: [docs/WBS-5.3.3.5-result-review.md](WBS-5.3.3.5-result-review.md).

#### 5.3.4 Gemma4 26B-A4B / llama.cpp [NON-EXECUTABLE PARENT — R0/R1/R2 PUBLISHED / R3 SKIP / REVIEW DONE — R0 RETAINED]

Frozen candidates:

| Candidate | Frozen configuration / R0 대비 exact delta |
|---|---|
| `G4-LCPP-WBS5-R0-TARGET-B512-UB128` | TARGET, batch 512, ubatch 128, FP16 KV. |
| `G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128` | R0에서 **`--spec-type none -> ngram-simple`만 변경**. explicit N/M/hits override 금지. |
| `G4-LCPP-WBS5-R2-TARGET-B1024-UB128` | R0에서 **`--batch-size 512 -> 1024`만 변경**. ubatch 128 유지. |
| `G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF` | **CONDITIONAL**. R0에서 graph-off 축만 변경하며 실제 option/binary support와 Gate B를 만족할 때만 실행. |

보존 invariant:
- `unsloth/gemma-4-26B-A4B-it-qat-GGUF@7b92b5b28818151e8669af2e45e88d6086f490dd`.
- `gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf`, SHA256 `a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891`.
- UD-Q4_K_XL weights / FP16 KV / llama.cpp b10775 pinned OCI.
- shared TP2 layer split 1,1 / ctx 262144 / parallel 2 / unified KV per-slot 131072 / FA on.

LOCAL_VERIFY_REQUIRED:
- pinned binary의 layer/tensor split, unified-KV, b/ub, ngram-simple 및 default 12/48/1.
- CUDA Graph compile/support status와 `GGML_CUDA_DISABLE_GRAPHS`의 실제 유효성.
- R3의 graph control을 model load 없이 증명할 수 없으면 `VERIFY_DURING_R0_STARTUP`으로 남긴다.
- R3 Gate B인 **R0 VRAM upward drift 또는 graph-related instability**는 measured evidence 전에는 `PENDING_MEASURED_EVIDENCE`다.

실행 순서/stop:
- R0 -> R1 -> R2. R3는 static support 확인 후에도 Gate B가 충족될 때만 조건부 실행한다.
- R3 gate가 충족되지 않아도 대체 candidate를 추가하지 않는다.
- artifact/runtime/binary/workload mismatch 또는 OFAT diff 위반은 hard stop.
- final recipe 승격은 valid measured evidence와 output integrity를 요구하며, R3는 conditional status를 그대로 보존한다.


##### 5.3.4.1 Gemma4 llama.cpp — R0 TARGET baseline

R3 Gate B의 근거가 되는 baseline이므로 성능뿐 아니라 graph support/instability와 VRAM telemetry를 반드시 보존한다.

- 상태: **DONE — PASS_C2_ACTIVE** (measured raw 회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001`; 완료 UTC: `2026-09-28T15:54:35.290671+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/) / [Report](../reports/gemma4-26b-a4b/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001.md); summary/comparison CSV 반영 완료.
- 두 요청 1,603/1,610 output tokens 모두 PASS; resident/active overlap true, queue-only false, post-health healthy. TTFT 439.10s, prefill 359.09 tok/s, aggregate decode 7.54 tok/s, batch wall 671.54s, peak VRAM 10,039/10,537 MiB. Graph reuse `OBSERVED` 4,425회. Gate B 판정은 5.3.4.4에 기록했다.

```bash
python3 scripts/run_wbs5_remote.py --track gemma-llama --candidate R0 --experiment-id EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.4.2 Gemma4 llama.cpp — R1 NGRAM

- 상태: **DONE — PASS_C2_ACTIVE** (measured raw 회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001`; 완료 UTC: `2026-09-28T16:10:03.752064+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001/) / [Report](../reports/gemma4-26b-a4b/EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001.md); summary/comparison CSV 반영 완료.
- 두 요청 1,462/1,635 output tokens 모두 PASS; resident/active overlap true, queue-only false, post-health healthy. TTFT 448.49s, prefill 353.18 tok/s, aggregate decode 7.10 tok/s, batch wall 685.38s, peak VRAM 10,039/10,607 MiB. NGRAM counter는 draft 144, accepted 54 (37.5%)로 기록됐다. 성능 해석은 5.3.4.6에서 수행한다.

```bash
python3 scripts/run_wbs5_remote.py --track gemma-llama --candidate R1 --experiment-id EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.4.3 Gemma4 llama.cpp — R2 batch1024

R0 대비 batch-size 512 -> 1024만 변경한다. VRAM fit은 runtime 결과로 판정한다.

- 상태: **DONE — PASS_C2_ACTIVE** (measured raw 회수 및 공식 publication 완료; final recipe 승격 아님).
- Experiment: `EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001`; 완료 UTC: `2026-09-28T16:25:05.340707+00:00`.
- [Raw](../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001/) / [Report](../reports/gemma4-26b-a4b/EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001.md); summary/comparison CSV 반영 완료.
- 두 요청 1,633/1,570 output tokens 모두 PASS; resident/active overlap true, queue-only false, post-health healthy. TTFT 440.10s, prefill 355.46 tok/s, aggregate decode 7.60 tok/s, batch wall 670.94s, peak VRAM 10,039/10,537 MiB. 성능 해석은 5.3.4.6에서 수행한다.

```bash
python3 scripts/run_wbs5_remote.py --track gemma-llama --candidate R2 --experiment-id EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.3.4.4 Gemma4 llama.cpp — Gate B evaluation

GPU inference 없음. 5.3.4.1 R0의 실제 raw evidence만 사용한다.

**2026-09-29 판정: `NOT_TRIGGERED`.** R0 `EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001`은 `PASS_C2_ACTIVE`이고 graph reuse 4,425회가 기록됐다. GPU telemetry에서 모델 로딩 후 GPU0/GPU1 사용량은 10,033/10,531 MiB로 약 10분 33초간 일정했고, 종료 직전 약 39초에 각각 6 MiB 증가한 뒤 서버 종료 시 해제됐다. 이 단발성 6 MiB 변화는 지속적인 `R0_VRAM_UPWARD_DRIFT`의 증거가 아니다. 서버 로그에는 graph-related error/instability가 없고 두 요청 모두 완료되어 `R0_GRAPH_INSTABILITY`도 관찰되지 않았다. 따라서 PASS receipt를 발급하지 않으며 5.3.4.5는 **SKIP**한다. 근거: R0 `runtime/gpu-telemetry.jsonl`, `runtime/server-0.log`, `graph-evidence.json`, `metrics.json`, `completion.json`.

- `R0_VRAM_UPWARD_DRIFT` 또는 `R0_GRAPH_INSTABILITY` 중 실제 관찰된 frozen trigger가 있어야 한다.
- graph support evidence가 PASS여야 한다.
- trigger가 없으면 `NOT_TRIGGERED`로 기록하고 5.3.4.5를 **SKIP**한다. R3를 돌리기 위해 trigger를 임의 해석하지 않는다.
- PASS인 경우 `results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/gate-b-receipt.json`을 작성한다.
- receipt는 실제 R0 `config.json`, `identity.json`, `metrics.json`, `completion.json`을 evidence로 포함하고 각각 현재 SHA256을 기록한다. baseline configuration SHA는 R0 candidate-plan의 값과 일치해야 한다.

##### 5.3.4.5 Gemma4 llama.cpp — R3 GRAPH-OFF [CONDITIONAL]

5.3.4.4 Gate B PASS receipt가 있을 때만 수행한다.

**SKIP — Gate B `NOT_TRIGGERED` (2026-09-29).** R3 측정은 실행하지 않는다.

```bash
python3 scripts/run_wbs5_remote.py --track gemma-llama --candidate R3 --experiment-id EXP-V100-WBS5-GEMMA-LLAMA-R3-PERF-20260928-001 --run-label screening-1 --gate-receipt results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/gate-b-receipt.json --execute-measured
```

Gate B 미충족은 R3 failure가 아니라 conditional candidate의 정상 SKIP이다.

##### 5.3.4.6 Gemma4 llama.cpp — track result review [DONE — R0 RETAINED]

GPU inference 없음. 이미 publication된 R0/R1/R2 raw만 사용해 frozen one-variable delta를 비교했다. R3는 5.3.4.4 Gate B가 `NOT_TRIGGERED`이므로 미실행 상태를 그대로 보존하며 대체 candidate를 추가하지 않는다.

Evidence scope:
- R0: `EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001` — TARGET, b512/ub128.
- R1: `EXP-V100-WBS5-GEMMA-LLAMA-R1-PERF-20260928-001` — R0 대비 `--spec-type none -> ngram-simple`만 변경.
- R2: `EXP-V100-WBS5-GEMMA-LLAMA-R2-PERF-20260928-001` — R0 대비 `--batch-size 512 -> 1024`만 변경, ub128 유지.
- 세 run 모두 `PASS_C2_ACTIVE`, resident/active overlap true, queue-only false, 두 요청 output minimum 1,024 tokens 충족, normal stop, post-health healthy다.

| Metric | R0 TARGET b512 | R1 NGRAM | R1 vs R0 | R2 TARGET b1024 | R2 vs R0 |
|---|---:|---:|---:|---:|---:|
| TTFT | 439.10 s | 448.49 s | +2.14% | 440.10 s | +0.23% |
| Prefill | 359.09 tok/s | 353.18 tok/s | -1.64% | 355.46 tok/s | -1.01% |
| Mean request decode | 22.54 tok/s | 21.48 tok/s | -4.69% | 22.28 tok/s | -1.15% |
| Aggregate decode | 7.54 tok/s | 7.10 tok/s | -5.92% | 7.60 tok/s | +0.72% |
| End-to-end output | 4.78 tok/s | 4.52 tok/s | -5.56% | 4.77 tok/s | -0.22% |
| Batch wall | 671.54 s | 685.38 s | +2.06% | 670.94 s | -0.09% |
| Peak VRAM GPU0/GPU1 | 10,039 / 10,537 MiB | 10,039 / 10,607 MiB | 0 / +70 MiB | 10,039 / 10,537 MiB | no change |

Capacity / stability:
- R0/R1/R2 모두 C2 active overlap을 유지했고 OOM/crash/server-health failure가 없다.
- R2의 b1024는 capacity/VRAM penalty를 만들지 않았지만 R0 대비 성능 이득도 만들지 않았다.

Output integrity:
- R0 outputs: 1,603 / 1,610 tokens, 둘 다 PASS / `finish_reason=stop`.
- R1 outputs: 1,462 / 1,635 tokens, 둘 다 PASS / `finish_reason=stop`.
- R2 outputs: 1,633 / 1,570 tokens, 둘 다 PASS / `finish_reason=stop`.
- 이 performance workload의 PASS를 별도 semantic superiority로 확대 해석하지 않는다.

Power / temperature / clocks:
- R0 max power GPU0/GPU1 169.00 / 161.46 W, max temp 61 / 58 C.
- R1 max power 169.35 / 159.58 W, max temp 60 / 58 C.
- R2 max power 168.88 / 161.93 W, max temp 61 / 58 C.
- 세 run 모두 observed max SM clock 1,200 MHz, memory clock 877 MHz. R1/R2에서 유의미한 thermal/clock advantage 또는 penalty는 관찰되지 않았다.

Speculative / topology behavior:
- R1 NGRAM counter는 draft 144, accepted 54, acceptance 37.5%로 실제 speculative activity가 있었다. 그러나 acceptance가 aggregate/E2E 개선으로 연결되지 않았다.
- R0/R1/R2 모두 동일한 2-GPU layer-split shared topology에서 active overlap을 유지했다.
- 요청별 decode 비대칭은 R0 약 41.26 / 3.82 tok/s, R2 약 40.81 / 3.75 tok/s로 유지됐다. R2의 larger logical batch가 topology behavior를 실질적으로 바꿨다는 evidence는 없다.

Candidate decision:
- **R1 NGRAM branch 종료.** R0 대비 mean decode -4.69%, aggregate decode -5.92%, E2E -5.56%, wall +2.06%이고 GPU1 peak VRAM도 70 MiB 증가했다. NGRAM acceptance 37.5%만으로 유지하지 않으며 N/M/hits 또는 다른 NGRAM variant를 추가하지 않는다.
- **R2 batch1024 branch 종료.** intended effect였던 TTFT/prefill 개선이 나타나지 않았다. 모든 주요 delta가 약 ±1.2% 이내이며 aggregate +0.72%도 E2E/wall 개선으로 이어지지 않았다. 이는 single-run measurement noise 가능성을 포함하는 미세 차이로 취급하고 자동 반복 측정을 요구하지 않는다. b2048/ubatch grid도 추가하지 않는다.
- **R3 GRAPH-OFF는 SKIP 유지.** R0에서 graph reuse 4,425회가 관찰됐지만 약 10분 33초 동안 VRAM이 안정적이었고 graph-related error/instability가 없어서 Gate B가 `NOT_TRIGGERED`였다. 미실행은 candidate failure가 아니다.
- **R0 TARGET b512/ub128만 final recipe 후보로 유지한다.** 이 단계에서는 5.5 publication 이전이므로 `VALIDATED_RECIPE`로 최종 승격하지 않고, track review 결과로서 승격 대상 configuration을 고정한다.

Track result review 결론:
- candidate branch 종료: R1, R2.
- conditional skip: R3.
- final recipe 승격 대상으로 유지: `G4-LCPP-WBS5-R0-TARGET-B512-UB128`.
- 새 candidate 추가 없음, 추가 GPU inference 없음.


### 5.4 1Cat-vLLM frozen tracks

1Cat-vLLM common identity는 pinned **1Cat-vLLM 1.5.0** / wheel SHA256
`2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b`를 기준으로 local verification한다.
설치 package tree만으로 wheel SHA를 추정하지 않으며 local wheel 원본이 없으면 provenance 한계를 명시한다.

#### 5.4.1 Qwen3.8-27B / 1Cat-vLLM [NON-EXECUTABLE PARENT — REVIEW COMPLETE / NO ELIGIBLE RECIPE]

2026-09-29 회수된 WBS 5.4.1.1/.2/.3의 `screening-1` 결과를 기록했다. 세 실행의 raw evidence, 개별 report, `results/summary.csv`, `reports/comparison.csv`를 보존한다.

| WBS | Candidate | Measured verdict | Evidence 범위 |
|---|---|---|---|
| 5.4.1.1 | R0 E4M3 | `QUEUE_ONLY` | 126,975/126,976 prompt tokens의 두 요청 완료, 7,788 output tokens, mechanical output PASS. C2 resident/active false. |
| 5.4.1.2 | R1 CUDA Graph | `FAIL_STARTUP` | Torch Inductor compile 중 GPU0 CUDA OOM (1.19 GiB allocation 시도, free 911.50 MiB). 측정 요청과 graph capture/replay evidence 없음. |
| 5.4.1.3 | R3 E5M2 | `QUEUE_ONLY` | R0와 같은 두 요청 완료, 7,788 output tokens, mechanical output PASS. C2 resident/active false. |

R0/R3의 수치는 이번 queue-only 실행에서 관측한 값이며 C2 ACTIVE 성능 수치가 아니다. Mechanical output PASS는 task-level semantic acceptance를 뜻하지 않는다. 5.4.1.5 review 결과 현재 frozen WBS5 evidence만으로 final recipe 승격 조건을 충족하는 candidate는 없다. R3는 R0보다 queue-only prefill/TTFT/wall 관측이 크게 개선됐지만 C2 ACTIVE와 task-level semantic qualification이 없어서 승격하지 않는다. R1은 FAIL_STARTUP, R2의 host toolchain blocker는 유지한다.

현재 evidence를 다음처럼 분리한다.

- E4M3 TP2 shared에서 **128K C1 physical capacity 성공 evidence가 존재**한다.
- B200-aligned diagnostic에서 **128,834 prompt tokens 수용 + completion decode 완료**가 기록되어 있다.
- 같은 실행에는 mechanical non-repetition completion evidence가 있다.
- authoritative `FAIL_OUTPUT`은 해당 synthetic/semantic audit의 task-level correctness failure이며 startup/capacity failure와 동일하지 않다.
- 기존 C2 evidence에는 `QUEUE_ONLY`가 존재하므로 **C2 ACTIVE가 검증됐다고 쓰지 않는다**.
- 따라서 이 track을 blanket `BLOCKED — semantic revalidation required`로 닫지 않는다. 다만 위 evidence를 WBS5 performance PASS로 승격하지도 않는다.

Frozen candidates:

| Candidate | Frozen axis |
|---|---|
| `R0-E4M3-128K-SEMANTIC-BASELINE` | E4M3 128K semantic baseline. LM-only, max len 131072, max seqs 1, MBT 2048, util 0.92, eager, `FLASH_ATTN_V100`, decode partition 256의 feasibility를 local source에서 검증. |
| `R1-E4M3-128K-CUDAGRAPH-C1` | R0의 E4M3 baseline에서 **CUDA Graph C1 축만** 변경. exact CLI/config key, capture-size `[1]`, mode는 pinned local source에서 확정해야 한다. |
| `R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL` | R0에서 **Original FlashQLA prefill route 축만** 변경. `VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL`의 exact 0/1 semantics와 route 조건은 local source 검증 전 확정하지 않는다. |
| `R3-E5M2-128K-KV-ROUTE` | R0에서 **KV dtype을 explicit `fp8_e4m3 -> fp8_e5m2` 축으로만 변경**. generic `fp8` alias는 candidate가 아니다. |

LOCAL_VERIFY_REQUIRED:
- actual pinned runtime/model/native-extension identity.
- `speculators_config`와 `mtp_num_hidden_layers`를 구분한 model metadata.
- R0 option/default 및 speculative auto-enable 가능성.
- R1 exact graph syntax/mode/capture shape와 TP2/GDN/Flash-V100 graph path.
- R2 original FlashQLA env semantics, module/TileLang 존재, static compile prerequisites.
- R3 explicit E5M2 parser/SM70/Flash-V100 route 및 GDN recurrent-state 영향.
- launcher/service environment contamination audit.
- R1/R2/R3가 R0 대비 정확히 한 축만 바뀌는지 normalized diff.

실행 순서/stop:
- local validation은 R0 -> R1 -> R2 -> R3.
- measured phase admission은 local validation과 ChatGPT pre-run final validation 이후 별도로 결정한다. frozen 상태 자체를 measured validation으로 간주하지 않는다.
- R0 semantic baseline의 measured output이 final recipe로 승격되려면 task-level semantic/output integrity를 통과해야 한다.
- C2 performance claim에는 `performance/v1.json`에서 active-overlap 여부를 새 evidence로 기록해야 하며 기존 `QUEUE_ONLY`를 ACTIVE로 재해석하지 않는다.
- unsupported/unknown local route는 해당 candidate를 local blocker로 남기고 대체 tuning을 추가하지 않는다.


##### 5.4.1.1 Qwen3.8 1Cat-vLLM — R0 E4M3 semantic baseline

실행 완료: `EXP-V100-WBS5-QWEN-ONECAT-R0-PERF-20260928-001` → **QUEUE_ONLY**. 두 요청이 각각 126,975/126,976 prompt tokens와 3,692/4,096 output tokens로 완료됐고 mechanical output은 PASS였다. `max-num-seqs=1` 실행에서 server sampler의 peak processing 1 / waiting 1, C2 resident=false, active=false다. TTFT 1,298,200.34 ms, aggregate decode 5.02 tok/s, batch wall 2,270.90 s는 queue-only 관측값이다. [개별 report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-ONECAT-R0-PERF-20260928-001.md). Semantic baseline의 task-level correctness는 미판정이다.

공통 invariant인 `VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0`, `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`, `VLLM_SM70_GDN_DECODE_FLASHQLA=0`을 유지한다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-onecat --candidate R0 --experiment-id EXP-V100-WBS5-QWEN-ONECAT-R0-PERF-20260928-001 --run-label screening-1 --execute-measured
```

기존 QUEUE_ONLY 결과를 ACTIVE로 재해석하지 말고 이번 performance run의 실제 overlap evidence를 기록한다.

##### 5.4.1.2 Qwen3.8 1Cat-vLLM — R1 CUDA Graph C1 axis

실행 종료: `EXP-V100-WBS5-QWEN-ONECAT-R1-PERF-20260928-001` → **FAIL_STARTUP**. EngineCore 초기화 중 Torch Inductor compile의 CUDA OOM으로 서버가 종료됐다. 측정 요청이 없어서 C1/C2, throughput, graph capture/replay를 판정할 수 없다. [개별 report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-ONECAT-R1-PERF-20260928-001.md). 기존 frozen 설정의 성공 evidence로 취급하지 않는다.

R0 대비 eager 제거 + frozen capture config `{"cudagraph_capture_sizes":[1]}` 축만 적용한다. 실제 capture/replay는 runtime evidence로만 판정한다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-onecat --candidate R1 --experiment-id EXP-V100-WBS5-QWEN-ONECAT-R1-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.4.1.3 Qwen3.8 1Cat-vLLM — R3 E5M2

실행 완료: `EXP-V100-WBS5-QWEN-ONECAT-R3-PERF-20260928-001` → **QUEUE_ONLY**. R0와 동일한 두 요청과 7,788 output tokens를 완료했고 mechanical output은 PASS였다. Server sampler의 peak processing 1 / waiting 1, C2 resident=false, active=false다. TTFT 470,113.08 ms, aggregate decode 7.86 tok/s, batch wall 1,160.41 s는 queue-only 관측값이다. [개별 report](../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-ONECAT-R3-PERF-20260928-001.md). E5M2 route의 task-level correctness 및 C2 ACTIVE 이득은 미판정이다.

현재 기본 실행 queue에서는 toolchain-blocked R2보다 먼저 수행한다. R0 대비 KV dtype E4M3 -> E5M2만 변경하고 GDN decode/prefill 공통 invariant는 유지한다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-onecat --candidate R3 --experiment-id EXP-V100-WBS5-QWEN-ONECAT-R3-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.4.1.4 Qwen3.8 1Cat-vLLM — R2 Original FlashQLA [BLOCKED_BY_HOST_TOOLCHAIN]

현재는 **실행 금지**다. 이 WBS를 지시받아도 Codex/Luna는 CUDA toolkit, driver, package, PATH, CUDA_HOME을 임의 설치/변경하지 않는다. 먼저 current toolchain receipt에서 nvcc와 승인된 isolated CUDA development toolkit이 실제로 제공되고 compile-only discovery가 PASS했는지 확인한다. 미충족이면 blocker를 보고하고 종료한다.

승인된 host change와 새 operational toolchain receipt까지 완료된 경우에만 아래 measured command를 사용할 수 있다.

```bash
python3 scripts/run_wbs5_remote.py --track qwen-onecat --candidate R2 --experiment-id EXP-V100-WBS5-QWEN-ONECAT-R2-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.4.1.5 Qwen3.8 1Cat-vLLM — track result review [DONE — REVIEW_COMPLETE / NO ELIGIBLE RECIPE]

GPU inference 없이 publication된 R0/R1/R3와 R2 blocker를 검토했다. 상세 기록: [5.4.1.5 result review](WBS-5.4.1.5-result-review.md).

- R0/R3는 동일 7,788 output tokens를 완료했지만 둘 다 `max-num-seqs=1`, C2 active=false, `QUEUE_ONLY`다.
- R3 E5M2는 queue-only 관측에서 R0 대비 TTFT -63.79%, prefill +275.55%, batch wall -48.90%였지만 Peak VRAM이 GPU당 15,567 -> 16,117 MiB로 증가했고 task-level semantic qualification이 없다. C2 recipe로 승격하지 않는다.
- R1은 Torch Inductor compile CUDA OOM의 `FAIL_STARTUP`; graph capture/replay 성능 evidence가 없다.
- R2는 `BLOCKED_BY_HOST_TOOLCHAIN` 상태로 미실행이며 validated/failure로 재분류하지 않는다.
- 결론: 현재 frozen WBS5 evidence에서 5.5 final recipe로 넘길 Qwen 1Cat candidate는 없다. 새 candidate와 추가 inference를 만들지 않는다.

#### 5.4.2 Ornith 1.5 9B / 1Cat-vLLM [NON-EXECUTABLE PARENT — REVIEW COMPLETE / NO ELIGIBLE RECIPE — G0 SEMANTIC FAIL]

2026-09-29 회수된 G0 3회와 performance diagnostic R0~R3 4회를 개별 report 및 summary/comparison CSV에 등록했다. G0 `-001`은 runtime preflight `INCONCLUSIVE`다. G0 `-002`/`-003`은 raw C2 ACTIVE 및 mechanical PASS이지만 Project B가 사전 등록된 `JobQueue.pop` check→await→heappop race 대신 `_sequence` 문제를 지목했으므로 publication 최종 판정은 **FAIL_OUTPUT**이다. `-003/semantic-audit.json`과 두 응답을 근거로 삼았으며 G0 PASS receipt는 없다. [G0 raw](../results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003/) / [G0 report](../reports/ornith-1.5-9b/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003.md).

| WBS | Candidate | 최종 판정 | C2 | TTFT / aggregate decode / wall | 출력·효과 증거 |
|---|---|---|---|---|---|
| 5.4.2.2 | R0 baseline | `FAIL_OUTPUT` | active, queue=false | 299.28 s / 14.85 tok/s / 478.89 s | A PASS, B FAIL; MTP 1,131/1,552 accepted. |
| 5.4.2.3 | R1 MBT8192 | `FAIL_OUTPUT` | active, queue=false | 299.38 s / 14.85 tok/s / 478.98 s | A PASS, B FAIL; R0와 성능 차이 미미. |
| 5.4.2.4 | R2 target graph | `FAIL_OUTPUT` | active, queue=false | 302.53 s / 19.53 tok/s / 413.14 s | A PASS, B FAIL; graph capture/replay `UNKNOWN`. |
| 5.4.2.5 | R3 MTP2 | `FAIL_OUTPUT` | active, queue=false | 302.16 s / 17.32 tok/s / 459.76 s | A PASS, B FAIL; 1,462/2,580 accepted, ratio 56.67%; graph `UNKNOWN`. |

R0~R3 모두 G0 FAIL receipt를 사용한 `performance_diagnostic=true` 실행이다. 출력 토큰 수가 2,184~2,754로 다르고 각 실행의 Project B가 실패했으므로 aggregate decode/wall 차이는 관측값으로만 둔다. 평균 request decode는 성공한 Project A만 반영한다. 어느 후보도 semantic-qualified recipe로 승격하지 않는다. 각 [R0](../reports/ornith-1.5-9b/EXP-V100-WBS5-ORNITH9-ONECAT-R0-PERF-20260928-001.md), [R1](../reports/ornith-1.5-9b/EXP-V100-WBS5-ORNITH9-ONECAT-R1-PERF-20260928-001.md), [R2](../reports/ornith-1.5-9b/EXP-V100-WBS5-ORNITH9-ONECAT-R2-PERF-20260928-001.md), [R3](../reports/ornith-1.5-9b/EXP-V100-WBS5-ORNITH9-ONECAT-R3-PERF-20260928-001.md) report 참조.

Frozen candidates:

| Candidate | Frozen configuration / R0 대비 exact delta |
|---|---|
| `ORN15-9B-1CAT-WBS5-R0-BASELINE` | NVFP4 TP2, FP16 KV, max len 131072, max seqs 2, MBT 4096, util 0.90, target `FLASH_ATTN_V100` eager, speculative MTP1, drafter `TRITON_ATTN`. |
| `ORN15-9B-1CAT-WBS5-R1-MBT8192` | R0에서 **MBT 4096 -> 8192만 변경**. |
| `ORN15-9B-1CAT-WBS5-R2-TARGET-GRAPH` | R0에서 **target `--enforce-eager` 제거만 변경**. MTP speculative config 유지. |
| `ORN15-9B-1CAT-WBS5-R3-MTP2` | R0에서 **`num_speculative_tokens 1 -> 2`만 변경**. target eager와 MBT 4096은 R0 값으로 유지. |

보존 invariant:
- `ornith-ai/Ornith-1.5-9B-NVFP4@155f200d85ad58464571c77d5e1122ea5d419d7b`.
- `/srv/models/ornith-1.5-9b-nvfp4`.
- TP2 / CUDA-visible GPU 0,1 / NVFP4 / FP16 KV / max seqs 2 / baseline MBT 4096 / util 0.90.
- target `FLASH_ATTN_V100`; R0/R1/R3 target eager; speculative MTP baseline depth 1; drafter `TRITON_ATTN`.
- prefix caching 및 pinned runtime의 linear-attention/Mamba defaults를 candidate tuning으로 변경하지 않는다.

LOCAL_VERIFY_REQUIRED:
- runtime/model identity, exact-SM70 NVFP4 TurboMind path, prefix/Mamba/MTP defaults.
- R1 MBT 8192 static admission 및 verifier graph-shape dependency.
- R2 target graph eligibility, expected MTP1 decode query/capture shapes, automatic graph/compile side effects.
- R3 exact `mtp_num_hidden_layers`, n_predict derivation, MTP2 validation rule, same-layer reuse 여부, expected graph shapes.
- prefix-cache common-prefix length을 static하게 알 수 없으면 `NEEDS FUTURE RUNTIME CHECK`.
- metric formula와 normalized R0~R3 command diff.

Admission gate:
- WBS3 Project B semantic discrepancy 때문에 WBS5 measured candidate 전에 별도 **G0 semantic requalification**이 필요하다.
- G0는 pre-registered WBS3 concurrency semantic oracle를 사용하며 이 planning integration에서 실행하지 않는다.
- G0 전에 workload/oracle path/hash와 seeded `JobQueue.pop` check -> await -> heappop race가 그대로인지 local validation한다.
- G0 PASS 전에는 final recipe 승격을 차단한다. 사용자 지정 R0 ~ R3 performance diagnostic은 G0 semantic FAIL을 hash-bound evidence로 기록하고 `--performance-diagnostic`을 명시한 경우에만 허용한다. 이 결과는 throughput/VRAM 관찰용이며 semantic PASS 또는 validated recipe로 간주하지 않는다.

실행 순서/stop:
- local validation: R0 -> R1 -> R2 -> R3.
- G0 admission -> ChatGPT pre-run validation -> WBS5 measured sequence. G0 semantic FAIL이 기록된 경우에는 아래 명시적 performance diagnostic 경로만 허용하며 final recipe 승격은 보류한다.
- frozen delta 이외 hidden effective change가 발견되면 해당 candidate는 measured admission 전에 stop/block.
- final recipe 승격에는 G0 admission, valid `performance/v1.json` evidence, output integrity, active-overlap/telemetry provenance가 필요하다.


##### 5.4.2.1 Ornith 1.5 9B 1Cat-vLLM — G0 semantic requalification [DONE — SEMANTIC FAIL]

이 항목은 WBS5 performance candidate가 아니라 **R0 ~ R3 공통 admission prerequisite**다. pre-registered WBS3 `concurrency/v2.json`과 `v2-ground-truth.json`을 사용한 별도 measured experiment를 수행한다.

첫 시도 `EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-001`은 원격 G0 프로세스에 `V100_1CAT_PYTHON`이 전달되지 않아 runtime preflight에서 `INCONCLUSIVE`로 종료했다. 이후 `-002`와 사용자 지정 `-003` 모두 raw `PASS_C2_ACTIVE`였지만 Project B가 pre-registered `JobQueue.pop` 결함 대신 `_sequence` 결함을 제시해 semantic audit는 FAIL이다. G0 원격 실행은 WBS5 1Cat 후보와 동일한 pinned Python을 사용한다.

```bash
python3 scripts/run_wbs5_remote.py --ornith9-g0 --experiment-id EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-002
```

실행 후 Project A/B 응답을 ground-truth oracle에 대해 semantic audit한다. 두 project 모두 PASS하고 raw measured evidence가 유효할 때만 `results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-002/g0-receipt.json`을 작성한다.

G0 receipt 필수 의미:

- `gate=ORNITH9_G0`, `verdict=PASS`, `track=ornith9-onecat`.
- `baseline_configuration_sha256`은 frozen WBS5 R0 candidate-plan의 configuration SHA.
- `experiment_id`는 위 별도 G0 experiment ID.
- `semantic_audit=PASS`, `project_a=PASS`, `project_b=PASS`.
- `file_sha256`에 현재 input lock의 `workloads/concurrency/v2.json` 및 `workloads/concurrency/v2-ground-truth.json` SHA를 기록.
- `evidence`에는 위 G0 raw directory 내부의 실제 semantic/requests/metrics/completion evidence 경로와 SHA256을 기록.

semantic audit가 불명확하거나 한 project라도 FAIL이면 PASS receipt를 만들지 않고 정식 G0 admission을 차단한다. 별도 hash-bound FAIL receipt와 `--performance-diagnostic`을 사용하는 R0 ~ R3 성능 진단만 예외로 허용한다.

##### 5.4.2.2 Ornith 1.5 9B 1Cat-vLLM — R0 baseline [DIAGNOSTIC DONE — FAIL_OUTPUT]

2026-09-29 사용자 지시에 따라 G0 `-003`의 semantic FAIL을 명시한 **performance diagnostic**으로 R0 baseline을 한 번 측정한다. G0 PASS receipt를 만들거나 주장하지 않는다. `g0-diagnostic-receipt.json`은 `-003`의 semantic audit, requests, metrics, completion, progress SHA를 묶는다. R0 raw에는 `performance_diagnostic=true`를 기록한다. 이 결과는 성능 관찰용이며 final recipe 승격에는 부적격이다.

```bash
python3 scripts/run_wbs5_remote.py --track ornith9-onecat --candidate R0 --experiment-id EXP-V100-WBS5-ORNITH9-ONECAT-R0-PERF-20260928-001 --run-label screening-1 --gate-receipt results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003/g0-diagnostic-receipt.json --performance-diagnostic --execute-measured
```

##### 5.4.2.3 Ornith 1.5 9B 1Cat-vLLM — R1 MBT8192 [DIAGNOSTIC DONE — FAIL_OUTPUT]

G0 `-003` semantic FAIL은 유지한다. 아래 명령은 R1을 성능 진단으로 한 번 측정하며 `g0-diagnostic-portable-receipt.json`이 G0 raw와 source-checkout baseline을 묶는다. 결과는 final recipe 승격에 사용할 수 없다.

```bash
python3 scripts/run_wbs5_remote.py --track ornith9-onecat --candidate R1 --experiment-id EXP-V100-WBS5-ORNITH9-ONECAT-R1-PERF-20260928-001 --run-label screening-1 --gate-receipt results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003/g0-diagnostic-portable-receipt.json --performance-diagnostic --execute-measured
```

##### 5.4.2.4 Ornith 1.5 9B 1Cat-vLLM — R2 TARGET-GRAPH [DIAGNOSTIC DONE — FAIL_OUTPUT]

```bash
python3 scripts/run_wbs5_remote.py --track ornith9-onecat --candidate R2 --experiment-id EXP-V100-WBS5-ORNITH9-ONECAT-R2-PERF-20260928-001 --run-label screening-1 --gate-receipt results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003/g0-diagnostic-portable-receipt.json --performance-diagnostic --execute-measured
```

실제 graph capture/replay가 확인되지 않으면 UNKNOWN으로 남긴다.

##### 5.4.2.5 Ornith 1.5 9B 1Cat-vLLM — R3 MTP2 [DIAGNOSTIC DONE — FAIL_OUTPUT]

```bash
python3 scripts/run_wbs5_remote.py --track ornith9-onecat --candidate R3 --experiment-id EXP-V100-WBS5-ORNITH9-ONECAT-R3-PERF-20260928-001 --run-label screening-1 --gate-receipt results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-G0-20260928-003/g0-diagnostic-portable-receipt.json --performance-diagnostic --execute-measured
```

resolved n_predict, actual MTP2 acceptance와 output integrity를 runtime evidence로 기록한다.

##### 5.4.2.6 Ornith 1.5 9B 1Cat-vLLM — track result review [DONE — REVIEW_COMPLETE / NO ELIGIBLE RECIPE]

GPU inference 없이 G0 semantic FAIL 및 R0 ~ R3 diagnostic raw를 재검토했다. 상세 기록: [5.4.2.6 result review](WBS-5.4.2.6-result-review.md).

- G0 PASS admission이 없고 R0 ~ R3 모두 Project B `FAIL_OUTPUT`이라 5.5 output-integrity/admission 조건을 충족하지 않는다.
- R1 MBT8192는 R0와 성능이 사실상 동일하고 VRAM만 GPU당 +96 MiB여서 branch를 닫는다.
- R2는 mean decode +17.24% / aggregate +31.47% / wall -13.73% 신호가 있으나 graph capture/replay가 `UNKNOWN`, E2E는 -5.68%, output 길이도 다르고 Project B가 실패했다. graph 효과나 recipe 우위를 주장하지 않는다.
- R3 MTP2 acceptance는 56.67%로 관측됐지만 G0/output failure를 우회할 근거가 아니다.
- 결론: final recipe 후보 없음. 새 graph/MTP/MBT candidate와 추가 inference를 만들지 않는다.

#### 5.4.3 Ornith 1.5 35B-A3B / 1Cat-vLLM [NON-EXECUTABLE PARENT — REVIEW COMPLETE / R0 RETAINED]

2026-09-29 회수된 `screening-1` R0/R1/R2 3회를 개별 report 및 summary/comparison CSV에 등록했다. 세 실행 모두 C2 resident/active=true, queue_only=false, post-health healthy다. 두 요청의 prompt tokens는 각각 126,975/126,976이다.

| WBS | Candidate | 최종 판정 | TTFT | Prefill | Aggregate decode | Batch wall | 출력·graph 증거 |
|---|---|---|---|---|---|---|---|
| 5.4.3.1 | R0 eager MBT4096 | `PASS_C2_ACTIVE` | 109.62 s | 1,456.96 tok/s | 11.48 tok/s | 282.74 s | A/B PASS, 2,557 output tokens; graph `UNKNOWN` (eager). |
| 5.4.3.2 | R1 graph-auto | `FAIL_OUTPUT` | 109.22 s | 1,459.67 tok/s | 23.34 tok/s | 205.02 s | A PASS/B FAIL, 3,384 output tokens; capture/replay `UNKNOWN`. |
| 5.4.3.3 | R2 eager MBT8192 | `PASS_C2_ACTIVE` | 111.34 s | 1,142.84 tok/s | 17.95 tok/s | 298.73 s | A/B PASS, 3,453 output tokens; graph `UNKNOWN` (eager). |

R1의 aggregate decode/wall은 실패한 B가 포함된 배치 관측값이며 mean request decode는 성공한 A만 반영한다. R1의 성능 우위나 graph hit를 주장하지 않는다. R2는 R0보다 prefill이 약 21.6% 낮고 TTFT가 약 1.6% 높다. 출력 길이도 달라 batch wall/aggregate decode의 순위를 recipe 효과로 단정하지 않는다. R0/R2의 PASS는 mechanical output 및 C2 판정이며 task-level semantic audit를 대신하지 않는다. [R0](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-ONECAT-R0-PERF-20260928-001.md), [R1](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260928-001.md), [R2](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-ONECAT-R2-PERF-20260928-001.md) report 참조. 5.4.3.4 review에서 R1은 output failure로, R2는 intended prefill/latency 효과 부재로 branch를 닫고 R0를 5.5 final recipe 대상으로 유지했다.

Frozen candidates:

| Candidate | Frozen configuration / R0 대비 exact delta |
|---|---|
| `R0-BASELINE-EAGER-MBT4096` | TP2 target-only, E5M2 KV, max len 131072, max seqs 2, MBT 4096, util 0.90, `FLASH_ATTN_V100`, `VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0`, eager. |
| `R1-GRAPH-AUTO-MBT4096` | R0에서 **`--enforce-eager` 제거만 변경**. |
| `R2-EAGER-MBT8192` | R0에서 **MBT 4096 -> 8192만 변경**. eager/max seqs/util/KV 유지. |

보존 invariant:
- `ornith-ai/Ornith-1.5-35B-A3B-NVFP4@94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`.
- `/srv/models/ornith-1.5-35b-a3b-nvfp4`.
- TP2 / dtype half / E5M2 KV / target-only / `FLASH_ATTN_V100` / max len 131072 / max seqs 2 / util 0.90.
- baseline original-prefill env 0; R0/R2 eager.

LOCAL_VERIFY_REQUIRED:
- installed runtime identity와 wheel provenance.
- WBS5 runner가 `performance/v1.json` 및 required C2 metrics를 지원하는지.
- R0 exact CLI와 speculative config가 암묵적으로 생성되지 않는지.
- R1 SM70 auto graph policy, compile-cache guard, graph-aware FLASH_ATTN_V100/E5M2/NVFP4 route와 disabling env contamination.
- R2 MBT 8192 scheduler/Mamba alignment static validity와 launcher overwrite 여부.
- R0/R1/R2 exact normalized command diff.

실행 순서/stop:
- R0 -> R1 -> R2.
- static source support와 actual future graph route hit를 구분한다.
- R2는 static validity와 runtime VRAM fit을 구분하며 GPU model-load 전에는 VRAM fit을 확정하지 않는다.
- frozen-delta violation, runtime/artifact mismatch, invalid workload는 hard stop.
- final recipe 승격에는 valid measured performance evidence와 output integrity가 필요하다.


##### 5.4.3.1 Ornith 1.5 35B 1Cat-vLLM — R0 eager MBT4096 [DONE — PASS_C2_ACTIVE]

```bash
python3 scripts/run_wbs5_remote.py --track ornith35-onecat --candidate R0 --experiment-id EXP-V100-WBS5-ORNITH35-ONECAT-R0-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.4.3.2 Ornith 1.5 35B 1Cat-vLLM — R1 graph-auto [DONE — FAIL_OUTPUT]

R0 대비 target eager 제거만 변경한다. 실제 graph route/capture/replay는 runtime evidence로 판정한다.

```bash
python3 scripts/run_wbs5_remote.py --track ornith35-onecat --candidate R1 --experiment-id EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260928-001 --run-label screening-1 --execute-measured
```

##### 5.4.3.3 Ornith 1.5 35B 1Cat-vLLM — R2 MBT8192 [DONE — PASS_C2_ACTIVE]

```bash
python3 scripts/run_wbs5_remote.py --track ornith35-onecat --candidate R2 --experiment-id EXP-V100-WBS5-ORNITH35-ONECAT-R2-PERF-20260928-001 --run-label screening-1 --execute-measured
```

VRAM fit 실패는 setting을 바꾸지 말고 candidate measured result로 보존한다.

##### 5.4.3.4 Ornith 1.5 35B 1Cat-vLLM — track result review [DONE — R0 RETAINED]

GPU inference 없이 R0/R1/R2의 exact frozen delta, 성능, graph evidence, output integrity, C2 state를 비교했다. 상세 기록: [5.4.3.4 result review](WBS-5.4.3.4-result-review.md).

- R1 graph-auto는 Project B `FAIL_OUTPUT`이고 graph capture/replay도 `UNKNOWN`이라 branch를 닫는다. 높은 decode/aggregate 수치를 graph 효과로 사용하지 않는다.
- R2 MBT8192는 R0 대비 TTFT +1.57%, prefill -21.56%, batch wall +5.66%로 intended long-prefill/latency 이득이 없었다. Mean decode +20.34% / aggregate +56.30%는 output tokens +35.04%와 scheduling 비대칭이 섞인 단일 run 관측이라 pure decode win으로 승격하지 않는다.
- R0는 C2 active, queue=false, 두 요청 mechanical output PASS, post-health healthy인 baseline으로 유지한다.
- 결론: `R0-BASELINE-EAGER-MBT4096`만 5.5 final recipe publication 대상으로 유지한다. R1/R2 branch 종료, 새 candidate 및 추가 inference 없음.

### 5.5 final recipe 승격 및 publication

WBS 5에서는 하나의 overall winner나 자동 배포 구성을 선택하지 않는다.
각 model/runtime track에서 실제 검증된 configuration만 recipe로 남긴다.

`VALIDATED_RECIPE` 승격 공통 조건:
- frozen candidate identity와 exact model/runtime/artifact provenance가 일치.
- candidate별 LOCAL_VERIFY_REQUIRED 항목이 measured run 전에 해소되거나 runtime-only uncertainty로 명확히 등록.
- `workloads/performance/v1.json` measured run이 infra/workload-invalid 없이 완료.
- required performance/telemetry/evidence가 보존.
- output integrity가 유효.
- topology/concurrency claim은 해당 measured evidence가 실제로 증명한 범위까지만 기록.
- conditional candidate는 gate가 실제 충족된 경우에만 실행/승격.
- failed/unsupported candidate는 raw verdict를 수정하지 않고 실패 조건 자체를 evidence로 보존.

각 final recipe에는 최소한 다음을 기록한다.
- exact model repository/revision/local artifact identity.
- runtime/version/commit 또는 wheel/image digest.
- weight quant / KV dtype.
- speculative method/depth.
- topology.
- exact launch command 및 relevant environment variables.
- context ceiling / concurrency envelope.
- batch/ubatch 또는 MBT/max-num-seqs.
- graph/eager 설정.
- measured performance.
- peak VRAM 및 telemetry.
- output-integrity verdict.
- known limitations / unsupported combinations.
- 근거 experiment IDs.

WBS 5 final publication 전 7개 track candidate ID/delta/invariant가 frozen source 문서와 다시 일치하는지 검토하고,
measured run을 하지 않은 candidate를 `VALIDATED`로 표기하지 않는다.


## 6. CPU+RAM 전용 dual-resident 128K 서버 + 32K measured request 검증 [DONE]

P520의 CPU+RAM만 사용하는 두 개의 llama.cpp server를 **128K context capacity(`--ctx-size 131072`)로 동시에 기동/resident** 상태로 유지한 뒤, 실제 measured request는 **실사용에 가까운 32K class 요청**을 **한 번에 하나씩 직렬 실행**한다.

CPU lane GPU 격리:
- CPU-only Docker에는 GPU device를 전달하지 않음
- `GGML_CUDA=OFF`
- `--n-gpu-layers 0`
- 두 CPU container의 VRAM allocation = 0B
- GPU0/GPU1: 기존 llama.cpp/vLLM serving은 존재할 수 있으며, CPU benchmark 때문에 기존 GPU serving을 중단할 필요 없음

목적 및 워크로드 성격:
목적은 CPU 단독 최대 TPS를 주장하거나 코딩 벤치마크를 수행하는 것이 아니다. 실제 P520 운용 상태에서 GPU serving과 공존 가능한 범위 안에서 두 MoE GGUF + Q8_0 KV 128K server를 동시에 상주시킬 수 있는지 확인하고, peer CPU server가 idle resident인 상태에서 각 모델의 32K class 장문 문서/리서치형 요청(문서 요약/정리/합성, 웹검색 결과 분석, AI agent/skill 조사 등)에 대한 CPU-only 처리 성능과 메모리 안정성을 fresh evidence로 검증하는 것이다. (본 워크로드는 coding-agent benchmark가 아니며 장문 문서 리서치/합성 워크로드로 정의한다.)

### 6.1 고정 하드웨어 / CPU-only Docker 계약 [DONE]

호스트:
- CPU: Intel Xeon W-2135.
- RAM: DDR4-2400 16GB ×4, 4-channel, 총 64GB.
- GPU0/GPU1: 본 Phase의 CPU inference에는 사용하지 않는다. 별도 llama.cpp/vLLM GPU server의 동시 기동·서빙은 허용되며 기존 V100 GPU serving runtime/container는 변경하지 않고 그대로 유지한다.
- 호스트의 기존 CPU power limit, governor, clock, BIOS, THP, sysctl 등 전력/시스템 정책은 변경하지 않는다.

CPU llama.cpp runtime:
- WBS 6은 기존 V100용 runtime/container와 분리된 **별도의 CPU-only Docker image를 반드시 사용한다**.
- CPU image는 **P520 Xeon W-2135 호스트에서 직접 빌드**한다. 다른 CPU 호스트나 범용 CI에서 만든 native image를 가져와 사용하지 않는다.
- llama.cpp CPU backend는 `GGML_NATIVE=ON`으로 W-2135의 실제 ISA에 맞춰 native compile한다.
- CPU image에는 CUDA backend를 포함하지 않는다: `GGML_CUDA=OFF`.
- native 단일 CPU backend를 사용하며, portable multi-ISA 배포를 위한 `GGML_BACKEND_DL=ON` / `GGML_CPU_ALL_VARIANTS=ON` 조합을 이 Phase의 CPU image에 사용하지 않는다.
- exact llama.cpp commit, compiler/version, CMake build flags, BLAS implementation/version, Docker image tag/digest를 measured run 전에 고정하고 report에 기록한다.
- BLAS를 사용하는 경우 BLAS/OpenMP thread 수는 아래 CPU envelope를 넘지 않게 제한한다.
- CPU-only Docker container에는 GPU device를 전달하지 않는다. runtime에서도 `--n-gpu-layers 0`을 명시해 CPU inference lane과 V100 serving lane을 분리한다.
- CPU build 자체는 W-2135에 최대한 최적화하되, runtime CPU/RAM 사용량은 GPU0/GPU1 serving과의 공존을 위해 6.2의 conservative resource envelope로 제한한다.
- Preflight A/B 확인 결과: pinned preflight baseline (760 prompt / 128 completion)에서 `b10428` (`885c5bbe`)과 `b10775` (`67a17c17`) 비교에서 prompt eval tok/s(35.07 vs 35.18), decode tok/s(10.05 vs 10.02)가 동등 수준으로 확인되어 최신 릴리스인 `p520-cpu-llama:b10775` (`sha256:8ee3818eee9df3690a64177b976692cffd509972cb31c0907f7136b567a4729b`)를 확정했다. (단, 이는 고정된 baseline 1회 검증 결과이며 CPU regression이 전혀 없다고 과도하게 일반화하지 않는다.)
- Dockerfile 빌드 유연성 및 OpenBLAS 지원: `docker/cpu/Dockerfile`은 기본적으로 native AVX2 (`USE_OPENBLAS=0`)를 사용하되, 필요 시 `--build-arg USE_OPENBLAS=1`을 통해 OpenBLAS 빌드(`p520-cpu-llama:b10775-openblas`)를 생성할 수 있도록 매개변수화되었다. 독립적인 preflight A/B 검증(`--openblas-preflight`)을 지원하여 기존 불변 증거를 훼손하지 않고 격리된 디렉터리(`results/raw/WBS6-PREFLIGHT-OPENBLAS/`)에서 짧은 프롬프트 성능 비교를 수행할 수 있다.

공통 llama.cpp 조건:
- CPU-only: `--n-gpu-layers 0`. 이 두 CPU server 자체는 GPU VRAM allocation/offload를 해서는 안 된다.
- 서버 context: `--ctx-size 131072` (128K context capacity 유지).
- concurrency: server별 `--parallel 1`; measured request는 두 CPU server 전체에서 동시에 1개만 허용한다.
- KV: K/V 모두 `Q8_0`.
- attention: `-fa auto`.
- speculative: `ngram-mod`.
- MTP / draft model / composite MTP+NGRAM은 사용하지 않는다.
- 두 CPU server는 서로 다른 port(8082, 8083)로 기동하고, 두 measured request가 끝날 때까지 모두 종료하지 않는다.

### 6.2 coexistence-oriented CPU/RAM resource envelope [DONE]

CPU:
- active CPU inference server는 **물리 코어 4개**를 기본 envelope로 사용한다.
- generation threads: `-t 4`.
- prompt/batch threads: `-tb 4`.
- logical batch: `-b 1024`.
- physical micro-batch: `-ub 256`.
- strict placement: `--cpu-strict 1`.
- polling: `--poll 50`.
- priority elevation은 사용하지 않는다; `--prio` 기본값 0을 유지한다.
- OpenBLAS/OpenMP를 사용하는 경우 `OPENBLAS_NUM_THREADS=4`, `OMP_NUM_THREADS=4`를 기본값으로 사용한다.
- CPU 번호를 `0-3`처럼 가정하지 않는다. 실행 전 `lscpu -e=CPU,CORE,SOCKET,NODE,ONLINE`으로 topology를 기록하고 서로 다른 물리 코어 4개의 logical CPU를 선택한다 (logical CPU IDs 1, 2, 3, 4, each mapped to physical CORE 1, 2, 3, 4).
- 나머지 물리 코어 2개와 SMT sibling 자원은 host OS, telemetry, Docker, GPU llama.cpp/vLLM process의 CPU-side work를 위해 예약한다.
- 두 CPU server는 요청이 직렬이므로 동일한 4-core cpuset을 공유할 수 있다.

RAM / model loading:
- model loading은 `--load-mode mmap`을 기본값으로 사용한다.
- `mlock`, `mmap+mlock`, unlimited memlock은 사용하지 않는다. 두 GGUF weight를 RAM에 강제로 고정해 GPU serving/OS의 host-memory headroom을 잠식하지 않는다.
- prompt cache 재사용은 capacity 측정을 혼동하지 않도록 `--cache-ram 0`, `--no-cache-prompt`를 사용한다.
- `--no-context-shift`를 사용한다.
- HTTP worker는 `--threads-http 1`을 기본값으로 사용한다.
- Web UI는 `--no-webui`로 비활성화한다.
- 본 Phase에서 선언하지 않은 allocator, thread, batch/ubatch, load mode를 첫 measured run 이후 성능을 이유로 조용히 변경하지 않는다.

### 6.3 ngram-mod 계약 [DONE]

llama.cpp의 draft-model-free `ngram-mod` 경로를 활성화한다.

고정값:
- `--spec-type ngram-mod`.
- `--spec-ngram-mod-n-match 24`.
- `--spec-ngram-mod-n-min 48`.
- `--spec-ngram-mod-n-max 64`.

이 Phase는 TARGET lane과의 A/B 성능 비교가 아니라 **NGRAM-on 상태의 dual-resident CPU-only 128K server feasibility**를 검증한다. draft/accepted token이 적거나 0이어도 capacity/correctness PASS 자체를 무효화하지 않으며 실제 counters를 그대로 기록한다.

### 6.4 모델 / artifact 계약 [DONE]

#### 6.4.1 Gemma 4 26B-A4B
- exact file: `gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf`.
- weight quant: `UD-Q6_K_XL`.
- repository: `unsloth/gemma-4-26B-A4B-it-GGUF@c099eb48e663fd284577b04978a94ffccb261841`.
- SHA256: `b01ee10a1423c17f9c4384f1fc569726b8782c5403557ff138ceb9468ca49d6b`.
- KV: `Q8_0`.
- server context: 128K (131,072).
- attention: `-fa auto`.
- speculative: `ngram-mod` 24/48/64.
- MTP: OFF.
- measured agent concurrency: 1.

#### 6.4.2 Ornith 1.5 35B-A3B
- exact file: `Ornith-1.5-35B-Q4_K_M.gguf`.
- weight quant: `Q4_K_M`.
- repository: `ornith-ai/Ornith-1.5-35B-A3B-GGUF@12393612fd4f730ff5aadc23e9b8f9648aa49ceb`.
- SHA256: `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`.
- KV: `Q8_0`.
- server context: 128K (131,072).
- attention: `-fa auto`.
- speculative: `ngram-mod` 24/48/64.
- MTP: OFF.
- measured agent concurrency: 1.

### 6.5 dual-resident + coexistence startup gate [DONE — PASS_STARTUP_GATE]

두 CPU server(`p520-cpu-gemma` 포트 8082, `p520-cpu-ornith` 포트 8083)를 128K context capacity로 기동하여 검증 완료:
- Gemma CPU server healthy (`/health` 200 OK).
- Ornith CPU server healthy (`/health` 200 OK).
- 두 CPU process가 동시에 resident 상태 (Gemma RSS 1.631 GiB, Ornith RSS 17.47 GiB).
- 두 CPU server 자체의 GPU offload/VRAM allocation 0B 확인 (GPU0 0.0 MiB, GPU1 0.0 MiB, GPU compute apps 0개).
- startup snapshot 당시 MemAvailable은 약 31.59 GiB (Total 62.56 GiB).
- 판정: **`PASS_STARTUP_GATE`** (`results/raw/WBS6-STARTUP-GATE/startup_gate.json`).
- **메모리 해석 엄밀화 및 한계 명시**:
  - 기존 startup gate 증거에서 확인된 사실은 "두 CPU 서버의 동시 기동, `/health` 정상, GPU 격리(VRAM 0B)"까지다.
  - raw snapshot 당시 Swap 사용량은 약 4.00 GiB (SwapTotal 4,194,300 kB, SwapFree 528 kB)로 기사용 중이었으며, startup 전후의 `pswpin`, `pswpout`, `pgmajfault`, SwapUsed delta는 계측되지 않았으므로 "swap thrash 없음"은 입증된 사실이 아니다.
  - 또한 `--load-mode mmap` 특성상 startup 직후 MemAvailable 31.59 GiB는 42GB 모델 가중치가 physical RAM에 완전히 fault-in된 후의 guaranteed headroom이 아니다.
  - 실제 가중치 fault-in에 따른 메모리 압박, major fault, swap thrash 여부는 6.6의 32K measured inference 실행 중에 강화된 telemetry로 정밀 측정한다.

### 6.6 128K 서버 상주 조건 하 32K 직렬 measured request [DONE]

서버는 128K context(`--ctx-size 131072`)로 dual-resident 상태를 유지하며, 실제 measured request는 실사용 리서치/문서 합성형 32K request(`prompt tokens + output reserve <= 32768`)를 직렬로 1회씩 수행하여 완료했다.

- 워크로드: `workloads/capacity/v1-32k.json` (live serving model tokenizer 기준 32K budget 준수; Gemma prompt 31,742 tokens, Ornith prompt 31,743 tokens, output reserve 1,024개 evidence 명시). 코딩 벤치마크가 아닌 장문 문서 요약/리서치 합성 워크로드.
- Gemma 4 26B-A4B: `EXP-P520-CPU-GEMMA4-26B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001`
  - 판정: **`PASS`** (Harness PASS, Output PASS, Server Health PASS).
  - TTFT: 4,927.28s (~82.1분), Prefill 속도: 6.44 tok/s (31,742 tokens).
  - Decode 속도: 2.72 tok/s (716 completion tokens), Batch Wall Time: 5,189.72s (~86.5분).
  - Peak VRAM: GPU0 0 MiB / GPU1 0 MiB (VRAM 0B 완전 격리 확인).
  - Peer Ornith server: 128K idle resident 유지 (/health 200 OK 확인; 단, smaps_rollup 수집 실패로 6.6 개별 프로세스 RSS/PSS는 0으로 기록되었으며, 공존 건전성은 시스템 전체 MemAvailable 및 헬스체크로 입증됨).
  - SwapUsed delta: +14.5 MiB, pswpin/pswpout delta: +1,704 / +4,466, pgmajfault delta: +8,844 (86분 실행 동안 경미한 swap 증분 외 심각한 지속적 swap thrashing은 관찰되지 않음).
  - MemAvailable min: ~41.4 GiB (Host Total 62.56 GiB 중 충분한 물리 헤드룸 유지).
  - Post-health: both healthy (`true`).
- Ornith 1.5 35B-A3B: `EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001`
  - 판정: **`PASS`** (Harness PASS, Output PASS, Server Health PASS).
  - TTFT: 4,160.26s (~69.3분), Prefill 속도: 7.63 tok/s (31,743 tokens).
  - Decode 속도: 3.15 tok/s (892 completion tokens), Batch Wall Time: 4,443.18s (~74.1분).
  - Peak VRAM: GPU0 0 MiB / GPU1 0 MiB (VRAM 0B 완전 격리 확인).
  - Peer Gemma server: 128K idle resident 유지 (/health 200 OK 확인; smaps_rollup 개별 프로세스 RSS/PSS는 0 기록 한계 명시).
  - SwapUsed delta: +12.4 MiB, pswpin/pswpout delta: +113 / +2,101, pgmajfault delta: +1,433 (74분 실행 동안 경미한 swap 증분 외 지속적 swap thrashing은 관찰되지 않음).
  - MemAvailable min: ~41.2 GiB.
  - Post-health: both healthy (`true`).
- Checkpoints A~G 전 구간 정상 계측 완료:
  - Checkpoint A (`baseline_before_startup`) -> B (`startup_healthy`) -> C (`gemma_pre`) -> D (`gemma_post`) -> E (`ornith_pre`) -> F (`ornith_post`) -> G (`final_post_health`).
- 사후 정리: 두 컨테이너 `p520-cpu-gemma`, `p520-cpu-ornith` 모두 정상 정지 및 cleanup 완료.

### 6.7 판정 기준 및 최종 결과 [DONE]

모델별 **`PASS_CPU_128K_SERVER_32K_REQUEST_DUAL_RESIDENT`** 평가 결과:
1. **Gemma 4 26B-A4B**: **`PASS_CPU_128K_SERVER_32K_REQUEST_DUAL_RESIDENT`**
   - UD-Q6_K_XL / KV Q8_0 / CPU-only / 4-core conservative envelope / NGRAM-MOD 24/48/64 / Server 128K / Request 32K / peer Ornith resident.
   - 32K 장문 문서 리서치/합성 요청 완수, 출력 정상(`finish_reason=stop`), OOM/크래시 0, 사후 헬스체크 정상, Swap delta +14.5 MiB (지속적 swap thrashing 미관찰), GPU VRAM 0B.
2. **Ornith 1.5 35B-A3B**: **`PASS_CPU_128K_SERVER_32K_REQUEST_DUAL_RESIDENT`**
   - Q4_K_M / KV Q8_0 / CPU-only / 4-core conservative envelope / NGRAM-MOD 24/48/64 / Server 128K / Request 32K / peer Gemma resident.
   - 32K 장문 문서 리서치/합성 요청 완수, 출력 정상(`finish_reason=stop`), OOM/크래시 0, 사후 헬스체크 정상, Swap delta +12.4 MiB (지속적 swap thrashing 미관찰), GPU VRAM 0B.

결론: P520 호스트에서 64GB RAM과 CPU 4코어만으로 두 거대 MoE 모델(가중치 합산 약 45GB)을 128K context capacity로 동시 상주시키면서 32K 실사용급 문서 리서치 요청을 오류 및 지속적 스왑 스래싱 없이 처리했고, CPU inference lane의 GPU VRAM 사용량이 0 MiB임을 확인했다. WBS 6.1~6.7의 dual-resident feasibility/correctness 검증은 완료되었으며, 후속 성능 최적화는 6.8에서 `-b/-ub`만 제한적으로 조정해 검증한다.


### 6.8 CPU prefill batch / ubatch 최소 튜닝 [DONE]

정정 사항:
- 2026-09-27 최초 6.8.1 실행 `EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-2K-20260927-001~004`는 experiment ID와 문서상 "2K"로 표기되었지만, raw `usage.prompt_tokens` 및 `metrics.json`의 실제 prompt는 네 케이스 모두 **922 tokens**였다.
- 해당 raw evidence는 삭제/수정하지 않고 **legacy short-prompt (~1K) diagnostic**으로 불변 보존한다.
- 따라서 이 922-token 결과가 증명하는 범위는 "약 1K short prompt에서 `-b/-ub` 확대 효과가 관찰되지 않았다"까지다.
- 이전 문서의 "장문 prefill에 유의미한 영향이 없다", "WBS 6.6의 7.63/6.44 tok/s가 prefill ceiling으로 확정된다"는 결론은 증거 범위를 초과하므로 **철회**한다.

고정 조건:
- Ornith 1.5 35B-A3B `Q4_K_M`.
- llama.cpp `b10775` / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`.
- `-t 4 -tb 4`, cpuset logical CPU IDs `1,2,3,4`.
- server context `--ctx-size 131072`, KV `Q8_0`, `-fa auto`.
- `GGML_NATIVE=ON`, `GGML_CUDA=OFF`, `GGML_BLAS=OFF`, `--n-gpu-layers 0`.
- `ngram-mod` 24/48/64, `--load-mode mmap`, `--cache-ram 0`, `--no-cache-prompt`, `--no-context-shift`.
- 모델/quant/KV/threads/affinity/context/speculative 설정은 고정하고 **오직 `-b/-ub`만 변경**한다.

#### 6.8.1 true-2K Ornith screening — 신규 4회 [READY]

이번에는 "대략 2K 문자열"이 아니라 **live llama.cpp tokenizer + 실제 chat template 적용 후 prompt token 수**를 실행 전에 검증한다.

Acceptance:
- measured request의 실제 `prompt_tokens`가 **2,000~2,048** 범위에 있어야 한다.
- tokenizer receipt와 measured response의 `usage.prompt_tokens`가 정확히 일치해야 한다.
- 네 케이스 모두 동일한 raw prompt SHA256 및 동일 prompt token count를 사용해야 한다.
- 위 조건을 만족하지 않으면 measured screening 결과로 인정하지 않고 실패 처리한다.

신규 experiment IDs:
- Case A: `EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-2K-20260927-005` — `-b 1024 -ub 256`.
- Case B: `...-006` — `-b 2048 -ub 512`.
- Case C: `...-007` — `-b 4096 -ub 512`.
- Case D: `...-008` — `-b 4096 -ub 1024`.

새 summary/winner evidence:
- `results/raw/WBS68-TRUE2K-SCREENING-SUMMARY.json`.
- `results/raw/WBS68-TRUE2K-WINNER.json`.
- 기존 `WBS68-SCREENING-SUMMARY.json`, `WBS68-WINNER.json`은 922-token legacy evidence로 그대로 보존한다.

Winner policy:
- prompt eval tok/s 최고값 대비 **2% 이내는 동률**로 취급한다.
- 동률 그룹 안에서는 더 작은 `b`, 그다음 더 작은 `ub`를 우선한다.
- 이 ±2% 규칙을 문서뿐 아니라 runner `select_winner()`에도 동일하게 구현한다.

#### 6.8.2 / 6.8.3 32K 후속 검증 조건

- true-2K screening에서도 Case A(`1024/256`)가 선택되거나 네 조건이 ±2% 이내로 사실상 동률이면, 기존 WBS 6.6과 동일한 baseline을 32K로 재실행하지 않고 6.8을 종료한다.
- true-2K에서 **baseline 대비 2%를 초과하는 non-baseline winner**가 나올 때만 Ornith 32K 검증 후보로 승격한다.
- 32K 실행은 자동으로 이어서 수행하지 않는다. 기존 `--run-ornith-32k` / `--run-gemma-32k`는 명시적 실행 플래그로 유지한다.
- Ornith 32K에서 실제 개선이 확인된 경우에만 동일 `b/ub`의 Gemma 32K 적용 검증을 의미 있는 후속 단계로 본다.

현재 상태:
- WBS 6.1~6.7: 기존 PASS 유지.
- 922-token legacy screening: 완료 및 보존.
- **true-2K 4-case screening: [DONE]**
  - `results/raw/WBS68-TRUE2K-SCREENING-SUMMARY.json`, `WBS68-TRUE2K-WINNER.json`
  - Case A (1024/256): 2,000 tok, prompt 31.72 tok/s, TTFT 63.05s
  - Case B (2048/512): 2,000 tok, prompt 31.32 tok/s, TTFT 63.87s
  - Case C (4096/512): 2,000 tok, prompt 31.34 tok/s, TTFT 63.81s
  - Case D (4096/1024): 2,000 tok, prompt 30.64 tok/s, TTFT 65.27s
  - 판정: Case A, B, C가 ±2% 이내 동률(31.72 vs 31.32 vs 31.34 tok/s). ±2% 동률 정책에 따라 가장 작은 설정인 **Case A (`1024/256`)가 Winner**로 선정됨.
  - baseline 대비 2%를 초과하는 non-baseline winner가 부재하므로, 사전 합의된 정책에 따라 32K 재실행을 생략하고 WBS 6.8을 종결했다.
  - **해석 범위**: 이 결과는 정확히 2,000-token prompt에서만 `b/ub` 확대 효과가 관찰되지 않았다는 뜻이다. 이후 WBS 6.9의 true-4K `cache_n=0` setup evidence에서는 큰 `b/ub`, 특히 `ub=1024`가 더 높은 prompt throughput을 보였으므로, 2K 결과를 4K 이상 장문 prompt에 일반화하지 않는다.
- **WBS 6.1~6.8 [DONE]**.



### 6.9 Combined optimized CPU serving stack — true-4K A/B/C/D [DONE — OpenVINO CLOSED / OpenBLAS+LTO COMPLETED]

목적:
- WBS 6.8에서 `-b/-ub` 확대만으로는 2K prefill 개선이 없음을 확인했다.
- 이번 단계는 weight/KV quantization을 바꾸지 않고, serving-side 최적화들을 적용한 상태에서 true-4K prompt의 실사용형 성능을 측정하고 최적 `-b/-ub` 조합을 확정한다.
- 최초 시도된 OpenVINO 결합 스택은 런타임 구조 비호환으로 실패 종결되었으며, 사용자 승인에 따라 크래시된 OpenVINO를 배제한 OpenBLAS + LTO + Flash Attention + Prompt Cache 최적화 스택으로 True-4K A/B/C/D 선별을 완수했다.

제외/고정:
- KV quant 변경 제외: K/V 모두 기존 `Q8_0`.
- weight quant 변경 제외: Ornith 1.5 35B-A3B `Q4_K_M` 그대로.
- CPU coexistence envelope 유지: `-t 4 -tb 4`, Docker cpuset logical CPU IDs `1,2,3,4`.
- GPU offload 없음: `--n-gpu-layers 0`, CUDA build OFF, GPU VRAM 0B.
- server capacity: `--ctx-size 131072`.
- speculative: `ngram-mod` 24/48/64.

#### 6.9.1 OpenVINO optimized image [DONE]
- Dockerfile: `docker/cpu-optimized/Dockerfile`.
- Pinned commit: `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`.
- Cmake 옵션: `GGML_BACKEND_DL=ON`, `GGML_CPU_ALL_VARIANTS=ON`, `GGML_NATIVE=OFF` (DL backend 호환), `GGML_LTO=ON`, `GGML_CUDA=OFF`, `GGML_BLAS=ON` (`GGML_BLAS_VENDOR=OpenBLAS`), `GGML_OPENVINO=ON`.
- OpenVINO runtime: 2026.3.1 (`2026.3.1.22476.56d9685302d`).
- 빌드 결과: `p520-cpu-llama-opt:b10775` (`p520-cpu-llama-opt@sha256:fb36832f7cd61afc59a2e753e0b84ab52d4d44673e60938107cdb7c6a31d3c0f`).

#### 6.9.2 OpenVINO preflight device verification [PASS]
- 증거: `results/raw/WBS69-OPT4K-PREFLIGHT.json`.
- 디바이스 인식:
  - `BLAS: OpenBLAS (0 MiB, 0 MiB free)`
  - `OPENVINO0: OpenVINO Runtime (62558 MiB, 62558 MiB free)`
- OpenVINO 런타임 라이브러리 및 디바이스 가시성 통과 확인.

#### 6.9.3 OpenVINO 런타임 실행 및 장애 원인 분석 [FAIL / INCOMPATIBLE]
- Case A: `EXP-P520-CPU-ORN15-35B-OPTSTACK-C1-4K-20260927-001` (`-b 1024 -ub 256`).
- 서버 기동 및 `/health` 통과 (`{"status":"ok"}`).
- 그러나 첫 번째 unmeasured 4K compile warmup 요청 실행 도중 `HTTP Error 500: Internal Server Error` (`llama_decode: failed to decode, ret = -3`) 발생.
- 상세 실패 증거: `results/raw/EXP-P520-CPU-ORN15-35B-OPTSTACK-C1-4K-20260927-001/runtime/backend-error.json`.

**치명적 비호환 원인 (심층 진단)**:
1. **`ScatterBase` Rank Mismatch (`set_rows.cpp`)**:
   - Ornith 1.5 35B 모델은 2D KV Cache 텐서 `cache_k_l3` `[131072, 512]`를 할당한다.
   - 반면 llama.cpp의 `ggml-openvino` 연산 변환기(`translate_set_rows`, `openvino/op/set_rows.cpp`)는 KV 캐시 대상을 무조건 4D로 간주하고 updates 텐서를 4D `[1, 1, n, 512]` 및 axis 2로 `ScatterUpdate` 노드를 생성한다.
   - OpenVINO Core 검증(`src/core/src/op/util/scatter_base.cpp:52`)에서 `updates_shape.rank() == indices_shape.rank() + data_shape.rank() - 1` 규칙을 검사하며, `rank(data)=2, rank(indices)=1, rank(updates)=4` 불일치로 예외가 발생하여 그래프 연산이 즉각 중단된다 (`graph_compute: ggml_backend_sched_graph_compute_async failed with error -1`).
2. **Recurrent/Conv State Dynamic Dimension 추론 불가**:
   - Ornith 1.5 하이브리드 아키텍처의 SSM/Conv 상태 노드(`conv_states_reshaped-0`, `state_predelta-0`)에 대해 OpenVINO 백엔드가 동적 차원을 결정하지 못해 웜업 시퀀스 shape으로 정적 고정되며, 후속 토큰 처리 시 `Can't set the input tensor with index: 3, because the model input (shape=[1,1,2,2048]) and the tensor (shape=(1.1.11.2048)) are incompatible` 텐서 형태 비호환 예외가 발생한다.

#### 6.9.4 OpenVINO 종결 및 정책 준수
- 프로젝트 불변 정책에 따라 native-GGML fallback을 조용히 수용하지 않고 즉시 fail-fast 종료했다.
- 하드웨어 읽기 전용 원칙 준수 (GPU 클럭/전력/persistence mode 변경 없음).
- Ornith 1.5 35B-A3B 하이브리드 아키텍처는 현재 llama.cpp b10775의 OpenVINO 백엔드와 구조적으로 비호환됨이 입증되었으며, OpenVINO 경로는 **`CLOSED — FAIL / INCOMPATIBLE`**로 종결하고 증거를 영구 보존한다.

#### 6.9.5 OpenBLAS + LTO True-4K Screening (Cases A~D) [DONE]
사용자 승인 하에 OpenVINO를 제외하고, 유효한 최적화 스택(OpenBLAS + LTO + Flash Attention + Prompt Cache)을 적용한 `p520-cpu-llama-opt:b10775-blas` 이미지(`docker/cpu-optimized/Dockerfile.blas`)를 통해 최종 True-4K A/B/C/D 스크리닝을 완수했다.

- **Preflight**: `results/raw/WBS69-OPTBLAS-4K-PREFLIGHT.json` (OpenBLAS device 인식 통과). Docker CPU-only / `--n-gpu-layers 0` 계약을 유지했으며, WBS 6.9 자체에는 별도의 sampled VRAM peak metric을 추가하지 않았다.
- **최종 matrix 계약 및 검증 기준**:
  - 최종 accepted matrix는 `005~008` 4개다. 네 케이스 모두 정확히 **4,071 total prompt tokens** 및 동일 prompt hash(`2378b3662af3...`), 동일 prefix hash(`01f0a0cb5cf8...`)를 사용했다.
  - Prefix cache 검증: prefix 실측 1,623 tokens, 모든 최종 케이스에서 `cache_n >= 512` 통과.
  - 단, 실제 새로 평가된 prompt는 `prompt_n = total prompt_tokens - cache_n`이므로 A~D에서 서로 달랐다. 따라서 measured `prompt_per_second` 차이를 순수한 `b/ub` 효과로 단독 귀속하지 않는다.
  - Coexistence envelope: 4 physical CPU cores (`cpuset 1,2,3,4`), `-t 4 -tb 4`, CPU-only serving.
- **최종 accepted measured 결과**:

  | Case | Experiment ID | `-b` | `-ub` | Total Prompt | `cache_n` | Evaluated `prompt_n` | Prompt Eval TPS | TTFT (s) | Decode TPS | Wall (s) |
  |:---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
  | A | `...-005` | 1024 | 256 | 4,071 | 1,363 | 2,708 | 18.48 | 146.57 | 6.64 | 185.03 |
  | B | `...-006` | 2048 | 512 | 4,071 | 1,107 | 2,964 | 21.62 | 137.11 | 5.41 | 184.30 |
  | C | `...-007` | 4096 | 512 | 4,071 | 1,107 | 2,964 | 22.27 | **133.12** | 5.38 | 180.58 |
  | D | `...-008` | 4096 | 1024 | 4,071 | 595 | 3,476 | **24.69** | 140.78 | 6.49 | **180.10** |

- **동일 4K / cache_n=0 setup diagnostic**:
  - 각 최종 케이스의 `setup-compile-warmup.json`에는 동일한 **4,086 prompt tokens / cache_n=0 / prompt_n=4,086** evidence가 있다. 이는 unmeasured setup request이므로 정식 measured matrix와 구분하지만, A~D의 `b/ub` 효과를 cache reuse 차이 없이 비교하는 보조 근거로 사용한다.

  | Case | `-b/-ub` | Uncached 4K Prompt TPS |
  |:---:|:---:|---:|
  | A | 1024/256 | 19.91 |
  | B | 2048/512 | 23.55 |
  | C | 4096/512 | 23.74 |
  | D | 4096/1024 | **26.02** |

  - 이 동일 uncached 4K diagnostic에서 D는 A보다 약 **30.7%** 높은 prompt throughput을 보였다.
  - B→C(`ub=512` 고정, `b=2048→4096`) 차이는 약 0.8%로 작았고, C→D(`b=4096` 고정, `ub=512→1024`)는 약 9.6% 상승했다. 현재 evidence에서는 4K에서 `ub` 확대의 영향이 더 뚜렷하다.
  - 반대로 WBS 6.8 true-2K에서는 A/B/C가 ±2% 동률이고 D가 느렸으므로, **최적 `b/ub`는 prompt/context 길이에 따라 달라질 수 있다.**

- **Winner 및 serving 해석**:
  - 사전 정의된 selection metric인 measured Prompt Eval TPS 기준 winner는 **Case D (`4096/1024`)**이며 `WBS69-OPTBLAS-4K-WINNER.json`의 판정은 그대로 유효하다.
  - 다만 measured cache reuse 양이 다르므로 **18.48→24.69(+33.6%)를 순수한 b/ub 개선율로 표현하지 않는다**. 이는 최종 cached-serving scenario에서 관찰된 prompt-eval TPS 차이다.
  - 실제 TTFT 최저는 **Case C (133.12s)**이고, total wall은 C 180.58s / D 180.10s로 약 0.3% 차이여서 사실상 비슷하다. 따라서 production serving에서는 D를 throughput-oriented recipe, C를 TTFT-oriented recipe로 구분한다.
- **pre-final attempt 기록**:
  - `...-OPTBLAS-...-001`: 이전 1,023-token prefix 계약에서 measured request까지 완료(4,083 total prompt, cache_n 763, 19.63 tok/s)했으나 최종 005~008 matrix와 prompt/prefix contract가 달라 superseded diagnostic으로 보존한다.
  - `...-OPTBLAS-...-002`: measured inference response를 얻은 뒤 `cache_n=507 < 512` acceptance gate에서 실패했다. 따라서 “4회”는 **최종 accepted comparison matrix 005~008의 크기**를 뜻하며, WBS 6.9 과정에서 발생한 모든 물리 inference 실행 횟수를 뜻하지 않는다.
- 상세 실행 보고서: [docs/WBS-6.9-execution-report.md](WBS-6.9-execution-report.md)
- WBS 6.9 전체 [DONE].


### 6.10 Optimized CPU true-32K validation [CLOSED — C32 PASS / D32 NOT RUN]

목적:
- WBS 6.9 true-4K에서 상위 후보로 남은 Case C(`b4096/ub512`)와 Case D(`b4096/ub1024`)가 true-32K에서도 실질적인 CPU prefill 가속을 제공하는지 확인한다.
- 4K cached matrix의 `cache_n` 차이를 제거하기 위해 32K measured request에서는 prompt cache를 완전히 비활성화한다.
- 최초 계획은 C32/D32 각 1회 비교였으나, C32가 장시간 측정 후 기존 32K observed result를 상회하지 못해 사용자 결정으로 D32는 실행하지 않았다. 따라서 이 단계는 완전한 C-vs-D 비교가 아니라 C32 validation 결과로 종결한다.

공통 고정:
- model: Ornith 1.5 35B-A3B `Q4_K_M`.
- KV: `Q8_0`.
- runtime: llama.cpp b10775 / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`.
- image: `p520-cpu-llama-opt:b10775-blas` (`sha256:5f4f7d9d7bc5c0539eef15d88c43051f23c3bc696acbbd7ab96da041eb29e3e9`).
- OpenBLAS + LTO + `GGML_CPU_ALL_VARIANTS=ON`, `-fa on`, `--repack`.
- `-t 4 -tb 4`, cpuset logical CPU IDs `1,2,3,4`.
- `--ctx-size 131072 --parallel 1`.
- `--load-mode mmap --lazy-mode off --warmup`.
- `--cpu-strict 1 --cpu-strict-batch 1 --poll 50 --poll-batch 1`.
- ngram-mod 24/48/64.
- `--n-gpu-layers 0`.
- measured cache policy: `--cache-ram 0 --no-cache-prompt`.

실행 기록:
- 초기 C32 attempt `EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-001`:
  - harness required identity(`runtime_revision`, `launch_command`, `chat_template`, `tool_parser`, `thinking`) 누락으로 measured request 제출 전 validation 단계에서 종료.
  - partial preparation evidence만 immutable raw로 보존.
  - corrected runner는 container/raw 생성 전에 `h.validate(config)`를 수행한다.
- corrected C32 `EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-003`: **PASS**.
  - `-b 4096 -ub 512`.
  - exact prompt tokens: **31,743**.
  - raw prompt SHA256: `75f3de663d9196805b399c70da3f1dd048629c9fca71b7337f0893b6b4527147`.
  - Prefill: **7.3849 tok/s**.
  - TTFT: **4,298.53s** (~71.64분).
  - Decode: **3.1405 tok/s**.
  - Batch wall: **4,553.92s** (~75.90분).
  - sampled Peak VRAM: GPU0/GPU1 **0 MiB**.
  - output/mechanical verdict PASS, post-health 정상.
- runtime caveat:
  - `--prio 1` / `--prio-batch 1`은 container에서 `Permission denied` / `Operation not permitted`가 발생하여 실제 priority 상승은 적용되지 않았다.

기존 WBS 6.6 Ornith 32K observed result와의 참고 비교:
- WBS 6.6: 31,743 prompt tokens, Prefill 7.6303 tok/s, TTFT 4,160.26s, Decode 3.1495 tok/s, Wall 4,443.18s.
- WBS 6.10 C32: Prefill **-3.22%**, TTFT **+3.32%**, Decode **-0.28%**, Wall **+2.49%**.
- 단, WBS 6.6은 native CPU stack + dual-resident 조건이고 WBS 6.10은 combined optimized stack + single-server 조건이므로 동일 controlled A/B가 아니다. 차이를 OpenBLAS, LTO, b/ub 등 특정 단일 설정 효과로 귀속하지 않는다.
- 직접 확인된 결론은 **이번 combined optimized C32 configuration이 기존 32K observed result를 상회하지 못했다**는 것이다.

Long-context runtime progression:
- 누적 prompt throughput은 4K 23.32 → 8K 18.39 → 12K 14.61 → 16K 12.05 → 20K 10.28 → 24K 8.99 → 28K 7.99 → final 약 7.39 tok/s로 감소했다.
- 따라서 WBS 6.9의 4K b/ub 이득을 32K 전체 prefill에 직접 일반화할 수 없다.

D32:
- `EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-004`: **NOT RUN — INTENTIONALLY STOPPED**.
- C32 한 건이 약 76분 소요됐음에도 기존 32K observed result를 상회하지 못해 추가 장시간 D32 측정의 기대 가치가 낮다고 판단하여 사용자 결정으로 중단했다.
- D32가 실행되지 않았으므로 `ub=1024`의 true-32K 성능은 판정하지 않는다.
- `results/raw/WBS610-OPTBLAS-32K-C-VS-D.json`은 두 case 완료를 전제로 하므로 생성되지 않은 것이 정상이다.

상세 실행 보고서:
- [docs/WBS-6.10-execution-report.md](WBS-6.10-execution-report.md)

최종 상태:
- **CLOSED — C32 PASS / C32 DID NOT OUTPERFORM PRIOR 32K OBSERVATION / D32 NOT RUN**.

## 7. Qwen3.8 llama.cpp post-WBS5 SM70 optimization validation [PLANNED]

목적:
- WBS 5의 Qwen3.8 llama.cpp 결과와 final candidate는 historical/frozen evidence로 그대로 보존한다.
- 후속 WBS 7에서는 새로 확인된 두 최적화만 독립적으로 검증한다.
  1. GGUF에 이미 포함된 Qwen3.8 native MTP head를 llama.cpp `draft-mtp`로 활성화.
  2. SM70 Flash Attention GQA×2 patch를 현재 pinned llama.cpp b10775에 forward-port.
- 두 후보 모두 **C2 / 128K per slot / 2 slots** 최종 serving 조건에서 각각 **measured execution 1회만** 수행한다.
- WBS 5 R2를 control로 재사용하며 baseline을 다시 실행하지 않는다.
- MTP와 GQA×2를 동시에 적용한 combined candidate는 WBS 7 범위에서 만들지 않는다.

### 7.0 Frozen baseline / provenance / no-inference preflight [PLANNED]

Authoritative control:
- Candidate: WBS 5 `Q38-LLAMA-WBS5-R2-TARGET-UB256`.
- Experiment: `EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001`.
- Verdict: `PASS_C2_ACTIVE`.
- Model: `/srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf`.
- Model SHA256: `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`.
- Runtime: llama.cpp b10775 / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`.
- OCI: `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`.
- Topology: project label `tp2-shared`; actual llama.cpp launch is `--split-mode layer --tensor-split 1,1` and must not be described as llama.cpp tensor-parallel mode.
- Context/concurrency: `--ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072`.
- Batch: `--batch-size 512 --ubatch-size 256`.
- KV: K/V `q8_0`.
- Flash Attention: on.
- Common runtime flags: `-ngl all --jinja --reasoning off --metrics --slots --no-warmup`.
- R2 speculative mode: `--spec-type none`.

R2 measured reference:
- TTFT: 679.053 s.
- Prefill: 264.11 tok/s.
- Mean request decode: 5.593 tok/s.
- Aggregate decode: 4.514 tok/s.
- End-to-end output: 3.457 tok/s.
- Batch wall: 1337.27 s.
- Peak VRAM: GPU0 13,447 MiB / GPU1 14,533 MiB.
- Both measured requests and post-health passed.

External provenance:
- Qwen3.8 native-MTP serving reference: `jackinthebox52/qwen38-v100-serve@7080181335f660cbb801c9ccb68e1a74697b5604`.
  - This is supporting evidence only; WBS 7 continues to use the project's pinned b10775 runtime.
  - The external reference documents an embedded `blk.64` MTP module and uses stock llama.cpp for MTP.
- SM70 GQA×2 reference: `123123213weqw/dual-v100-llama.cpp@5edfd28c56ef10d21f32fdcfcb12361bb6db1c55`.
  - Source patch: `patches/sm70-tuning.patch`, Git blob `7074ba8d0a48142823f7f4befff271ff1879633d`.
  - WBS 7 imports only the GQA×2 Flash Attention change controlled by `GGML_CUDA_FATTN_VEC_GQA_HEADS=2`. Other patches/tuning from that repository are out of scope.

7.0 is a **no-generation preflight** and does not count as either measured test:
- Do not submit a short, 128K, warmup, or benchmark generation request.
- Confirm from the exact GGUF/server-load evidence that the current artifact contains the embedded `blk.64` / `blk.64.nextn.*` MTP tensors that target-only execution currently ignores.
- Confirm the pinned b10775 binary/source accepts `--spec-type draft-mtp` and `--spec-draft-n-max 1`.
- Forward-port the GQA×2 change onto exactly b10775 and preserve a reviewable patch/diff.
- Record base commit, external source commit/blob, resulting patch SHA256, build command, build flags and resulting binary/image identity.
- Reject unrelated changes to GDN, ARGMAX, MTP subvocabulary, tensor-split behavior, KV type, batch/ubatch, graph policy, clocks or host settings.
- No C1 128K measured screening is scheduled. The first and only measured execution for each candidate is C2 128K × 2 slots.

### 7.1 Qwen3.8 native MTP1 — C2 128K × 2 slots [PLANNED — EXACTLY 1 MEASURED RUN]

Candidate ID:
- `Q38-LLAMA-WBS7-MTP1-C2-128K`.

Planned experiment:
- `EXP-V100-WBS7-QWEN-LLAMA-MTP1-C2-128K-20260929-001`.

Exact delta from frozen WBS 5 R2:
- Replace `--spec-type none` with `--spec-type draft-mtp --spec-draft-n-max 1`.
- No companion draft GGUF.
- All other model/runtime/topology/context/batch/KV/FA/workload settings remain byte-for-byte or semantically identical to R2.

Why MTP1:
- The goal of this single run is first to establish native-MTP feasibility under the project's constrained 2× V100 16GB, C2, 128K-per-slot memory envelope.
- External Qwen3.8 deployments use deeper draft lengths, but they are not evidence that MTP3/MTP7 fits this exact 2×16GB C2 configuration.
- WBS 7 therefore does not claim MTP1 is the throughput-optimal draft depth.

Required evidence:
- server/load logs proving the embedded MTP path is actually used rather than ignored;
- C2 residency and active-overlap evidence;
- both 128K requests' output/mechanical integrity;
- post-health;
- TTFT, prefill, per-request decode, mean request decode, aggregate decode, end-to-end throughput and batch wall;
- GPU0/GPU1 lifecycle and measured-window peak VRAM;
- speculative counters: draft tokens, accepted tokens, draft count and acceptance ratio.

Pass/stop policy:
- `PASS_C2_ACTIVE` requires both 128K slots resident/active, both outputs valid, post-health healthy, and non-zero native-MTP draft activity.
- OOM/startup/capacity/crash/output failure is a valid terminal result for this candidate; do not reduce context, concurrency, KV precision, batch/ubatch, or MTP depth and retry under the same WBS 7 candidate.
- Only one measured execution is authorized. Harness-invalid/no-request-admitted infrastructure failures must be preserved as inconclusive evidence and require explicit user authorization before any rerun.
- No automatic MTP2/MTP3/MTP7, MTP+NGRAM or MTP+GQA×2 follow-up is authorized.

### 7.2 SM70 GQA×2 + Q8_0 KV — C2 128K × 2 slots [PLANNED — EXACTLY 1 MEASURED RUN]

Candidate ID:
- `Q38-LLAMA-WBS7-SM70-GQA2-Q80-C2-128K`.

Planned experiment:
- `EXP-V100-WBS7-QWEN-LLAMA-GQA2-Q80-C2-128K-20260929-001`.

Exact delta from frozen WBS 5 R2:
- Keep TARGET mode: `--spec-type none`.
- Keep K/V `q8_0`.
- Keep the exact R2 model, workload, layer split, context, parallelism, unified KV, batch 512, ubatch 256, Flash Attention and serving flags.
- Change only the llama.cpp binary/build by forward-porting the isolated SM70 GQA×2 Flash Attention path and compiling it with `GGML_CUDA_FATTN_VEC_GQA_HEADS=2`.

Explicit exclusions:
- no `safe.patch`, `operator.patch`, `mtp-subvocab.patch` or unrelated SM70/GDN tuning;
- no `--split-mode tensor` topology experiment;
- no F16/Q4 KV substitution;
- no MTP/NGRAM;
- no clock/power-limit change;
- no batch/ubatch/context/workload change.

Required correctness/provenance evidence:
- exact b10775 base commit;
- forward-port patch SHA256 and source provenance;
- build command, CMake/build flags, binary/image hash;
- proof that the candidate build has GQA×2 enabled and the control build does not;
- server/load health, C2 residency/active overlap, both outputs' integrity and post-health;
- peak VRAM and the same performance fields used by R2.

Primary interpretation:
1. Capacity/correctness and `PASS_C2_ACTIVE`.
2. Per-request runtime decode and mean request decode TPS.
3. Peak VRAM.
4. TTFT/prefill.
5. Batch wall/end-to-end throughput.
- `aggregate_decode_tps` remains a mixed overlap/output-window metric and must not be presented as a pure decode-kernel measurement.
- A small positive delta is not automatically a validated optimization because this candidate has only one measured run. Report the exact observed delta and retain measurement-noise caveat.

Stop policy:
- Exactly one measured C2 128K × 2 run is authorized.
- Failure is terminal for this frozen candidate; do not silently add other patches, change KV type or switch topology.
- Harness-invalid/no-request-admitted infrastructure failure is preserved as inconclusive and is not automatically rerun.

### 7.3 Result review / closeout [PLANNED — NO GPU INFERENCE]

Use only:
- frozen WBS 5 R2 control;
- the single valid WBS 7.1 MTP1 measured result, if reached;
- the single valid WBS 7.2 GQA×2 measured result, if reached.

Review separately:
- MTP1: C2 128K feasibility, VRAM cost, speculative activity/acceptance, decode effect and any prefill/wall trade-off.
- GQA×2: correctness, VRAM neutrality/regression, and long-context decode delta with TARGET/Q8_0 unchanged.
- Do not rank by aggregate decode alone.
- Do not infer that MTP1 is the optimal MTP depth.
- Do not infer that MTP and GQA×2 effects are additive.
- Do not create a combined candidate during review.
- WBS 5 historical/frozen results are never rewritten to include WBS 7 outcomes.

WBS 7 completion condition:
- 7.0 provenance/static checks recorded;
- at most one measured execution for 7.1 and at most one for 7.2;
- terminal PASS/FAIL/INCONCLUSIVE evidence preserved without silent fallback;
- 7.3 review records whether either candidate is worth retaining as a separate post-WBS5 recipe.

## 실행 규칙
- 별도 승인이 없는 한 선언된 configuration당 measured execution은 1회만 수행한다.
- 실패 후 context, quantization, KV, speculative method, topology를 조용히 변경해서는 안 된다.
- diagnostic 96K/64K 재실행은 새로운 experiment ID를 사용한다.
- UNSUPPORTED는 유효한 최종 결과다.
- 과거 qwen3.8-bench 결과는 이 저장소에서 PASS로 인정하지 않는다.
