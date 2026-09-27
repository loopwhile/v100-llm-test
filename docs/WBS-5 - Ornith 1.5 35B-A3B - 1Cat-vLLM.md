너는 `loopwhile/v100-llm-test` 저장소에서 다음 WBS5 frozen candidate들의 **로컬 실행 가능성만 검증**한다.

대상:

- MODEL: `Ornith-1.5-35B-A3B`
- model repo: `ornith-ai/Ornith-1.5-35B-A3B-NVFP4`
- revision: `94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`
- local model path: `/srv/models/ornith-1.5-35b-a3b-nvfp4`
- RUNTIME: `1Cat-vLLM 1.5.0`
- Python: `/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python`
- expected wheel SHA256:
  `2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b`

Frozen candidates:

```text
R0-BASELINE-EAGER-MBT4096
R1-GRAPH-AUTO-MBT4096
R2-EAGER-MBT8192
```

R3는 없다.

새 candidate를 추가하거나 recipe를 재설계하지 마라.

# 절대 금지

GPU measured inference를 실행하지 마라.

금지 항목:

- vLLM server를 실제 GPU model-load까지 기동
- performance workload request 실행
- C1/C2 inference 실행
- benchmark 실행
- CUDA Graph capture 실행
- 실제 model forward
- GPU VRAM benchmark
- throughput/TTFT 측정

이번 단계는 오직:

- 파일 검사
- source inspection
- installed package inspection
- CLI/help inspection
- config generation inspection
- static validation
- command diff 검증

만 수행한다.

GPU를 실제 연산에 사용하지 않는 범위에서만 작업한다.

---

# 1. 현재 repository 상태 확인

먼저 현재 `main` HEAD를 기록한다.

다음 파일을 확인한다.

```text
docs/WBS.md
workloads/performance/v1.json
config/models/ornith-1.5-35b-a3b.json
config/runtime-lock.json
scripts/runtime_launcher.py
scripts/run_c1_onecat.py
scripts/run_c2_onecat.py
```

추가 WBS5 runner 또는 optimized/performance runner가 있다면 그것도 찾는다.

확인할 것:

1. WBS5 공식 workload가 `workloads/performance/v1.json`인지.
2. 현재 runner 중 실제로 이 workload를 읽는 것이 있는지.
3. `run_c2_onecat.py`가 여전히 `workloads/concurrency/v2.json`에 고정돼 있는지.
4. WBS5에서 필요한:
   - output >=1024
   - C2 active overlap
   - TTFT
   - prefill tok/s
   - mean request decode tok/s
   - aggregate decode tok/s
   - end-to-end output tok/s
   - batch wall
   - peak VRAM
   - power/temp/clocks
   - output integrity
   - post-health
   를 현재 harness가 수집 가능한지.

GPU inference는 하지 말고 code/static inspection만 한다.

---

# 2. Exact runtime identity 검증

다음을 실제 local environment에서 확인한다.

```text
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python
```

확인 항목:

- Python version
- installed `1cat-vllm` / `vllm` version
- package location
- installed wheel/package files
- 가능하면 installed distribution metadata
- expected wheel SHA receipt와 현재 runtime identity가 일치하는지

wheel 원본 파일이 local에 존재한다면 SHA256을 계산해도 된다.

wheel 원본이 없다면 설치된 package tree만 보고 wheel SHA가 동일하다고 추정하지 마라.

그 경우:

```text
wheel SHA provenance: repo receipt only / local wheel file unavailable
```

로 명시한다.

---

# 3. R0 실행 가능성 static 검증

R0:

```text
R0-BASELINE-EAGER-MBT4096
```

expected serving configuration:

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python \
  -m vllm.entrypoints.openai.api_server \
  --model /srv/models/ornith-1.5-35b-a3b-nvfp4 \
  --served-model-name Ornith-1.5-35B-A3B \
  --trust-remote-code \
  --dtype half \
  --attention-backend FLASH_ATTN_V100 \
  --tensor-parallel-size 2 \
  --kv-cache-dtype fp8_e5m2 \
  --max-model-len 131072 \
  --max-num-seqs 2 \
  --max-num-batched-tokens 4096 \
  --gpu-memory-utilization 0.90 \
  --enforce-eager \
  --host 127.0.0.1 \
  --port 18080
```

실제 server를 실행하지 말고 다음만 확인한다.

- CLI option들이 installed build에 존재하는가.
- parser가 해당 값들을 수용하는가.
- runner/launcher가 이 configuration을 표현할 수 있는가.
- `--enforce-eager`가 실제 설정에 연결되는가.
- target-only 상태를 보장할 수 있는가.
- speculative config가 암묵적으로 들어가지 않는가.

---

# 4. R1 실행 가능성 static 검증

R1:

```text
R1-GRAPH-AUTO-MBT4096
```

R0 대비 exact diff:

```diff
- --enforce-eager
```

그 외에는 절대 변경하지 않는다.

installed package source에서 다음 symbol/logic의 실제 존재 여부를 확인한다.

```text
VLLM_SM70_FLASH_V100_0DOT3_COMPILE_GRAPH
VLLM_DISABLE_COMPILE_CACHE
FULL_AND_PIECEWISE
VLLM_COMPILE
SM70/V100 device capability gate
no-MTP cudagraph capture-size selection
FLASH_ATTN_V100 graph-aware dispatch
fp8_e5m2 graph-aware dispatch
SM70 NVFP4 TurboMind W4A16 route
```

특히 다음 질문에 답한다.

1. `--enforce-eager`를 제거하면 SM70 auto graph policy가 activation 가능한 source 구조인가?
2. 다른 explicit option 없이 runtime auto policy가 graph mode를 선택하는가?
3. 현재 shell/environment에 graph를 disable할 수 있는 env가 설정돼 있는가?

예:

```text
TORCH_COMPILE_DISABLE
VLLM_USE_BREAKABLE_CUDAGRAPH
```

기타 관련 env도 source에서 찾는다.

4. compile-cache quality guard가 installed source에도 존재하는가?
5. E5M2 + FLASH_ATTN_V100가 CUDA graph와 호환되도록 작성된 dispatch path가 있는가?
6. NVFP4 path에 graph capture를 명백히 금지하는 code가 있는가?
7. Qwen3.5-MoE path에 full/piecewise graph를 명백히 금지하는 code가 있는가?

중요:

source에 구현이 존재하는 것과 Ornith runtime에서 실제 route가 hit되는 것은 구분한다.

GPU inference를 하지 않으므로 실제 route hit 여부는:

```text
NOT VERIFIED UNTIL MEASURED RUN
```

으로 남겨라.

---

# 5. R2 실행 가능성 static 검증

R2:

```text
R2-EAGER-MBT8192
```

R0 대비 exact diff:

```diff
- --max-num-batched-tokens 4096
+ --max-num-batched-tokens 8192
```

그 외에는 변경하지 않는다.

확인 항목:

1. installed scheduler가 `max_num_batched_tokens=8192`를 허용하는가.
2. known Mamba alignment condition과 정적인 충돌이 있는가.
3. 기존 실패:
   `block_size=2096 > MBT=2048`
   와 달리 8192는 해당 assertion을 통과 가능한가.
4. runner/launcher가 8192를 다른 값으로 overwrite하지 않는가.
5. `max_num_seqs=2`가 그대로 유지되는가.
6. `--enforce-eager`가 그대로 유지되는가.
7. gpu_memory_utilization=0.90이 그대로 유지되는가.

실제 memory fit 여부는 GPU model-load 없이 확정하지 마라.

그 항목은:

```text
STATICALLY VALID, RUNTIME VRAM FIT UNVERIFIED
```

처럼 구분한다.

---

# 6. Command diff 검증

R0/R1/R2 final commands를 생성하되 실행하지 않는다.

machine-readable diff 또는 명확한 textual diff로 다음을 증명한다.

```text
R0 → R1:
ONLY --enforce-eager removal

R0 → R2:
ONLY max_num_batched_tokens 4096 → 8192
```

다른 env/flag/path/value가 달라지면 오류로 판정한다.

---

# 7. MTP/NGRAM 등은 조사하지 않는다

이번 Freeze에서 제외된 항목:

```text
MTP
MTP_NGRAM
NGRAM
DFlash
KV dtype 변경
gpu_memory_utilization tuning
all-reduce tuning
capture-size tuning
other MBT values
```

새 candidate를 만들지 마라.

단 source inspection 과정에서 우연히 발견되더라도 결과에 후보로 제안하지 않는다.

---

# 8. 최종 출력 형식

다음 순서로 보고한다.

## A. Environment Receipt

- repo HEAD
- Python
- runtime version
- installed package path
- wheel provenance
- model path/revision receipt

## B. WBS5 Harness Readiness

각 항목:

```text
PASS
FAIL
NEEDS IMPLEMENTATION
UNKNOWN
```

으로 판정.

## C. Candidate Static Validation

표 형식:

| Candidate | CLI valid | Runner expressible | Static config valid | Runtime route source exists | GPU execution still needed |
|---|---|---|---|---|---|

## D. R1 Graph Source Audit

위에서 요구한 SM70 graph 관련 symbol/path와 실제 source file/line 또는 함수명을 기록.

## E. R2 MBT Static Audit

8192 admission과 Mamba align 관련 source evidence 기록.

## F. Exact Command Diff

R0/R1/R2 command를 실행하지 않고 출력.

## G. Blocking Issues

GPU measured inference 전에 반드시 해결해야 하는 blocker만 기록.

## H. Final Verdict

각 candidate를 다음 중 하나로만 판정:

```text
READY_FOR_MEASURED_INFERENCE
BLOCKED_BY_HARNESS
BLOCKED_BY_RUNTIME_CONFIG
BLOCKED_BY_MISSING_SOURCE_SUPPORT
NEEDS_LOCAL_RUNTIME_CONFIRMATION
```

중요:

`READY_FOR_MEASURED_INFERENCE`라고 판정해도 실제 inference는 절대 실행하지 마라.

이번 작업의 끝은 실행 가능성 검증이다.
