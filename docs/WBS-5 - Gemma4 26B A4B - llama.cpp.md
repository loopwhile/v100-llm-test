너는 `loopwhile/v100-llm-test`의
Gemma4 26B-A4B / llama.cpp WBS5 frozen candidate set에 대해
**로컬 실행 가능성만 검증**한다.

중요:

**GPU measured inference는 절대 실행하지 마라.**

금지:

- 모델 inference 요청
- performance workload 실행
- C1/C2 benchmark 실행
- llama-server에 모델을 load한 상태로 inference
- llama-bench 또는 성능 측정
- CUDA kernel benchmark
- R0/R1/R2/R3 실제 성능 run
- 기존 raw artifact 수정
- 기존 benchmark 결과 수정
- candidate 추가
- candidate parameter 임의 변경

허용:

- repository 파일 확인
- config 확인
- launcher/runner source 확인
- pinned image/runtime identity 확인
- `--version`
- `--help`
- binary feature introspection
- container metadata 확인
- 모델 파일 존재 여부와 SHA256 확인
- command dry-run 또는 command construction 확인
- GPU topology/P2P 정보 확인
- model을 load하지 않는 범위의 CUDA/device introspection

어떤 명령이 모델 load 또는 measured inference를 시작할 가능성이 있으면
실행하지 말고 `NEEDS_MEASURED_RUN`으로 기록해라.

---

# Frozen candidates

새 candidate를 만들지 않는다.

```text
R0 = G4-LCPP-WBS5-R0-TARGET-B512-UB128

R1 = G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128

R2 = G4-LCPP-WBS5-R2-TARGET-B1024-UB128

R3 = G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF
     CONDITIONAL
```

R3 gate가 충족되지 않아도
대체 candidate를 추가하지 않는다.

---

# Fixed identities

Model:

```text
Gemma4-26B-A4B-IT-QAT

repo:
unsloth/gemma-4-26B-A4B-it-qat-GGUF

revision:
7b92b5b28818151e8669af2e45e88d6086f490dd

target:
/srv/models/gemma-4-26b-a4b-it-qat-gguf/
gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf

SHA256:
a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891

weight:
UD-Q4_K_XL

KV:
FP16
```

Runtime:

```text
llama.cpp build 10775
commit:
67a17c17caa95742186f8b1ecadd1b5abd6d5ebb

image:
kyuz0/nvidia-v100-ai-toolboxes@
sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149
```

Topology:

```text
2× V100 SXM2 16GB

repo topology ID:
tp2-shared

actual implementation:
--split-mode layer
--tensor-split 1,1
```

C2 contract:

```text
--ctx-size 262144
--parallel 2
--kv-unified
--kv-unified-per-slot 131072

--cache-type-k f16
--cache-type-v f16

--flash-attn on
```

Formal workload:

```text
workloads/performance/v1.json
```

---

# Task 1 — repository/current main 확인

현재 GitHub/local checkout의 main/HEAD를 확인하고
WBS5 관련 파일이 frozen candidate assumptions와 충돌하지 않는지 확인해라.

필요한 파일만 본다.

최소:

```text
docs/WBS.md
config/models/gemma4-26b-a4b.json
config/runtime-lock.json
scripts/runtime_launcher.py
workloads/performance/v1.json
```

WBS5 runner가 별도로 존재하면 그것도 확인한다.

보고:

```text
HEAD
dirty/clean status
relevant file paths
candidate contract conflict 여부
```

파일 수정은 하지 마라.

---

# Task 2 — exact artifact 검증

실제 로컬 target GGUF:

```text
/srv/models/gemma-4-26b-a4b-it-qat-gguf/
gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf
```

에 대해 확인:

```text
exists?
size
SHA256
expected SHA와 일치?
```

MTP artifact는 이번 frozen candidate set에서 사용하지 않으므로
검증 대상으로 확장하지 마라.

---

# Task 3 — pinned runtime 검증

Pinned OCI image가 로컬에 존재하는지 확인하고:

```text
image digest
llama-server --version
```

을 확인한다.

Expected:

```text
build 10775
commit prefix consistent with 67a17c17...
```

모델은 load하지 마라.

---

# Task 4 — pinned binary option 검증

`llama-server --help` 또는 동등한 non-inference 방법으로
다음 option이 실제 pinned binary에 존재하는지 확인한다.

```text
--split-mode
--tensor-split

--ctx-size
--parallel

--kv-unified
--kv-unified-per-slot

--batch-size
--ubatch-size

--cache-type-k
--cache-type-v

--flash-attn

--spec-type
```

특히 R1:

```text
ngram-simple
```

지원 여부 확인.

가능하면 binary help에서:

```text
--spec-ngram-simple-size-n
--spec-ngram-simple-size-m
--spec-ngram-simple-min-hits
```

와 default를 확인한다.

Expected source defaults:

```text
N = 12
M = 48
min-hits = 1
```

actual binary가 다르면
candidate를 수정하지 말고 차이만 보고해라.

---

# Task 5 — R0 command construction 검증

실제 inference를 실행하지 않고
launcher/runner가 R0에 대해 생성할 expected command를 확인해라.

필수 포함:

```text
-ngl all
--split-mode layer
--tensor-split 1,1

--ctx-size 262144
--parallel 2
--kv-unified
--kv-unified-per-slot 131072

--batch-size 512
--ubatch-size 128

--cache-type-k f16
--cache-type-v f16

--flash-attn on

--spec-type none
```

다음도 확인:

```text
--jinja
--reasoning off
--metrics
--slots
--no-warmup
```

실제 server start는 하지 마라.

---

# Task 6 — R1 diff 검증

R1 command가 R0 대비 정확히:

```text
--spec-type none
→
--spec-type ngram-simple
```

만 바뀌는지 확인한다.

다음이 임의 추가되면 FAIL:

```text
explicit N/M/hits override
MTP model
MTP options
batch change
ubatch change
context change
topology change
```

---

# Task 7 — R2 diff 검증

R2가 R0 대비 정확히:

```text
--batch-size 512
→
--batch-size 1024
```

만 바뀌는지 확인.

반드시:

```text
--ubatch-size 128
```

은 그대로여야 한다.

가능하면 binary/system metadata에서:

```text
PEER_MAX_BATCH_SIZE
```

를 확인한다.

또한 로컬 GPU topology에서 가능한 범위 내:

```text
GPU0 ↔ GPU1 P2P capability
NVLink / PCIe topology
```

를 확인한다.

이 정보는 R2를 자동 PASS/FAIL시키기 위한 것이 아니라
나중의 성능 해석을 위한 preflight evidence다.

GPU inference는 실행하지 마라.

---

# Task 8 — CUDA Graph feasibility 검증

R3에서 가장 중요하다.

Pinned source가 아니라
가능하면 **actual pinned binary/image**를 기준으로:

```text
USE_GRAPHS = 1
```

인지 확인한다.

모델 inference 없이 확인 가능한 방법을 먼저 사용한다.

예:

```text
binary feature metadata
system_info를 출력하지만 모델을 load하지 않는 안전한 command
binary inspection
```

단, 모델을 load해야만 확인할 수 있다면 실행하지 말고:

```text
VERIFY_DURING_R0_STARTUP
```

으로 기록한다.

다음도 확인:

```text
GGML_CUDA_DISABLE_GRAPHS
```

가 pinned runtime source/binary에서 실제 유효한지.

그리고 container environment로 전달 가능한지 확인한다.

R3에 대해 현재 단계에서 판정 가능한 것은:

```text
SUPPORTED
UNSUPPORTED
VERIFY_DURING_R0_STARTUP
```

뿐이다.

**R3 GPU inference는 실행하지 마라.**

R3 Gate B:

```text
R0에서 VRAM upward drift 또는 graph-related instability
```

는 measured inference 후에만 평가 가능하므로
현재는 반드시:

```text
PENDING_MEASURED_EVIDENCE
```

로 남겨라.

---

# Task 9 — workload 검증

`workloads/performance/v1.json`을 읽고 다음을 확인한다.

```text
workload_id
mode = performance
context target
output reserve
min_output_tokens = 1024
two independent projects
temperature = 0
identifier diversification
```

WBS3 concurrency workload와 혼동되지 않는지 확인한다.

파일은 수정하지 마라.

---

# Task 10 — 실행 준비상태 판정

각 candidate를 다음 네 상태 중 하나로만 판정한다.

```text
READY_FOR_MEASURED_RUN
BLOCKED
VERIFY_DURING_R0_STARTUP
SKIPPED_NOT_APPLICABLE
```

단:

R0/R1/R2에 대해 실제 inference를 수행해서
READY를 증명하려 하지 마라.

READY는 오직:

```text
artifact
runtime
command
binary feature
runner
workload
```

의 static/preflight 검증을 의미한다.

R3는 Gate B 때문에 이 단계에서
완전 READY가 될 수 없을 수 있다.

---

# Final report format

다음 형식으로만 정리해라.

## A. Environment Identity

```text
repo HEAD:
working tree:
image:
runtime:
model SHA:
GPU topology:
```

## B. Binary Feature Check

| Feature | Result | Evidence |
|---|---|---|
| layer split | | |
| tensor-split arg | | |
| kv-unified | | |
| kv-unified-per-slot | | |
| b/ub | | |
| ngram-simple | | |
| NGRAM defaults | | |
| CUDA Graph compile status | | |
| GGML_CUDA_DISABLE_GRAPHS | | |

## C. Candidate Validation

| Candidate | Static status | Exact diff verified? | Blocker |
|---|---|---|---|
| R0 | | | |
| R1 | | | |
| R2 | | | |
| R3 | | | |

## D. Exact Expected Commands

R0/R1/R2/R3 각각에 대해
실제로 실행될 것으로 예상되는 command/env를 출력하되
**실행하지 마라.**

## E. Differences / Problems Found

Candidate freeze 문서와 actual local runtime/repo가 다른 부분만 기록.

추정하지 마라.

## F. Final Pre-Inference Verdict

각 candidate:

```text
R0:
R1:
R2:
R3:
```

그리고 마지막 줄:

```text
GPU MEASURED INFERENCE EXECUTED: NO
```

반드시 NO여야 한다.
