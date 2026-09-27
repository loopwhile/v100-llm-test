# WBS-5 로컬 실행 가능성 리뷰 — Ornith 1.5 35B-A3B / 1Cat-vLLM

검토 기준: 로컬 `main` checkout @ `8233d2f46513bbe5e61a72b1aecc39504d1c7044`. 작업 범위는 파일/source/config 및 메모리 내 plan-only command 비교다. 서버, 모델, CUDA graph, 추론, VRAM, benchmark를 실행하지 않았다. 기존 report/artifact는 변경하지 않았다.

## A. Environment Receipt

- **Repo:** 현재 branch `main`, HEAD `8233d2f46513bbe5e61a72b1aecc39504d1c7044`.
- **지정 Python:** `/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python` 및 상위 runtime 경로가 존재하지 않는다. 따라서 그 환경에서 Python/version, installed distribution metadata, package files, CLI/help 또는 source를 읽지 못했다.
- **대체 로컬 Python:** `/usr/bin/python3`, Python 3.12.3. 이 환경에는 `1cat-vllm`, `1cat_vllm`, `vllm` distribution이 설치되지 않았다. 지정 환경의 증거로 대체 사용하지 않았다.
- **Wheel:** `config/runtime-lock.json`의 repository receipt는 1Cat-vLLM 1.5.0, `1cat_vllm-1.5.0-cp312-cp312-linux_x86_64.whl`, expected SHA256 `2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b`라고 기록한다. 지정 runtime 및 wheel 원본이 없어 **wheel SHA provenance: repo receipt only / local wheel file unavailable**. 설치 package tree와 동일하다고 추정하지 않는다.
- **Model receipt:** `config/models/ornith-1.5-35b-a3b.json`은 `ornith-ai/Ornith-1.5-35B-A3B-NVFP4@94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`, `/srv/models/ornith-1.5-35b-a3b-nvfp4`, NVFP4를 기록한다. 이 경로도 현재 filesystem에 없어 local artifact receipt 검증은 못 했다. config는 compatibility가 host startup pending이라고 명시한다.

## B. WBS5 Harness Readiness

WBS 공식 workload는 `workloads/performance/v1.json`이며 2개 독립 Project A/B, context 131072, output reserve 4096, minimum output 1024, temperature 0 / top_p 1 / seed 520, diversified identifiers를 선언한다.

| 확인 사항 | 판정 | 근거 |
|---|---|---|
| WBS5 authoritative workload 지정 | PASS | `docs/WBS.md` §5.2 및 manifest의 `mode=performance`. |
| current 1Cat C2 runner가 performance workload를 읽음 | FAIL | `scripts/run_c2_onecat.py:29,79-90`에서 `WORKLOAD_MANIFEST`가 `workloads/concurrency/v2.json`로 고정되고 그 manifest를 직접 materialize한다. |
| required minimum output 1024 연동 | FAIL | harness의 `worker()`는 case의 `min_output_tokens`를 지원하지만(`scripts/bench_harness.py:400-407`), 현재 C2 runner는 WBS5 manifest를 공급하지 않는다. 현재 runner notes에는 v2의 output reserve 2048/minimum 256이 명시된다. |
| C2 active overlap, TTFT, prefill, mean/aggregate decode, end-to-end, batch wall | PASS — harness capability / FAIL — WBS5 runner wiring | C2 barrier/probe 및 집계는 `scripts/bench_harness.py:182-210,395-418,440-478`에 있다. 올바른 workload/candidate config로 호출하는 WBS5 runner 경로는 찾지 못했다. |
| peak VRAM 및 power/temp/clocks | PASS — harness capability / FAIL — WBS5 runner wiring | GPU peak는 `nvidia-smi memory.used` 0.5초 sampler; 순간 peak를 놓칠 수 있다. C2 lifecycle telemetry query는 power/temp/SM/memory clock을 포함하나 2초 간격이다 (`scripts/run_c2_onecat.py:258-276`, `scripts/bench_harness.py:332-350`). WBS5 결과 경로로 연결하는 runner는 없다. |
| output integrity와 post-health | PASS — generic harness | repetition/empty/control-char 검사와 actual output/minimum 확인은 `scripts/bench_harness.py:19-57,400-407`; post-request health 저장은 `459-480`. 단, performance workload를 현재 1Cat C2 runner가 읽지 않아 WBS5 acceptance evidence가 아니다. |
| fresh candidate ID/config/report, overwrite 방지 | FAIL — WBS5 integration | `run_c2_onecat.py`는 WBS3 model ID/실험 흐름이며 WBS5 candidate key를 받지 않는다. `prepare_wbs5_plan.py`의 frozen set은 별도 Ornith 9B llama.cpp 전용이다. |

**핵심 gap:** 현재 `run_c2_onecat.py`는 C2/v2 workload에 고정되어 있고, Ornith 35B 1Cat-vLLM에 대한 WBS5 candidate selector, `performance/v1.json` 선택, 후보별 exact override/identity가 없다. `run_c1_onecat.py`도 capacity C1 전용이다. 따라서 현재 harness metric capability만으로 WBS5 실행 준비가 되었다고 볼 수 없다.

Warmup: 이 track의 candidate spec은 별도 full-size warmup을 정의하지 않는다. 기존 C2 runner는 server healthy 이후 한 measured batch를 실행하지만 performance workload/candidate별 warmup 정책을 raw config에 기록하는 WBS5 path가 없다. R1에서 graph capture/compile이 언제 일어나는지는 설치 source를 못 봐서 UNKNOWN이다.

## C. Candidate Static Validation

`runtime_launcher.build_plan()`만 호출해 config 기반 command를 메모리에서 생성하고, 허용된 candidate delta를 적용해 비교했다. 서버 호출, model load, CUDA access는 없었다.

| Candidate | CLI valid | Runner expressible | Static config valid | Runtime route source exists | GPU execution still needed |
|---|---|---|---|---|---|
| R0-BASELINE-EAGER-MBT4096 | UNKNOWN — 지정 설치 없음 | PARTIAL — launcher가 baseline command는 만들지만 WBS5 workload/ID/report 경로 없음 | PASS — checked-in profile와 task contract 기준 | UNKNOWN — installed source 없음 | YES — route/VRAM/실제 workload 필요 |
| R1-GRAPH-AUTO-MBT4096 | UNKNOWN — 지정 설치 없음 | FAIL — `--enforce-eager` 제거를 선택하는 WBS5 candidate path 없음 | PASS — R0에서 flag 하나 제거한 in-memory delta | UNKNOWN — installed graph source 없음 | YES — auto policy/실제 route hit 검증 필요 |
| R2-EAGER-MBT8192 | UNKNOWN — 지정 설치 없음 | FAIL — MBT candidate override path 없음; runner 기본 4096 유지 | PASS (정적 한정) — 2096 < 8192이며 다른 config 불변 | UNKNOWN — installed scheduler source 없음 | YES — runtime admission/VRAM fit 필요 |

R0의 source-config 계획은 model path/revision, TP2, half dtype, E5M2 KV, target-only, `FLASH_ATTN_V100`, max len 131072, max seqs 2, util 0.90, baseline env `VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0`, eager를 표현한다. `runtime_launcher.py:103-119`는 target-only이면 `speculative_config` 인자를 만들지 않는다. 다만 pinned CLI가 해당 값들을 받는지는 UNKNOWN이다.

## D. R1 Graph Source Audit

요구된 installed package source는 지정 venv가 없어 접근 불가하다. 체크아웃 내 `scripts/runtime_hooks/sitecustomize.py`는 Transformers/Gemma4 compatibility hook만 다루며 1Cat graph policy를 구현하지 않는다. 검색한 repository source에서도 아래 symbol/logic을 확인할 수 없었다. **미발견은 지원 부재의 증거가 아니다.**

| 조사 항목 | 판정 |
|---|---|
| `VLLM_SM70_FLASH_V100_0DOT3_COMPILE_GRAPH` / SM70 device capability gate / `FULL_AND_PIECEWISE` / `VLLM_COMPILE` | UNKNOWN — pinned package source unavailable |
| `VLLM_DISABLE_COMPILE_CACHE` 및 compile-cache quality guard | UNKNOWN |
| no-MTP CUDA Graph capture-size selection | UNKNOWN |
| `FLASH_ATTN_V100` 및 `fp8_e5m2` graph-aware dispatch | UNKNOWN |
| SM70 NVFP4 TurboMind W4A16 path와 graph 제한 여부 | UNKNOWN |
| Qwen3.5-MoE path가 full/piecewise graph를 금지하는지 | UNKNOWN |
| `--enforce-eager` 제거 시 auto graph policy가 선택될 수 있는지 | UNKNOWN — runner command에 explicit graph-enable 인자는 없고, auto policy 여부는 installed source 확인이 필요 |
| 현재 shell의 `TORCH_COMPILE_DISABLE`, `VLLM_USE_BREAKABLE_CUDAGRAPH`, `VLLM_SM70_*`, `VLLM_DISABLE_COMPILE_CACHE`, `VLLM_COMPILE`, graph 관련 변수 | 이 review shell에서는 해당 변수들이 설정되지 않음. P520 실행 환경은 접근 불가하므로 UNKNOWN |

launcher는 자식 환경을 `os.environ.copy()`한 다음 `CUDA_VISIBLE_DEVICES=0,1`, `VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0`, `PYTHONPATH=scripts/runtime_hooks`를 덮어쓴다 (`runtime_launcher.py:113-118`). graph-disabling 환경을 정리하지 않으므로 P520의 ambient environment는 measured 전에 별도 확인해야 한다. 실제 graph route hit는 요구대로 **NOT VERIFIED UNTIL MEASURED RUN**.

## E. R2 MBT Static Audit

- `runtime_launcher.py:112`는 MBT 4096을 hard-code한다. `run_c2_onecat.py:137-141`의 유일한 MBT 변경은 Qwen 27B에서 2048로 내리는 조건부 override다. Ornith 35B-A3B에는 적용되지 않는다. R2용 8192 override는 없다.
- 저장소의 기존 WBS 기록은 MBT 2048에서 Mamba align `block_size=2096 > 2048`로 startup 실패, MBT 4096에서 C1 pass라고 기술한다 (`docs/WBS.md:281-290`). 주어진 정적 조건과 비교하면 `2096 <= 8192`이므로 동일한 단순 upper-bound 검사는 통과할 크기다. 하지만 installed scheduler source가 없어 `8192`의 실제 parser/admission 동작이나 추가 alignment 조건은 확정할 수 없다.
- R2 diff는 max-num-batched-tokens만 8192로 바꾸므로 max-num-seqs=2, eager, util=0.90, E5M2 KV는 유지된다. 이는 plan-only 비교이며 current runner는 값을 4096으로 낼 것이다.
- 판정: **STATICALLY VALID, RUNTIME VRAM FIT UNVERIFIED**. exact `--max-num-batched-tokens 8192` CLI acceptance도 지정 package 부재로 UNKNOWN. GPU model-load 없이 VRAM fit을 주장하지 않는다.

## F. Exact Command Diff

아래 command는 source/config에서 생성한 최종 candidate 명령 문자열이다. **실행하지 않았다.** 세 command의 환경은 동일하다.

```text
CUDA_VISIBLE_DEVICES=0,1
VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0
PYTHONPATH=<repo>/scripts/runtime_hooks
```

```bash
# R0 — R0-BASELINE-EAGER-MBT4096
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-35b-a3b-nvfp4 --served-model-name Ornith-1.5-35B-A3B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.90 --enforce-eager --host 127.0.0.1 --port 18080

# R1 — R1-GRAPH-AUTO-MBT4096
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-35b-a3b-nvfp4 --served-model-name Ornith-1.5-35B-A3B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.90 --host 127.0.0.1 --port 18080

# R2 — R2-EAGER-MBT8192
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-35b-a3b-nvfp4 --served-model-name Ornith-1.5-35B-A3B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 8192 --gpu-memory-utilization 0.90 --enforce-eager --host 127.0.0.1 --port 18080
```

Normalized exact diffs:

```diff
R0 -> R1:
- --enforce-eager

R0 -> R2:
- --max-num-batched-tokens 4096
+ --max-num-batched-tokens 8192
```

다른 argv와 env 값은 같다. 이 명령은 `runtime_launcher.py`에서만 생성 가능함을 보여 주며, `run_c2_onecat.py` 자체가 R1/R2를 선택한다는 뜻은 아니다.

## G. Blocking Issues

1. **BLOCKED_BY_HARNESS:** Ornith 35B 1Cat C2 runner는 `workloads/concurrency/v2.json`으로 고정되어 있다. WBS5 `performance/v1.json`, frozen candidate ID, exact R1/R2 override를 받는 runner 경로와 plan/report identity가 필요하다. 기존 WBS2/3 runner behavior를 보존하는 명시적 WBS5 dispatch가 필요하다.
2. **NEEDS_LOCAL_RUNTIME_CONFIRMATION:** 지정 Python/installed package/wheel source/model path가 이 실행 환경에 없어 CLI parser, runtime version, package SHA provenance, graph/compile-cache/attention/NVFP4/Mamba scheduler source를 검증하지 못했다. 이 상태를 source support 부재로 단정하지 않는다.
3. **R2 runtime fit pending:** MBT 8192의 CLI/scheduler acceptance는 local package 확인 필요. GPU memory fit은 모델 로드 후 확인할 항목이며 현재 결론에서 제외했다.
4. **R1 route pending:** source/설정에서 graph 정책을 확인하더라도 실제 Ornith + E5M2 + Flash-V100 runtime route hit은 측정 전 확정할 수 없다.

새 candidate나 recipe 변경은 제안하지 않는다. MTP/NGRAM/DFlash/다른 MBT/KV/util 설정도 검토 대상에 넣지 않았다.

## H. Final Verdict

- **R0-BASELINE-EAGER-MBT4096 — `BLOCKED_BY_HARNESS`**
- **R1-GRAPH-AUTO-MBT4096 — `BLOCKED_BY_HARNESS`**
- **R2-EAGER-MBT8192 — `BLOCKED_BY_HARNESS`**

세 candidate 모두 exact static command는 생성 가능하지만 현 C2 runner는 WBS5 workload/identity를 연결하지 않는다. 설치 package 부재는 별도의 local runtime confirmation blocker이며, candidate의 source support 여부를 FAIL로 표시하지 않았다.
