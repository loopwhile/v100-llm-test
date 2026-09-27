# WBS-5 로컬 실행 가능성 리뷰 — Ornith 1.5 35B-A3B / 1Cat-vLLM

검토 기준: source inspection snapshot은 로컬 `main` @ `8233d2f46513bbe5e61a72b1aecc39504d1c7044`; 현재 workspace `main`은 `d9501207566fba98663ba861b55c1bacc9aa09ff`이며 그 사이 commit들은 WBS5 리뷰 문서만 변경했다. GitHub `origin/main`도 해당 시점에 `d9501207566fba98663ba861b55c1bacc9aa09ff`였다. 설치 runtime/source/CLI와 모델 receipt를 P520에서 read-only로 확인하고, 서버/model load/CUDA graph capture/추론/VRAM 측정/benchmark는 실행하지 않았다. plan command는 메모리 내에서만 비교했다. historical raw artifacts와 measured reports/plans는 변경하지 않았다.

## A. Environment Receipt

- **Repo:** source inspection branch `main`, HEAD `8233d2f46513bbe5e61a72b1aecc39504d1c7044`; review update branch `main`, HEAD `d9501207566fba98663ba861b55c1bacc9aa09ff`.
- **지정 Python:** P520 `/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python`은 Python 3.12.14.
- **설치 package:** 지정 venv의 distribution metadata는 `1cat-vllm` 1.5.0, 2,525 package file을 보고하고 `vllm` package tree는 해당 venv의 `site-packages/vllm`에 있다. package `WHEEL` tag는 `cp312-cp312-linux_x86_64`; `direct_url.json`은 wheel 경로 `/home/loopwhile/1cat-vllm-wheel/1cat_vllm-1.5.0-cp312-cp312-linux_x86_64.whl`를 가리킨다. `pip` module은 venv에 없어 `pip show`는 실행할 수 없었지만 metadata/API로 receipt를 확인했다.
- **Wheel:** direct-url 경로의 wheel 파일이 존재하며 SHA256은 `2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b`로 `config/runtime-lock.json`의 expected SHA와 일치한다. 이로써 해당 wheel artifact receipt는 확인했지만 설치 tree 전체가 그 wheel에서 변경 없이 생성됐다는 점까지 독립 검증한 것은 아니다.
- **CLI/help:** 지정 Python의 `python -m vllm.entrypoints.openai.api_server --help`에서 `--model`, `--served-model-name`, `--trust-remote-code`, `--dtype`, `--attention-backend`, `--tensor-parallel-size`, `--kv-cache-dtype`, `--max-model-len`, `--max-num-seqs`, `--max-num-batched-tokens`, `--gpu-memory-utilization`, `--enforce-eager` 옵션을 확인했다. `--kv-cache-dtype` help choices에 `fp8_e5m2`가 있다. help 노출은 parser 옵션의 존재를 확인하지만 exact model의 startup/route 동작을 보증하지 않는다.
- **Model receipt:** `config/models/ornith-1.5-35b-a3b.json`은 `ornith-ai/Ornith-1.5-35B-A3B-NVFP4@94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`, `/srv/models/ornith-1.5-35b-a3b-nvfp4`, NVFP4를 기록한다. P520 경로와 파일은 존재한다. 다만 `.sync_complete`는 label `b200-1-35b-checkpoint-4500`, source `/mnt/hicache/models/checkpoint/nvfp4/checkpoint-4500-NVFP4`, destination `/mnt/ceph/c-af57nace6susi9bu/nvfp4_exports/b200-1/checkpoint-4500-NVFP4` 및 manifest SHA를 가리킨다. 추가로 `.cache/huggingface/download/`의 config, index, 세 weight shard 및 `.sync_complete` metadata를 확인했고 모두 고정 revision `94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`를 기록했다. B200 문자열은 해당 revision에서 다운로드된 파일의 내용이며, 이것만으로 local model mismatch를 주장할 수 없다. 다운로드 revision receipt는 일치한다. 이번 검토에서 전체 tensor SHA를 다시 계산한 것은 아니다.
- **Model files/config:** `config.json`은 `model_type=qwen3_5_moe`, `architectures=[Qwen3_5MoeForConditionalGeneration]`; `model.safetensors.index.json`은 94,393 tensor names와 3 shard를 가리킨다. 이는 config shape의 참고 정보이며, checkpoint revision/weight identity를 증명하지 않는다. 모델은 load하지 않았다.
- **P520 runtime environment:** graph/compile 관련 queried variables (`TORCH_COMPILE_DISABLE`, `VLLM_USE_BREAKABLE_CUDAGRAPH`, `VLLM_SM70_*`, `VLLM_DISABLE_COMPILE_CACHE`, `VLLM_COMPILE*`, `CUDA_GRAPH*`)는 shell snapshot에서 설정되지 않았다. Runner는 별도 env를 추가/제거할 수 있으므로 최종 child env는 plan만으로 확정하지 않는다.

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

Warmup: 이 track의 candidate spec은 별도 full-size warmup을 정의하지 않는다. 기존 C2 runner는 server healthy 이후 한 measured batch를 실행하지만 performance workload/candidate별 warmup 정책을 raw config에 기록하는 WBS5 path가 없다. 설치 source `vllm/v1/worker/gpu/cudagraph_utils.py:311-320`는 graph capture 전에 forward warmup 후 capture를 수행한다. 즉 R1 graph capture/compile은 server initialization 중 발생할 수 있어, measured request warmup과 구분되는 startup capture receipt가 필요하다.

## C. Candidate Static Validation

`runtime_launcher.build_plan()`만 호출해 config 기반 command를 메모리에서 생성하고, 허용된 candidate delta를 적용해 비교했다. 서버 호출, model load, CUDA access는 없었다.

| Candidate | CLI valid | Runner expressible | Static config valid | Runtime route source exists | GPU execution still needed |
|---|---|---|---|---|---|
| R0-BASELINE-EAGER-MBT4096 | PARTIAL — P520 help에 exact option names 노출, model/runtime startup 미실행 | PARTIAL — launcher baseline argv는 만들지만 WBS5 workload/ID/report 경로 없음 | PASS — checked-in profile와 task contract 기준 | PASS — eager flag가 argv에 연결됨; model compatibility는 미검증 | YES — route/VRAM/workload 필요 |
| R1-GRAPH-AUTO-MBT4096 | PARTIAL — P520 help에 exact option names 노출, model/runtime startup 미실행 | FAIL — `--enforce-eager` 제거를 선택하는 WBS5 candidate path 없음 | PASS — R0에서 flag 하나 제거한 in-memory delta | PASS — 조건 충족 시 설치 source가 SM70 compile-graph flag를 자동 설정; exact checkpoint route는 미검증 | YES — graph capture/route 필요 |
| R2-EAGER-MBT8192 | PARTIAL — P520 help에 MBT option 노출, model/runtime startup 미실행 | FAIL — MBT candidate override path 없음; runner 기본 4096 유지 | PASS (정적 한정) — align-mode assertion의 `2096 <= 8192` | PASS — scheduler source에 bound assertion 있음; runtime admission/model block size는 startup 미검증 | YES — VRAM/runtime admission 필요 |

R0의 source-config 계획은 model path/revision, TP2, half dtype, E5M2 KV, target-only, `FLASH_ATTN_V100`, max len 131072, max seqs 2, util 0.90, baseline env `VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0`, eager를 표현한다. `runtime_launcher.py:103-119`는 target-only이면 `speculative_config` 인자를 만들지 않는다. P520 `--help`에는 command의 주요 옵션과 `fp8_e5m2` KV choice가 나타난다. Help와 source 검사는 실제 model startup이나 exact-checkpoint compatibility를 입증하지 않는다.

## D. R1 Graph Source Audit

Installed source was inspected under the designated venv's `site-packages/vllm`. The source defines an automatic SM70 Flash-V100 compile-graph path. The behavior is conditional, and exact checkpoint route selection remains unverified because no model was loaded.

| 조사 항목 | 설치 source 관찰 |
|---|---|
| `--enforce-eager` 제거 후 default graph policy | `vllm/config/vllm.py:454,475` sets default `cudagraph_mode=FULL_AND_PIECEWISE`; v1 graph configuration is therefore available when eager is off. |
| SM70 Flash-V100 compile graph and `VLLM_COMPILE` | `vllm/envs.py:304,558` defaults `VLLM_SM70_FLASH_ATTN_V100=True`, graph flag false. In `VllmConfig.__post_init__` (`vllm/config/vllm.py:1500-1512,1574-1605`), CUDA SM70 + Flash-V100 baseline + no compile-disable/no-compile override auto-sets `VLLM_SM70_FLASH_V100_0DOT3_COMPILE_GRAPH=1`. Lines 1620-1647 then select `CompilationMode.VLLM_COMPILE`, `FULL_AND_PIECEWISE`, and no-MTP capture sizes. R1 removes eager and no disabling env was present in the P520 shell snapshot, so this source gate is statically reachable on the designated V100 setup. |
| Compile-cache quality guard | Source has an explicit guard: `vllm/config/vllm.py:1775-1795` auto-sets `VLLM_DISABLE_COMPILE_CACHE=1` unless profiling override is enabled; explicit `=0` is marked diagnostic-only because of observed deterministic greedy token drift. |
| no-MTP capture sizing | `_sm70_nomtp_cudagraph_capture_sizes()` is called by `VllmConfig.__post_init__` at `vllm/config/vllm.py:1645-1655`; task's target-only config has no speculative config, so source follows no-MTP sizing. |
| `FLASH_ATTN_V100` / E5M2 / graph awareness | `vllm/v1/attention/backends/flash_attn_v100.py:479-483` explicitly admits `fp8_e5m2`; `FlashAttnV100MetadataBuilder` declares `AttentionCGSupport.UNIFORM_BATCH` at line 3080. Backend source contains graph metadata paths. This proves a source route exists, not that this checkpoint selects it at runtime. |
| Qwen3.5-MoE graph restriction | `qwen3_5.py` implements the Qwen3.5 MoE model and GDN/Mamba state hooks (e.g. lines 1151-1181); no model-local `cudagraph_mode=NONE` or full/piecewise prohibition was found. Generic source/model config remains the authority; actual route is unverified. |
| SM70 NVFP4/TurboMind | `compressed_tensors_w4a4_nvfp4.py:206-222` allows min capability 70 only when the SM70 TurboMind route/forced Marlin/emulation applies; `_sm70_ops.py` and the same scheme include explicit SM70 NVFP4 QPN2 operations. `compressed_tensors_wNa16.py:229-255` has a separate `sm70_tm.should_prepare_turbomind` dense compressed-uint4 path. These are quantization-specific routes, not proof the target checkpoint maps to them; no source statement found that NVFP4 itself forbids graph capture. |
| Qwen3.5-MoE and Mamba scheduler | Scheduler config assertion in `vllm/config/vllm.py:2930-2944` governs align mode. The model config's GDN/Mamba hooks do not declare a graph prohibition. |
| P520 ambient env snapshot | Queried `TORCH_COMPILE_DISABLE`, `VLLM_USE_BREAKABLE_CUDAGRAPH`, all `VLLM_SM70_*`, `VLLM_DISABLE_COMPILE_CACHE`, `VLLM_COMPILE*`, and `CUDA_GRAPH*` variables were unset in the P520 shell. The runner inherits `os.environ.copy()` then sets its planned values (`runtime_launcher.py:113-118`), so its final child environment still needs to be stored in WBS5 evidence. |

Conclusion: removing `--enforce-eager` can reach both generic FULL_AND_PIECEWISE defaults and the source's conditional SM70 Flash-V100 compile-graph path; the latter automatically enables its quality guard on the baseline described above. Neither conclusion verifies graph capture or the exact Ornith weight/attention/quantization route. Actual route hit remains **NOT VERIFIED UNTIL MEASURED RUN**.

## E. R2 MBT Static Audit

- `runtime_launcher.py:112`는 MBT 4096을 hard-code한다. `run_c2_onecat.py:137-141`의 유일한 MBT 변경은 Qwen 27B에서 2048로 내리는 조건부 override다. Ornith 35B-A3B에는 적용되지 않는다. R2용 8192 override는 없다.
- P520 installed parser source `vllm/engine/arg_utils.py:1399-1401` wires `--max-num-batched-tokens` to scheduler integer config; `--help` exposes the option. Scheduler constraint is explicit in `vllm/config/vllm.py:2930-2944`: in Mamba cache align mode, `block_size <= max_num_batched_tokens`. Existing WBS record documents block_size 2096 and the 2048 failure (`docs/WBS.md:281-290`), so 8192 satisfies that same bound (`2096 <= 8192`). Exact model-derived block size/admission cannot be rechecked without startup.
- R2 diff는 max-num-batched-tokens만 8192로 바꾸므로 max-num-seqs=2, eager, util=0.90, E5M2 KV는 유지된다. 이는 plan-only 비교이며 current runner는 값을 4096으로 낼 것이다.
- 판정: **STATICALLY VALID, RUNTIME VRAM FIT UNVERIFIED**. Installed help/source accept the integer option and the known align bound is satisfied; actual model scheduler admission and GPU memory fit remain unverified. No model-load/VRAM claim is made.

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
2. **MODEL REVISION RECEIPT MATCHED:** config/index/세 weight shard와 `.sync_complete`의 Hugging Face download metadata는 모두 고정 revision과 일치한다. `.sync_complete`의 B200 내부 경로는 revision 불일치 blocker로 취급하지 않는다. 모델 startup과 실제 tensor 사용은 실행하지 않았다.
3. **STARTUP/ROUTE CONFIRMATION PENDING:** P520 Python, 1cat-vllm metadata, direct-url wheel SHA, CLI help 및 relevant source는 확인했다. 그러나 model/server startup은 금지되어 실행하지 않았다. 따라서 exact checkpoint loading, graph capture, quantization/attention dispatch 및 VRAM fit은 미확인이다.
4. **R2 runtime fit pending:** CLI/source는 MBT integer 및 align bound를 확인시켜 주지만 model-derived scheduler admission과 GPU memory fit은 model startup/inference를 금지해 미확인이다.
5. **R1 route pending:** source상 default/SM70 auto graph policy path는 존재한다. 실제 Ornith + E5M2 + Flash-V100 route hit은 측정 전 확정할 수 없다.

새 candidate나 recipe 변경은 제안하지 않는다. MTP/NGRAM/DFlash/다른 MBT/KV/util 설정도 검토 대상에 넣지 않았다.

## H. Final Verdict

- **R0-BASELINE-EAGER-MBT4096 — `BLOCKED_BY_HARNESS`**
- **R1-GRAPH-AUTO-MBT4096 — `BLOCKED_BY_HARNESS`**
- **R2-EAGER-MBT8192 — `BLOCKED_BY_HARNESS`**

세 candidate 모두 exact static command는 생성 가능하지만 현 C2 runner는 WBS5 workload/identity를 연결하지 않는다. P520 runtime metadata/wheel SHA/source/CLI와 model download revision receipt는 확보했다. WBS5 harness 연결과 eventual startup/runtime route 확인이 남아 있으며, measured inference는 실행하지 않았다.
