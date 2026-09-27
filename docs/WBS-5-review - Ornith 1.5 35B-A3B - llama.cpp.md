# WBS-5 로컬 실행 가능성 리뷰 — Ornith 1.5 35B-A3B / llama.cpp

검토 범위: source/config 검사 및 in-memory plan-only command 생성. 서버/model load, inference, workload, benchmark는 실행하지 않았다. P520에서 요청된 read-only GPU/topology/image/model checksum/CLI 점검을 수행했으며, 기존 raw/report/plan artifacts는 수정하지 않았다.

## A. 로컬 환경 검증 결과

- Git/source snapshot: `main` @ `775f9a2f1bce8286d5bdd745349ed5d5504fd0a0`, source 검토 시작 시 clean. 최종 검토 parent HEAD는 `8fd5565`이며 그 사이 변경은 리뷰 문서뿐이다. origin/main은 각 push 성공으로 일치 확인했다. 현재 draft는 이 신규 리뷰 파일뿐이다.
- OCI: P520 `docker image inspect` 결과 ID와 RepoDigest 모두 `sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`로 pinned digest와 일치했다.
- CLI: P520 pinned image에 `--gpus all`을 전달한 `llama-server --version`은 `0.3.0-dev (build 10775, commit 67a17c17c)`로 성공했다. `--help`에서 unified KV/per-slot, batch/ubatch, `--spec-type`의 `draft-mtp`, `--spec-draft-n-max`, FA/Jinja/reasoning/metrics/slots/no-warmup을 확인했다. GPU device를 노출하지 않은 최초 호출의 libcuda 오류는 container 실행 설정 문제였고, required CLI support blocker는 해소됐다. 모델 인자는 사용하지 않았다.
- GGUF artifact: P520의 `/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf`가 존재하며 크기는 21,713,463,040 bytes. read-only `sha256sum`은 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`로 config/task의 SHA와 일치했다.
- GPU/topology: P520 `nvidia-smi`에서 Tesla V100-SXM2-16GB 2개, 각 16,384 MiB, driver `580.178.04`, 당시 사용량 각 0 MiB로 확인했다. compute-app query는 GPU process가 없음을 보였다. `CUDA_VISIBLE_DEVICES`는 unset. `nvidia-smi topo -m`은 GPU0↔GPU1 `NODE` (NUMA node 0, CPU affinity 0-11)로 표시했다. `nvidia-smi nvlink -s`는 두 GPU 모두 모든 링크가 inactive라고 보고했다. P2P/NVLink 설정은 바꾸지 않았다. `nvidia-smi` header의 CUDA compatibility version은 13.0이다 (container CUDA userspace 버전과 구분).
- Workspace 자체에는 `nvidia-smi`가 없고 Docker socket도 사용할 수 없었다. 이는 workspace 실행 환경에 대한 사실이며 P520 hardware 상태를 뜻하지 않는다. P520 snapshot과 pinned CLI features를 확인했으며 model startup은 실행하지 않았다.

## B. invariant 일치 여부

| Invariant | 정적 설정 대조 | 로컬 runtime/artifact 확인 |
|---|---|---|
| Repo/revision: `ornith-ai/Ornith-1.5-35B-A3B-GGUF@12393612fd4f730ff5aadc23e9b8f9648aa49ceb` | `config/models/ornith-1.5-35b-a3b.json` 일치 | P520 HF download metadata의 revision 및 SHA receipt가 고정값과 일치 |
| GGUF path/SHA: `/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf`; `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f` | config 일치 | P520 파일 존재, SHA256 일치 |
| Q4_K_M weights / Q8_0 K/V | profile/launcher가 Q8_0 → `q8_0` 설정 | artifact SHA 일치 및 source config 확인; model load 미실행 |
| llama.cpp b10775 / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb` / pinned OCI digest | `config/runtime-lock.json` 일치 | P520 OCI digest 및 version build/commit 일치; GPU passthrough를 사용한 help 성공 |
| TP2 shared; `-ngl all`; layer split 1,1; ctx 262144; parallel 2; unified KV/slot 131072 | `runtime_launcher.py`가 모두 생성 | 실제 startup은 실행하지 않음 |
| FA on, Jinja, reasoning off, metrics, slots, no-warmup | launcher가 모두 생성 | P520 pinned help에서 옵션 지원 확인 |
| MTP R1은 embedded native MTP | `MTP` lane에 `--model-draft` 추가 요건 없음; plan은 target GGUF mount만 함 | source plan상 별도 companion 없음; pinned help에 draft-mtp 지원 |

저장소 자체도 runtime lock을 `bootstrap_pin_requires_fresh_verification`으로 표시한다. 이전 WBS3 성공 evidence는 현재 local binary/image identity를 새로 확인한 receipt가 아니다.

## C. R0~R3 candidate별 launch-plan 검증

`runtime_launcher.build_plan()`으로 `TARGET` 및 `MTP` command를 메모리에서 생성하고 frozen delta만 적용해 비교했다. 다음은 **실행하지 않은 plan-only command**다. 공통 model/image/mount/topology/args는 launcher에서 왔다.

```bash
# R0 — ORN35-LLAMA-WBS5-R0-TARGET
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup

# R1 — ORN35-LLAMA-WBS5-R1-MTP1
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type draft-mtp --spec-draft-n-max 1 --jinja --reasoning off --metrics --slots --no-warmup

# R2 — ORN35-LLAMA-WBS5-R2-UB256
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup

# R3 — ORN35-LLAMA-WBS5-R3-QUEUE4X (required container environment transmission)
docker run --rm --pull=never --name v100-test-18080 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --env CUDA_SCALE_LAUNCH_QUEUES=4x --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

정규화한 diff:

```diff
R0 -> R1:
- --spec-type none
+ --spec-type draft-mtp --spec-draft-n-max 1

R0 -> R2:
- --ubatch-size 128
+ --ubatch-size 256

R0 -> R3:
+ Docker container environment: CUDA_SCALE_LAUNCH_QUEUES=4x
```

각 backend server argv에서 다른 설정은 같다. R1 command에는 별도 `--model-draft`/`--spec-draft-model` 인자와 draft GGUF mount가 없으므로 계획상 embedded native MTP다. R1의 `runtime_lanes.json` 공통 MTP 기본 n-max 3은 model profile의 `mtp_draft_n_max=1`로 launcher가 치환한다.

**R3 전달 gap:** 현재 `runtime_launcher.py`의 llama `command_environments`는 빈 dict이고 `run_c2_llama.py`는 `subprocess.Popen(cmd)`로 Docker를 실행한다. host subprocess의 `CUDA_SCALE_LAUNCH_QUEUES`만 설정해도 Docker container에 자동 전달되지 않는다. 따라서 위 `--env CUDA_SCALE_LAUNCH_QUEUES=4x`는 필요한 planned argv delta이며, 현재 runner가 생성/검증/저장하는 설정은 아니다. P520에서 같은 pinned image의 entrypoint를 `/usr/bin/env`로 바꾸고 `--env CUDA_SCALE_LAUNCH_QUEUES=4x`만 전달한 비추론 호출이 정확한 값을 출력했다. container 전달 자체는 확인됐으며 candidate runner 연결은 미구현이다.

Pinned image digest/build 및 required CLI features는 P520 help/version로 확인했다. 이 확인은 model load, 실제 native MTP route 또는 측정 성능을 보증하지 않는다.

## D. 필요한 WBS5 runner/harness 최소 변경

### Runner

현재 `scripts/run_c2_llama.py`는 `workloads/concurrency/v2.json`에 고정되어 있으며 WBS3 model/lane만 받는다. `scripts/prepare_wbs5_plan.py`와 `run_1gpu_litellm.py`에는 performance/v1 지원이 있지만 각각 Ornith 9B llama.cpp 및 Ornith 9B 1GPU×2 track용이므로 이 Ornith 35B shared-TP2 llama.cpp track에 사용할 수 없다. 따라서 이 track에 맞는 WBS5 performance runner는 **없다**.

가장 작은 안전한 경로는 WBS3 기본값/동작을 보존하는 WBS5 전용 dispatch(또는 전용 runner)로 frozen R0~R3를 명시적으로 처리하는 것이다. 필요한 최소 기능:

1. `workloads/performance/v1.json` 선택 및 SHA, candidate ID/key, frozen exact launch config를 planned/raw config와 report에 기록한다.
2. R0→R1→R2→R3만 허용하고 one-variable delta를 검증한다. R1은 model `mtp_draft_n_max=1`/embedded MTP, R2는 ubatch만 교체, R3는 Docker `--env CUDA_SCALE_LAUNCH_QUEUES=4x`를 추가한다.
3. candidate별 fresh experiment ID와 raw directory exclusive creation을 유지하고 기존 raw를 거부한다. 자동 repetition은 추가하지 않으며 한 run당 repetition 1을 유지한다.
4. C2 performance workload의 4096 output reserve와 minimum 1024/request를 저장 및 acceptance에 연결한다.

### Harness/evidence

기존 `bench_harness.py`는 per-request TTFT/prefill/decode, mean request decode, aggregate decode, end-to-end output TPS, batch wall, actual output/min-output integrity, C2 active/queue/resident, post-health 및 `nvidia-smi` peak sampler를 지원한다. aggregate 산식은 현재대로 유지한다: **total output tokens / (latest request completion − earliest first-token)**. submission부터 끝까지를 쓰는 별도 metric은 `end_to_end_output_tps`다.

- `run_c2_llama.py` telemetry는 power/temp/SM/memory clocks를 2초 간격으로 저장하고 `GPUPeakProbe`는 `memory.used`를 0.5초 간격으로 샘플링한다. VRAM peak는 샘플 사이 순간 peak를 놓칠 수 있다.
- C2 overlap probe는 `/slots`를 확인하지만 `resident_slots()`가 slot 내 `n_prompt_tokens_processed`/`n_past`를 읽어 resident 개수로만 축약한다. 저장된 overlap sample은 `resident_slots` 수치이고 per-slot token-progress timeline이 아니다. WBS5에서는 각 slot ID별 `n_prompt_tokens_processed` (가능하면 `n_past`, `n_decoded`, `is_processing`)를 같은 monotonic timestamp와 함께 JSONL로 남겨야 한다.
- WBS3 Ornith 35B TARGET C2의 기존 raw `requests.json`은 Project A TTFT 약 488.76s / first token, Project B 약 1143.17s / first token을 기록하고, `overlap-evidence.json`은 active overlap은 보였지만 slot-progress 필드 없이 `resident_slots` count만 저장한다. 이를 수정/재해석하지 말고 WBS5에서 prefill serialization을 관찰할 prompt-progress timeline을 추가한다.
- `speculative_metric_delta()`는 draft/accepted/verification counters 계산을 구현했지만 `run_batch()` 호출 조건은 `ngram`이 off가 아닌 경우다. pure MTP R1은 `ngram="off"`이므로 현재 경로에서 MTP draft/accepted/acceptance evidence가 빠진다. 조건을 MTP/speculative lane도 포함하도록 WBS5 호출 경로에서 최소 보강하고 WBS3 동작은 보존해야 한다.

## E. measured inference 전에 남은 blocker

- [x] GitHub/local parent HEAD 관계 확인: 최초 source snapshot은 `775f9a2`; 최신 parent `8fd5565`의 변경은 리뷰 문서뿐이다.
- [x] P520 exact OCI digest, GPU passthrough help/version 및 required CLI features 확인.
- [x] P520에서 model path 존재 및 SHA256 확인: 일치.
- [x] P520 GPU 2개/VRAM/process/driver/CUDA_VISIBLE_DEVICES/topology/NVLink 상태 수집. NVIDIA-SMI CUDA compatibility version 13.0 확인. P2P 설정은 건드리지 않았다.
- [ ] WBS5 R0~R3 runner/plan identity 및 exact command/env diff를 구현/확인하고 R3 container env 전달을 evidence로 남긴다.
- [ ] MTP R1의 draft/accepted/acceptance metric capture를 확인한다.
- [ ] per-slot prompt progress timeline capture를 추가하고 fresh plan-only output에서 schema/경로 확인.
- [ ] `performance/v1.json` workload SHA, independent Project A/B, per request 131072 context / 4096 output reserve / minimum actual 1024 계약을 measured 전에 확인.
- [ ] 한 candidate당 fresh ID/새 raw directory 및 single repetition 확인; 기존 raw overwrite와 automatic repetition 없음 확인.

R0~R3 measured execution 전 local validation 순서는 고정 후보 순서 `R0 -> R1 -> R2 -> R3`다. 여기서는 어떤 inference도 실행하지 않았다.

## F. 최종 verdict

**NOT_READY** — frozen candidate command는 source/config로 계획할 수 있고 정규화한 delta를 대조했다. P520의 main HEAD, pinned OCI digest, model SHA 및 GPU/topology snapshot은 확인했다. Pinned help/version 및 R3 container env 전달 자체는 확인했지만 현재 runner는 concurrency/v2 고정이며 이 track의 WBS5 performance runner가 없다. R3 container env 전달, MTP metric capture, per-slot prompt-progress capture도 보강되어야 한다. 이 verdict는 별도 measured-inference 실행 승인이 아니다.
