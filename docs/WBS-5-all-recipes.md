# WBS 5 — All recipes, measured results and launch commands

Date: 2026-09-29 · Updated: 2026-09-30

Update: 2026-09-30 · Ornith 35B / 1Cat R1 동일 설정 재측정 `PASS_C2_ACTIVE`를 현재 authoritative result로 반영했다. 2026-09-29 원측정 `FAIL_OUTPUT`은 historical evidence로 보존하며, current 5.5 final recipe는 R0에서 R1으로 갱신한다.

이 문서는 WBS 5.5가 최종 review한 **7개 model/runtime track의 frozen candidate 25개 전체**를 한 곳에 기록한다. `WBS-5.5-final-recipes.md`가 승격된 6개 final recipe 중심이라면, 이 문서는 baseline, closed candidate, output failure, queue-only, gate skip, toolchain blocked까지 포함한 **전체 recipe ledger**다.

2026-09-29 원래 WBS 5.5 publication 단계 자체에서는 새 GPU inference를 수행하지 않았다. 이후 2026-09-30 사용자 요청으로 기존 frozen R1 동일 설정을 독립 재측정했고, 해당 `PASS_C2_ACTIVE` 결과를 현재 publication에 반영했다. 그 외 측정값은 기존 canonical raw/report의 관찰값이다. 모든 performance workload는 독립 Project A/B 두 요청, 요청당 131,072-token ceiling, output reserve 4,096 / minimum 1,024, temperature 0 / top_p 1 / seed 520을 기준으로 한다.

## 읽는 법

- `C2 ACTIVE`는 두 요청의 실제 active overlap이 증명된 경우다. `QUEUE_ONLY`는 두 요청을 제출했지만 서버에서 동시에 active하지 못한 경우다.
- `FAIL_OUTPUT` 수치는 diagnostic observation으로 보존하되 정상 recipe와 직접 성능 비교하지 않는다.
- `NOT_RUN`, `BLOCKED`, `SKIP` candidate에는 측정값을 채우지 않는다.
- `Mean decode`와 `Agg decode`는 같은 지표가 아니다. Aggregate는 overlap/scheduling과 output 길이의 영향을 포함한다.
- VRAM은 measured window에서 0.5초 간격 `nvidia-smi memory.used` sampled peak다.
- WBS5 performance workload의 mechanical output PASS는 별도 task-level semantic certification을 뜻하지 않는다.
- Qwen llama R0는 같은 frozen configuration을 2회 측정했으므로 한 candidate 행에 두 관찰값을 병기한다.

## 전체 candidate / 성능 / VRAM

### 1. Qwen3.8-27B / llama.cpp

| Candidate | 설정 | 실행 verdict | 동시요청 | TTFT s | Prefill tok/s | Mean decode | Agg decode | E2E tok/s | Wall s | Output | Peak VRAM MiB<br>GPU0/GPU1 | 5.5 final disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 `Q38-LLAMA-WBS5-R0-TARGET-B512-UB128` | TARGET · b512/ub128 · Q8_0 | PASS_C2_ACTIVE ×2 | C2 ACTIVE / queue=false | 901.97<br>904.12 | 206.12<br>178.23 | 5.269<br>5.385 | 3.693<br>3.958 | 2.527<br>2.732 | 1541.28<br>1580.35 | 3895<br>4318 | 13159/14247<br>13159/14245 | REFERENCE_ONLY |
| R1 `Q38-LLAMA-WBS5-R1-NGRAM-DEFAULT` | NGRAM · b512/ub128 · Q8_0 | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 904.45 | 178.17 | 5.559 | 3.998 | 2.744 | 1560.73 | 4283 | 13161/14249 | CLOSED_NO_QUALIFYING_BENEFIT |
| ⭐ R2 `Q38-LLAMA-WBS5-R2-TARGET-UB256` | TARGET · b512/ub256 · Q8_0 | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 679.05 | 264.11 | 5.593 | 4.514 | 3.457 | 1337.27 | 4623 | 13447/14533 | VALIDATED_RECIPE |

R0는 동일 frozen configuration 반복 2회다. R1/R2 optional confirm은 `SKIP — USER_DECISION`이며 별도 measured raw가 없다.

### 2. Ornith 1.5 9B / llama.cpp — 1GPU×2 + LiteLLM

| Candidate | 설정 | 실행 verdict | 동시요청 | TTFT s | Prefill tok/s | Mean decode | Agg decode | E2E tok/s | Wall s | Output | Peak VRAM MiB<br>GPU0/GPU1 | 5.5 final disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 `TARGET_BASELINE` | TARGET · b512/ub128 · FP16 KV | PASS_C2_ACTIVE | C2 ACTIVE / distinct backends | 182.02 | 697.74 | 43.81 | 77.73 | 13.03 | 215.90 | 2814 | 10893/10893 | REFERENCE_ONLY |
| ⭐ R1 `TARGET_UB256` | TARGET · b512/ub256 · FP16 KV | PASS_C2_ACTIVE | C2 ACTIVE / distinct backends | 139.20 | 912.19 | 43.99 | 80.90 | 16.20 | 173.34 | 2808 | 10945/10945 | VALIDATED_RECIPE |
| R2 `NGRAM_DEFAULT` | NGRAM · b512/ub128 · FP16 KV | PASS_C2_ACTIVE | C2 ACTIVE / distinct backends | 182.04 | 697.67 | 43.21 | 76.57 | 13.00 | 216.41 | 2814 | 10893/10893 | CLOSED_NO_DRAFT_ACTIVITY |

모든 run은 단일 LiteLLM endpoint를 통해 project-a→GPU0/backend-0, project-b→GPU1/backend-1로 분산됐고 active overlap=true였다. R2는 `ngram-simple`로 실행됐지만 measured-window draft counter가 0이었다.

### 3. Ornith 1.5 35B-A3B / llama.cpp

| Candidate | 설정 | 실행 verdict | 동시요청 | TTFT s | Prefill tok/s | Mean decode | Agg decode | E2E tok/s | Wall s | Output | Peak VRAM MiB<br>GPU0/GPU1 | 5.5 final disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 `ORN35-LLAMA-WBS5-R0-TARGET` | TARGET · b512/ub128 · Q8_0 | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 791.44 | 191.42 | 15.406 | 5.400 | 3.218 | 1176.33 | 3786 | 12831/12309 | REFERENCE_ONLY |
| ⭐ R1 `ORN35-LLAMA-WBS5-R1-MTP1` | native MTP1 · b512/ub128 · Q8_0 | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 833.07 | 182.78 | 17.329 | 5.709 | 3.432 | 1242.84 | 4265 | 12897/13737 | VALIDATED_RECIPE — DECODE_ORIENTED |
| ⭐ R2 `ORN35-LLAMA-WBS5-R2-UB256` | TARGET · b512/ub256 · Q8_0 | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 670.09 | 229.75 | 15.697 | 7.228 | 4.505 | 1038.99 | 4681 | 13103/12581 | VALIDATED_RECIPE — LONG_PREFILL |
| R3 `ORN35-LLAMA-WBS5-R3-QUEUE4X` | TARGET · b512/ub128 · `CUDA_SCALE_LAUNCH_QUEUES=4x` | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 791.61 | 191.38 | 15.390 | 5.399 | 3.218 | 1176.66 | 3786 | 12831/12309 | CLOSED_NO_MEASURABLE_BENEFIT |

R1 최초 `-001`은 measured request 전 port conflict로 INCONCLUSIVE이며 성능표에서 제외했다. R1 수치는 사용자 승인 재실행 `-002`다. R1 MTP1 acceptance는 1838/2426 = 75.76%. R1+R2 결합 설정은 검증하지 않았다.

### 4. Gemma4 26B-A4B / llama.cpp

| Candidate | 설정 | 실행 verdict | 동시요청 | TTFT s | Prefill tok/s | Mean decode | Agg decode | E2E tok/s | Wall s | Output | Peak VRAM MiB<br>GPU0/GPU1 | 5.5 final disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ⭐ R0 `G4-LCPP-WBS5-R0-TARGET-B512-UB128` | TARGET · b512/ub128 · FP16 KV | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 439.10 | 359.09 | 22.54 | 7.54 | 4.78 | 671.54 | 3213 | 10039/10537 | VALIDATED_RECIPE |
| R1 `G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128` | NGRAM · b512/ub128 · FP16 KV | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 448.49 | 353.18 | 21.48 | 7.10 | 4.52 | 685.38 | 3097 | 10039/10607 | CLOSED_PERFORMANCE_REGRESSION |
| R2 `G4-LCPP-WBS5-R2-TARGET-B1024-UB128` | TARGET · b1024/ub128 · FP16 KV | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 440.10 | 355.46 | 22.28 | 7.60 | 4.77 | 670.94 | 3203 | 10039/10537 | CLOSED_NO_QUALIFYING_BENEFIT |
| R3 `G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF` | TARGET · b512/ub128 · graph off | SKIP — Gate B NOT_TRIGGERED | NOT_RUN | — | — | — | — | — | — | — | — | SKIPPED_GATE_B_NOT_TRIGGERED |

R3는 실패 run이 아니라 R0에서 VRAM upward drift/graph instability가 관측되지 않아 조건부 Gate B가 발동하지 않은 미실행 candidate다.

### 5. Qwen3.8-27B / 1Cat-vLLM

| Candidate | 설정 | 실행 verdict | 동시요청 | TTFT s | Prefill tok/s | Mean decode | Agg decode | E2E tok/s | Wall s | Output | Peak VRAM MiB<br>GPU0/GPU1 | 5.5 final disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 `R0-E4M3-128K-SEMANTIC-BASELINE` | E4M3 KV · eager · max-seqs1 · MBT2048 | QUEUE_ONLY | C2 request submitted / active=false | 1298.20 | 121.95 | 9.38 | 5.02 | 3.43 | 2270.90 | 7788 | 15567/15567 | NO_ELIGIBLE_RECIPE_QUEUE_ONLY |
| R1 `R1-E4M3-128K-CUDAGRAPH-C1` | E4M3 KV · graph capture size 1 | FAIL_STARTUP — compile CUDA OOM | NOT_REACHED | — | — | — | — | — | — | — | — | CLOSED_FAIL_STARTUP |
| R2 `R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL` | E4M3 KV · eager · original FlashQLA prefill | BLOCKED_BY_HOST_TOOLCHAIN | NOT_RUN | — | — | — | — | — | — | — | — | BLOCKED_BY_HOST_TOOLCHAIN_NOT_RUN |
| R3 `R3-E5M2-128K-KV-ROUTE` | E5M2 KV · eager · max-seqs1 · MBT2048 | QUEUE_ONLY | C2 request submitted / active=false | 470.11 | 457.97 | 9.49 | 7.86 | 6.71 | 1160.41 | 7788 | 16117/16117 | NO_ELIGIBLE_RECIPE_QUEUE_ONLY |

R0/R3는 두 128K 요청을 모두 mechanical PASS로 완료했지만 `max-num-seqs=1`이라 peak processing=1 / waiting=1의 QUEUE_ONLY다. R1은 Torch Inductor compile 중 CUDA OOM이며 measured request가 없다. R2는 nvcc/승인된 isolated CUDA development toolkit 부재로 미실행이다.

### 6. Ornith 1.5 9B / 1Cat-vLLM — G0 semantic FAIL 이후 diagnostic

| Candidate | 설정 | 실행 verdict | 동시요청 | TTFT s | Prefill tok/s | Mean decode | Agg decode | E2E tok/s | Wall s | Output | Peak VRAM MiB<br>GPU0/GPU1 | 5.5 final disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 `ORN15-9B-1CAT-WBS5-R0-BASELINE` | FP16 KV · eager · MTP1 · MBT4096 | FAIL_OUTPUT | C2 ACTIVE / queue=false | 299.28 | 424.28 | 10.01 | 14.85 | 5.60 | 478.89 | 2684 | 13899/13899 | NO_ELIGIBLE_RECIPE_G0_FAIL_OUTPUT |
| R1 `ORN15-9B-1CAT-WBS5-R1-MBT8192` | FP16 KV · eager · MTP1 · MBT8192 | FAIL_OUTPUT | C2 ACTIVE / queue=false | 299.38 | 424.13 | 10.01 | 14.85 | 5.60 | 478.98 | 2684 | 13995/13995 | NO_ELIGIBLE_RECIPE_G0_FAIL_OUTPUT |
| R2 `ORN15-9B-1CAT-WBS5-R2-TARGET-GRAPH` | FP16 KV · graph target · MTP1 · MBT4096 | FAIL_OUTPUT | C2 ACTIVE / queue=false | 302.53 | 419.71 | 11.74* | 19.53* | 5.29* | 413.14* | 2184 | 14019/14019 | NO_ELIGIBLE_RECIPE_G0_FAIL_OUTPUT |
| R3 `ORN15-9B-1CAT-WBS5-R3-MTP2` | FP16 KV · eager · MTP2 · MBT4096 | FAIL_OUTPUT | C2 ACTIVE / queue=false | 302.16 | 420.24 | 11.27* | 17.32* | 5.99* | 459.76* | 2754 | 13883/13885 | NO_ELIGIBLE_RECIPE_G0_FAIL_OUTPUT |

G0 semantic audit에서 Project B가 seeded race가 아닌 `_sequence` 문제를 지목해 admission FAIL이다. 따라서 R0 ~ R3는 performance diagnostic으로만 보존한다. `*` 값은 output trajectory/길이가 서로 달라 recipe superiority나 graph/MTP depth speedup으로 해석하지 않는다.

### 7. Ornith 1.5 35B-A3B / 1Cat-vLLM

| Candidate | 설정 | 실행 verdict | 동시요청 | TTFT s | Prefill tok/s | Mean decode | Agg decode | E2E tok/s | Wall s | Output | Peak VRAM MiB<br>GPU0/GPU1 | 5.5 final disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R0 `R0-BASELINE-EAGER-MBT4096` | NVFP4 · E5M2 KV · eager · MBT4096 | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 109.62 | 1456.96 | 8.01 | 11.48 | 9.04 | 282.74 | 2557 | 14765/14765 | REFERENCE_ONLY — superseded by R1 |
| ⭐ R1 `R1-GRAPH-AUTO-MBT4096` | NVFP4 · E5M2 KV · graph auto · MBT4096 | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 108.01 | 1484.15 | 30.51 | 30.32 | 22.16 | 218.77 | 4849 | 14825/14825 | VALIDATED_RECIPE — 2026-09-30 remeasurement |
| R2 `R2-EAGER-MBT8192` | NVFP4 · E5M2 KV · eager · MBT8192 | PASS_C2_ACTIVE | C2 ACTIVE / queue=false | 111.34 | 1142.84 | 9.65 | 17.95 | 11.56 | 298.73 | 3453 | 14753/14753 | CLOSED_NO_QUALIFYING_BENEFIT |

R1의 2026-09-30 동일 설정 [재측정](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001.md)은 A/B 모두 PASS(2915/1934 tokens), C2 active, queue=false, post-health healthy를 충족했다. 따라서 이 재측정을 R1의 현재 authoritative measured result로 사용하고 R1을 5.5 `VALIDATED_RECIPE`로 승격한다. 2026-09-29 [원측정](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260928-001.md)의 Project B FAIL(997 < 최소 1024 tokens)은 historical evidence로 보존한다. 단, graph capture/replay는 두 실행 모두 `UNKNOWN`이므로 이 승격은 **R1 serving configuration의 검증**이며 CUDA Graph 자체의 speedup을 증명한 것으로 해석하지 않는다. R2는 prefill -21.56%, TTFT +1.57%, wall +5.66%로 intended latency 개선을 충족하지 못했다. [현재 review](WBS-5.4.3.4-result-review.md#7-2026-09-30-r1-재측정-addendum) 참조.

## 구동 명령어

아래 명령은 WBS5 frozen plan의 **normalized serving command**를 재사용하기 쉽게 기록한 것이다. 실제 measured raw에는 snapshot 경로, experiment label, `--cidfile` 등 실행 식별용 metadata가 추가된 exact command가 보존돼 있다. 1Cat-vLLM의 `PYTHONPATH`는 현재 repository checkout의 `scripts/runtime_hooks`를 가리키며, 과거 measured snapshot의 절대경로와 byte-for-byte 동일한 문자열이라는 뜻은 아니다.

### 1. Qwen3.8-27B / llama.cpp

#### R0 TARGET b512/ub128

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R1 NGRAM b512/ub128

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type ngram-simple --jinja --reasoning off --metrics --slots --no-warmup
```

#### R2 TARGET b512/ub256

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### 2. Ornith 1.5 9B / llama.cpp — 1GPU×2 + LiteLLM

이 track은 backend 두 개 외에 **LiteLLM gateway가 필수**다. 세 candidate 모두 같은 gateway topology를 사용한다.

Gateway config 예시:

```yaml
model_list:
  - model_name: Ornith-1.5-9B
    model_info: {id: backend-0}
    litellm_params:
      model: openai/Ornith-1.5-9B
      api_base: http://127.0.0.1:18080/v1
      api_key: local-no-key
      max_parallel_requests: 1
      timeout: 1800
      stream_timeout: 1800
      max_retries: 0
  - model_name: Ornith-1.5-9B
    model_info: {id: backend-1}
    litellm_params:
      model: openai/Ornith-1.5-9B
      api_base: http://127.0.0.1:18081/v1
      api_key: local-no-key
      max_parallel_requests: 1
      timeout: 1800
      stream_timeout: 1800
      max_retries: 0
router_settings:
  routing_strategy: least-busy
  num_retries: 0
```

Gateway launch:

```bash
LITELLM_CONFIG=/absolute/path/to/litellm-config.yaml
docker run --rm --pull=never --name v100-test-litellm --label project=v100-llm-test --network host \
  -v "${LITELLM_CONFIG}:/app/config.yaml:ro" \
  ghcr.io/berriai/litellm:v1.101.0 \
  --config /app/config.yaml --host 127.0.0.1 --port 18079
```

#### R0 backend-0

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus device=0 -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R0 backend-1

```bash
docker run --rm --pull=never --name v100-test-18081 --label project=v100-llm-test --gpus device=1 -p 127.0.0.1:18081:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R1 backend-0

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus device=0 -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R1 backend-1

```bash
docker run --rm --pull=never --name v100-test-18081 --label project=v100-llm-test --gpus device=1 -p 127.0.0.1:18081:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R2 backend-0

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus device=0 -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type ngram-simple --jinja --reasoning off --metrics --slots --no-warmup
```

#### R2 backend-1

```bash
docker run --rm --pull=never --name v100-test-18081 --label project=v100-llm-test --gpus device=1 -p 127.0.0.1:18081:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type ngram-simple --jinja --reasoning off --metrics --slots --no-warmup
```

### 3. Ornith 1.5 35B-A3B / llama.cpp

#### R0 TARGET

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R1 native MTP1

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type draft-mtp --spec-draft-n-max 1 --jinja --reasoning off --metrics --slots --no-warmup
```

#### R2 TARGET ub256

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R3 queue4x

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --env CUDA_SCALE_LAUNCH_QUEUES=4x --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### 4. Gemma4 26B-A4B / llama.cpp

#### R0 TARGET

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R1 NGRAM

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type ngram-simple --jinja --reasoning off --metrics --slots --no-warmup
```

#### R2 TARGET b1024

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 1024 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

#### R3 graph-off — 계획 명령, 미실행

```bash
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --env GGML_CUDA_DISABLE_GRAPHS=1 --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### 5. Qwen3.8-27B / 1Cat-vLLM

#### R0 E4M3 eager

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256 \
VLLM_SM70_GDN_DECODE_FLASHQLA=0 \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e4m3 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --enforce-eager --language-model-only --host 127.0.0.1 --port 18080
```

#### R1 E4M3 graph capture — startup FAIL 기록

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256 \
VLLM_SM70_GDN_DECODE_FLASHQLA=0 \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e4m3 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --language-model-only --host 127.0.0.1 --port 18080 --compilation-config '{"cudagraph_capture_sizes":[1]}'
```

#### R2 original FlashQLA prefill — 계획 명령, toolchain BLOCKED

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=1 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256 \
VLLM_SM70_GDN_DECODE_FLASHQLA=0 \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e4m3 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --enforce-eager --language-model-only --host 127.0.0.1 --port 18080
```

#### R3 E5M2 eager

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256 \
VLLM_SM70_GDN_DECODE_FLASHQLA=0 \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --enforce-eager --language-model-only --host 127.0.0.1 --port 18080
```

### 6. Ornith 1.5 9B / 1Cat-vLLM — G0 semantic FAIL 이후 diagnostic

#### R0 MTP1 MBT4096

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.9 --enforce-eager --speculative-config '{"method":"mtp","num_speculative_tokens":1,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

#### R1 MTP1 MBT8192

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 8192 --gpu-memory-utilization 0.9 --enforce-eager --speculative-config '{"method":"mtp","num_speculative_tokens":1,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

#### R2 graph target + MTP1

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.9 --speculative-config '{"method":"mtp","num_speculative_tokens":1,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

#### R3 MTP2 MBT4096

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.9 --enforce-eager --speculative-config '{"method":"mtp","num_speculative_tokens":2,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

### 7. Ornith 1.5 35B-A3B / 1Cat-vLLM

#### R0 eager MBT4096

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-35b-a3b-nvfp4 --served-model-name Ornith-1.5-35B-A3B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.9 --enforce-eager --host 127.0.0.1 --port 18080
```

#### R1 graph-auto MBT4096

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-35b-a3b-nvfp4 --served-model-name Ornith-1.5-35B-A3B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.9 --host 127.0.0.1 --port 18080
```

OpenCode에서 사용하는 현재 서버 기동 명령은 [R1 recipe의 OpenCode용 명령](../reports/recipes/ornith35-onecat-r1.md#현재-opencode용-서버-기동-명령-p520)을 따른다. 위 명령은 WBS5 후보 기록이며 자동 도구 선택 파서가 포함되지 않았다.

#### R2 eager MBT8192

```bash
CUDA_VISIBLE_DEVICES=0,1 \
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
PYTHONPATH=/home/loopwhile/Data/Workspace_VSCode/v100-llm-test/scripts/runtime_hooks \
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-35b-a3b-nvfp4 --served-model-name Ornith-1.5-35B-A3B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 8192 --gpu-memory-utilization 0.9 --enforce-eager --host 127.0.0.1 --port 18080
```

## Final disposition summary

WBS 5.5 최종 상태는 다음과 같다.

- `VALIDATED_RECIPE` 6개: Qwen llama R2, Ornith9 llama R1, Ornith35 llama R1, Ornith35 llama R2, Gemma llama R0, Ornith35 1Cat R1.
- Qwen 1Cat / Ornith9 1Cat track은 `NO ELIGIBLE RECIPE`.
- 미실행 candidate는 Gemma llama R3 (`Gate B NOT_TRIGGERED`)와 Qwen 1Cat R2 (`BLOCKED_BY_HOST_TOOLCHAIN`).
- Qwen llama R1/R2 optional confirm은 frozen dry-plan에는 존재하지만 사용자 결정으로 SKIP됐으며, candidate 수 25개에는 새로운 configuration으로 추가되지 않는다.
- Ornith35 llama R1의 최초 port-conflict `-001`은 infrastructure-invalid `INCONCLUSIVE`; 동일 frozen configuration의 사용자 승인 재실행 `-002`가 authoritative measured evidence다.

관련 문서: [WBS 5.5 final recipes](WBS-5.5-final-recipes.md) · [WBS](WBS.md) · [machine-readable final recipe receipt](../state/wbs5-final-recipes.json).
