# 작업 목적

Qwen3.8-27B / 1Cat-vLLM WBS5 candidate set이 R0~R3으로 Freeze되었다.

이번 작업은 **로컬 실행 가능성 검증만 수행한다.**

절대로 GPU measured inference, benchmark, server startup, model loading을 실행하지 마라.

새 candidate를 제안하거나 추가하지 마라.

검증 대상은 오직 다음 4개다.

- R0-E4M3-128K-SEMANTIC-BASELINE
- R1-E4M3-128K-CUDAGRAPH-C1
- R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL
- R3-E5M2-128K-KV-ROUTE

---

# 절대 금지

다음 작업은 수행하지 않는다.

- `vllm serve`
- OpenAI API server 실행
- EngineCore 실행
- model load
- tokenizer를 이용한 full workload inference
- CUDA Graph 실제 capture
- Triton/TileLang kernel compilation 또는 warmup
- GPU benchmark
- CUDA kernel 실행
- 128K request 실행
- 짧은 probe inference
- 임의의 새로운 성능 option 제안
- runtime/source 수정
- model artifact 수정
- 기존 raw evidence 수정
- package install/update
- CUDA/toolchain 설치
- git checkout 변경
- 새 branch/commit 생성

가능하면 `grep`, `sed`, `find`, `sha256sum`, JSON parsing, Python AST/text inspection 등 **파일 정적 분석**만 사용한다.

Python이 필요하면 model을 load하거나 `torch.cuda`를 호출하지 않는 범위에서만 사용한다.

---

# 1. Runtime identity 확인

현재 실제 사용 예정인 1Cat-vLLM runtime을 찾아 다음을 기록한다.

- vLLM/1Cat package version
- 설치 경로
- wheel/package identity
- 가능한 경우 wheel SHA256 또는 설치 artifact SHA256
- git checkout 기반이면 exact commit
- Python version
- CUDA runtime 관련 package version
- `flash_attn_v100` native extension 파일 존재 여부와 파일 SHA256
- `flash_qla` / TileLang 관련 package와 설치 경로

중요:

upstream GitHub source가 아니라 **현재 P520에서 실제 실행될 pinned runtime 파일**을 authoritative local source로 취급한다.

upstream과 local source가 다르면 차이를 명시한다.

---

# 2. Model identity 확인

Qwen3.8-27B QUASAR NVFP4 local artifact에 대해 다음을 기록한다.

- exact model path
- config.json SHA256
- 주요 safetensors identity/hash
- architecture
- model_type
- max_position_embeddings
- `mtp_num_hidden_layers`
- `speculators_config` 존재 여부
- KV 관련 scale/config metadata 존재 여부

특히 다음을 명확히 답한다.

```text
Does config.json contain "speculators_config"?
YES / NO
```

`mtp_num_hidden_layers`와 `speculators_config`를 혼동하지 마라.

---

# 3. R0 feasibility

현재 local pinned runtime/source에서 다음 option들이 실제 존재하고 사용할 수 있는지 정적으로 확인한다.

- `--kv-cache-dtype fp8_e4m3`
- `--language-model-only`
- `--max-model-len 131072`
- `--max-num-seqs 1`
- `--max-num-batched-tokens 2048`
- `--gpu-memory-utilization 0.92`
- `--enforce-eager`
- `FLASH_ATTN_V100`
- `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`

또한 다음 resolved/default를 source에서 확인한다.

- `enable_dbo`
- `ubatch_size`
- custom all-reduce default
- P2P/NCCL 관련 default
- prefix caching default 또는 launcher override
- speculative configuration 생성 경로

`maybe_override_with_speculators()`가 현재 model artifact에서 자동 spec decode를 활성화할 수 있는지 local config와 함께 결론내라.

R0 판정:

```text
SUPPORTED
UNSUPPORTED
VERIFY_AT_RUNTIME
```

중 하나.

---

# 4. R1 CUDA Graph feasibility

실제 local pinned source에서 다음을 확인한다.

1. CUDA Graph 관련 CLI/config key의 정확한 이름
2. capture size `[1]`을 지정하는 exact syntax
3. FULL / FULL_DECODE_ONLY 등 가능한 mode
4. target-only C1에서 어떤 mode가 맞는지 source contract
5. GDN backend의 `decode_cudagraph_max_bs` 계산식
6. `max_num_seqs=1` + spec=None일 때 `[1]`이 충분한지
7. Flash-V100 backend가 graph capture/replay를 지원하는 코드 경로
8. GDN recurrent path가 graph execution에서 사용 가능한 코드 경로
9. TP2 collective가 CUDA Graph와 관련해 특별한 제한을 갖는지
10. graph capture/replay 여부를 추후 로그로 검증할 수 있는 기존 debug/route flag

실제 graph capture는 하지 않는다.

R1에 필요한 command diff를 **실행하지 말고 텍스트로만** 작성한다.

판정:

```text
SUPPORTED
UNSUPPORTED
VERIFY_AT_RUNTIME
```

---

# 5. R2 Original FlashQLA feasibility

local pinned source에서 다음 함수/분기를 찾아라.

```text
_resolve_gdn_prefill_backend
_sm70_flashqla_original_prefill_enabled
flashqla_sm70_chunk_gated_delta_rule
```

그리고 다음을 확인한다.

- `VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL` 실제 지원 여부
- `0`일 때 route
- `1`일 때 route
- `flashqla_sm70` backend가 선택되기 위한 exact 조건
- 현재 model dtype/head_k_dim이 해당 조건을 만족하는지
- `flash_qla` Python/module files가 현재 설치되어 있는지
- original TileLang function 파일이 실제 존재하는지
- TileLang package 존재 여부
- nvcc/CUDA path를 요구하는 static code path가 있는지

다음 adjacent flag도 현재 값/default를 기록한다.

```text
VLLM_SM70_FLASHQLA_INDEXED_PREFILL
VLLM_SM70_FLASHQLA_DIRECT_OUTPUT
VLLM_SM70_FLASHQLA_DECODE_WARMUP
```

중요:

환경이 실제 kernel compile까지 가능한지는 inference/JIT 없이 100% 증명할 수 없을 수 있다.

그 경우 억지로 PASS하지 말고:

```text
VERIFY_AT_RUNTIME
```

으로 남겨라.

과거 실패의 원인과 현재 설치 상태가 정적으로 달라졌는지도 비교하되, kernel을 실행하지 않는다.

R2 판정:

```text
SUPPORTED
UNSUPPORTED
VERIFY_AT_RUNTIME
```

---

# 6. R3 E5M2 feasibility

local pinned runtime에서 다음을 확인한다.

- explicit `fp8_e5m2` parser support
- SM70에서 `fp8_e5m2` resolve 결과
- Flash-V100 backend가 E5M2를 받아들이는지
- E5M2 XQA/paged decode 코드 존재 여부
- E5M2-specific native extension symbol 또는 wrapper 존재 여부
- E5M2가 model weight quantization과 독립적인 KV-only option인지
- E5M2 변경이 GDN recurrent state dtype까지 바꾸는지 여부

generic:

```text
--kv-cache-dtype fp8
```

은 candidate가 아니다.

반드시 explicit:

```text
--kv-cache-dtype fp8_e5m2
```

만 검증한다.

현재 local pinned source의 generic fp8 alias가 무엇으로 resolve되는지는 provenance 차원에서만 기록한다.

R3 판정:

```text
SUPPORTED
UNSUPPORTED
VERIFY_AT_RUNTIME
```

---

# 7. Environment contamination audit

현재 실행 shell / launcher / service unit / project scripts에서 다음 prefix를 전부 찾아 기록한다.

```text
VLLM_SM70_
VLLM_FLASH_V100_
VLLM_DFLASH_
FLASH_QLA_
NCCL_
CUDA_
```

후보별로 의도하지 않은 environment delta가 있는지 확인한다.

특히 R0~R3가 OFAT가 되려면:

- R1은 graph 관련 delta만
- R2는 ORIGINAL_PREFILL delta만
- R3는 KV dtype delta만

이어야 한다.

숨겨진 launcher default 때문에 다른 값까지 함께 바뀌면 반드시 보고한다.

수정하지는 마라.

---

# 8. 최종 산출물

GPU를 실행하지 않고 다음 표를 작성한다.

| Candidate | Local verdict | Exact supported delta | Blocking issue | Runtime-only uncertainty |
|---|---|---|---|---|
| R0 | | | | |
| R1 | | | | |
| R2 | | | | |
| R3 | | | | |

그리고 별도로:

## A. Runtime receipt
정확한 runtime/model/source/native-extension identity.

## B. Frozen invariant receipt
R0~R3에 공통으로 실제 고정 가능한 값.

## C. Candidate command diff
R1/R2/R3 각각 R0 대비 **정확히 한 축만 변경한 command/env diff**.

## D. Pre-inference blockers
GPU measured inference 전에 해결 또는 확인해야 하는 항목만 나열.

## E. Unexpected findings
Freeze된 candidate의 실행 가능성을 직접 뒤집는 사항만 작성.

새 최적화 후보나 성능 아이디어는 제안하지 않는다.

---

# 최종 원칙

이번 작업의 목적은:

```text
"무엇을 테스트하면 빠를까?"
```

가 아니라:

```text
"Freeze된 R0~R3가 현재 P520의 실제 pinned runtime에서
문법적·소스적·artifact적으로 실행 가능한가?"
```

를 확인하는 것이다.

GPU measured inference는 절대 실행하지 마라.
