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
- v100-skinny: 필수 SKINNY lane.
- Shared TP2 및 Ornith 9B 1GPU×2 topology 정의.
- Ornith 9B 1GPU×2는 LiteLLM 단일 gateway endpoint를 포함한 실제 배포 topology로 고정한다. backend 직접 분배는 진단용일 뿐 정식 acceptance 경로가 아니다.

## 1. 신규 환경 및 artifact 검증 [TODO]

### 1.1 호스트 스냅샷
다음을 수집한다.
- NVIDIA driver 및 CUDA compatibility.
- V100 2장의 identity 및 VRAM.
- 전력 제한, clock, persistence 상태.
- CPU/RAM/kernel.
- GPU 사용 중인 process와 listening port.
- 런타임 stdout/stderr를 experiment runtime log 디렉터리에 보존한다.

벤치마크 자동화는 하드웨어 정책을 변경해서는 안 된다.

### 1.2 llama.cpp 런타임 검증
고정된 image/build/commit을 검증하고 다음 기능 지원 여부를 확인한다.
- kv-unified
- kv-unified-per-slot
- spec-type none
- ngram-simple
- draft-mtp
- composite draft-mtp,ngram-simple

### 1.3 1Cat-vLLM STOCK 및 LiteLLM gateway 검증
다음을 검증한다.
- 1Cat-vLLM 1.5.0 exact wheel identity.
- FLASH_ATTN_V100.
- TP2 startup.
- exact STOCK artifact가 확정된 경우 Ornith 9B의 GPU별 TP1 독립 server startup.
- LiteLLM v1.101.0 exact image/version.
- gateway 자체 상태 확인은 inference를 유발할 수 있는 `/health`가 아니라 `/health/liveliness`를 사용할 것.
- Ornith 9B 1GPU×2에서 두 backend를 동일 model group으로 등록하고, least-busy + backend별 max_parallel_requests=1 설정으로 단일 client endpoint를 제공할 것.
- 각 모델 profile의 tokenizer/template/tool/parser 요구사항.

### 1.4 v100-skinny 검증
필수 확인 항목:
- exact skinny commit 5b589c0dc81223e0ba65bcb3e755874723f8b515.
- exact 1Cat-vLLM 1.2.2 wheel.
- exact Qwen3.8 RadixArk revision.
- TP2 experimental boot.
- TP2, depth 3 조건의 skinny_gate.py PASS.

TP2 실패는 UNSUPPORTED, FAIL_STARTUP, FAIL_OOM, FAIL_CAPACITY 중 실제 결과로 유지한다. 공개된 TP4 결과로 대체해서는 안 된다.

### 1.5 모델 artifact 확정
기존에 고정된 다음 artifact를 새 환경에서 다시 검증한다.
- Qwen3.8-27B llama.cpp.
- Qwen3.8-27B STOCK 1Cat.
- Qwen3.8-27B SKINNY.
- Ornith 1.5 9B llama.cpp.
- Ornith 1.5 35B-A3B llama.cpp.

다음 항목은 실제 지원 여부를 확인해 artifact를 확정하거나 unsupported/pending으로 명시한다.
- Ornith 9B STOCK 1Cat NVFP4.
- Ornith 35B STOCK 1Cat NVFP4.
- Gemma4 26B llama.cpp exact artifact.
- Gemma4 26B STOCK 1Cat NVFP4.
- non-Qwen v100-skinny contract.

repository, revision, path를 추정해서 채우는 것은 금지한다.

## 2. C1 — 128K capacity 및 correctness [TODO]

workloads/capacity/v1.json을 사용하며, 정확한 live tokenizer 기준으로 materialize한다.

### 2.1 llama.cpp 필수 lane
검증된 모든 llama.cpp artifact에 대해 다음을 실행한다.
1. TARGET
2. NGRAM
3. MTP
4. MTP_NGRAM

규칙:
- TARGET vs NGRAM 비교는 필수다.
- MTP 또는 MTP_NGRAM이 UNSUPPORTED이더라도 두 항목은 결과 행으로 명시적으로 남긴다.
- 처음부터 128K로 테스트한다.
- 96K/64K는 128K capacity 실패 이후 원인 확인용 diagnostic으로만 사용한다.

C1 PASS 조건:
- live tokenizer 기준 전체 context budget이 128K에 근접할 것.
- 요청한 output이 정상 완료될 것.
- 출력이 유효할 것.
- OOM, truncation, corruption이 없을 것.
- 실행 후 server가 정상 상태일 것.

### 2.2 1Cat-vLLM STOCK
검증된 모든 STOCK artifact에 대해:
- TP2.
- max_model_len 131072.
- max_num_seqs 1.
- 선언된 KV format.
- 신규 C1 128K acceptance 수행.

### 2.3 v100-skinny SKINNY
필수 Qwen3.8 TP2 실험:
- v100-skinny v1.1.
- 1Cat 1.2.2.
- RadixArk mixed NVFP4/FP8 checkpoint.
- FP16 KV.
- MTP k=3.
- 128K.
- TP2 skinny boot gate 결과를 evidence로 보존.

non-Qwen skinny row는 실제 실행 가능한 지원 상태로 확정하거나 UNSUPPORTED로 판정한다.

## 3. C2 — 독립적인 128K 에이전트 2개 [TODO]

선행 조건:
- 동일한 exact lane이 C1 128K를 PASS해야 한다.
- 단, C2 capacity 한계 자체를 확인하기 위한 의도적인 failure-boundary 실험은 예외로 한다.

workloads/concurrency/v1.json을 사용하며 다음을 보장한다.
- Project A와 Project B는 서로 무관한 프로젝트다.
- prompt hash가 서로 다르다.
- 인위적으로 큰 shared prefix를 만들지 않는다.

### 3.1 Shared TP2 llama.cpp
다음 설정을 사용한다.
- parallel 2.
- ctx-size 262144.
- kv-unified.
- kv-unified-per-slot 131072.

### 3.2 Shared TP2 1Cat / skinny
다음 설정을 사용한다.
- TP2.
- max_model_len 131072.
- max_num_seqs 2.

다음 항목을 각각 분리해서 기록한다.
- 두 request가 모두 admission 되었는가.
- 두 context가 동시에 resident 상태였는가.
- sampled runtime state 기준 실제 active decode overlap이 있었는가.
- queue/preemption 동작(llama.cpp requests_processing/requests_deferred + slots, vLLM num_requests_running/num_requests_waiting).
- request별 성능 및 aggregate 성능.

QUEUE_ONLY를 PASS_C2_ACTIVE로 판정해서는 안 된다.

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

### 5.2 1Cat
Qwen3.8에 대해 STOCK과 SKINNY를 실제 서빙 구성 관점에서 비교한다.

checkpoint, KV, speculative, runtime identity가 서로 다름을 명시하며, 이를 단순 kernel-only causal A/B 테스트처럼 해석하지 않는다.

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
