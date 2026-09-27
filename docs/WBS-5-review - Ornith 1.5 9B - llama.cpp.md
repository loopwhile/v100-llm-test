# WBS-5 로컬 실행 가능성 리뷰 — Ornith 1.5 9B / llama.cpp

검토 기준: 작업 체크아웃 `main`의 `f6715e729ea676d6684314760f0b2cb181273661` 및 기존 source/config/plan-only 산출물. 이 리뷰에서는 추론 요청, 서버 기동, 측정 실행, source/config/WBS 작업 문서 변경을 하지 않았다. 후보 계획은 이미 있던 `results/plans/wbs5/`의 plan-only 산출물을 읽어 대조했다.

동결 invariant 대조: model `/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf`, SHA256 `79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480`, Q6_K weights / FP16 KV; llama.cpp build 10775 / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`; V100 SXM2 16GB 두 장 독립 backend; backend별 context 131072 / parallel 1 / unified KV per-slot 131072; FA on, Jinja, reasoning off. plan은 cold-independent 및 `--no-warmup`이며 C2 전 짧은 routing preflight만 둔다. 이 항목들은 source/config/계획 값 대조이며 현재 P520에서 재검증한 결과가 아니다.

## A. 현재 main HEAD

- 로컬 체크아웃: `main` @ `f6715e729ea676d6684314760f0b2cb181273661`.
- GitHub `main` HEAD는 확인 불가. `git ls-remote origin refs/heads/main`은 DNS 오류(`Could not resolve host: github.com`)로 끝났고 GitHub 페이지 열기도 cache miss였다. 따라서 위 커밋이 원격 최신 HEAD라고 단정하지 않는다.

## B. R0 실행 가능성 — `TARGET_BASELINE`

**PASS — source/기존 plan-only 산출물 기준.** GPU 실행 가능성이나 현재 호스트의 pinned image 검증을 뜻하지 않는다.

- 기존 fresh plan: `results/plans/wbs5/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260927-001/runtime/`.
- 후보 ID, workload 경로와 SHA256, exact launch command, runtime contract은 `candidate-plan.json` 및 `planned-config.json`에 보존되어 있다. 완전한 Docker/Gateway 실행 문자열은 `candidate-plan.json`의 `exact_launch_commands` 필드에 있다.
- exact generated commands: [candidate-plan.json](../results/plans/wbs5/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260927-001/runtime/candidate-plan.json) (`exact_launch_commands`).
- 두 backend의 llama-server 설정: image `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`; GPU 각각 `device=0/1`, host port `18080/18081`; model `/model/target.gguf`; `--ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup`.
- 별도 gateway는 LiteLLM `v1.101.0` pinned image, 단일 endpoint `:18079`, least-busy, backend별 `max_parallel_requests=1`, `num_retries=0`으로 생성된다.
- 기존 계획이 기대한 정확한 성능 workload는 `workloads/performance/v1.json` (SHA256 `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`)이다. runner의 `--wbs5-candidate R0 --concurrency 2` 경로가 C2 기본 `concurrency/v2.json` 대신 이를 선택한다.
- 각 후보는 별도 experiment ID의 새 계획 디렉터리에 기록되어 있다. executor는 raw 경로를 `exist_ok=False`로 만들고 harness도 비어 있지 않은 실험 경로를 거부하도록 작성되어 있어 기존 raw 덮어쓰기를 막는다.
- 문제/증거 한계: pinned image의 `--help`와 `--version`은 이번 리뷰에서 재실행하지 않았다. plan 자료에는 build 10775 / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`가 기록되어 있으나, 현재 호스트에서의 image 존재와 실행 증거는 미확인이다.

## C. R1 실행 가능성 — `TARGET_UB256`

**PASS — source/기존 plan-only 산출물 기준.**

- 기존 fresh plan: `results/plans/wbs5/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260927-002/runtime/`.
- R0와 exact backend command diff는 `--ubatch-size 128` → `--ubatch-size 256` 한 곳이다. batch 512, TARGET/spec none, backend GPU/port/context/KV, gateway/workload가 유지된다. 두 backend 모두 같은 단일 값 변경을 갖는다.
- exact generated commands: [candidate-plan.json](../results/plans/wbs5/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260927-002/runtime/candidate-plan.json) (`exact_launch_commands`).
- launcher 자체는 `runtime_launcher.py`에서 batch/ubatch를 512/128로 고정하지만 WBS5 runner가 frozen candidate에 따라 값을 덮어쓴다. `prepare_wbs5_plan.py`는 별도로 exact one-variable diff를 검사한다. ID와 최종 command는 plan 산출물에 보존된다.
- pinned image가 `--ubatch-size`를 받는다는 것은 계획 자료의 help evidence에 기재되어 있다. 이번 세션에서 binary help를 독립 실행해 확인하지 못했으므로 measured 전 host preflight 결과를 받아야 한다.

## D. R2 실행 가능성 — `NGRAM_DEFAULT`

**PASS — source/기존 plan-only 산출물 기준.**

- 기존 fresh plan: `results/plans/wbs5/EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260927-003/runtime/`.
- R0와 exact backend command diff는 `--spec-type none` → `--spec-type ngram-simple` 한 곳이다. batch/ubatch 512/128, topology, KV/context, gateway, workload는 유지된다.
- exact generated commands: [candidate-plan.json](../results/plans/wbs5/EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260927-003/runtime/candidate-plan.json) (`exact_launch_commands`).
- command에 NGRAM size 옵션을 추가하지 않는다. pinned default `size_n=12`, `size_m=48`, `min_hits=1`은 기존 plan의 help/source evidence 필드에 기록되어 있다. 이번 리뷰에서 upstream pinned source 또는 pinned image를 네트워크/실행으로 독립 재검증하지 못했다. 기본값 검증 전에는 R2 measured 진입을 보류해야 한다.
- `runtime_launcher.py`의 NGRAM lane profile은 `--spec-type ngram-simple`만 추가하며 파라미터 override를 하지 않는다. draft/generated/accepted evidence는 benchmark harness가 pre/post backend metric delta에서 수집하도록 되어 있다.

## E. WBS5 runner gap

### 반드시 보강할 사항

1. **pinned CLI 증거의 실제 검증 경로가 약하다.** `runtime_launcher.py:preflight`는 `--help` 텍스트에서 옵션 문자열과 `ngram-simple`의 존재만 확인한다. `--ubatch-size 256` 허용 범위/값 및 NGRAM default `size_n/size_m/min_hits`를 비교하지 않는다. `prepare_wbs5_plan.py`의 `runtime_cli_evidence` 값은 현재 코드상 고정 기재이며 해당 실행에서 help/source를 읽어 자동 생성하지 않는다. measured 전에 exact pinned image help와 commit source를 확인하고 결과를 새 plan/preflight evidence에 보존하는 것이 필요하다.
2. **remote HEAD 미확인.** GitHub DNS가 회복되면 `main` HEAD와 검토 커밋을 확인해야 한다. 이는 코드 변경이 아니라 리뷰 provenance의 미완료 항목이다.

### 선택적으로 보강할 사항

- runner에서 최종 조립된 backend command를 `prepare_wbs5_plan.py` 결과와 직접 비교해 실행 진입 전에 diff를 거부하면 planner와 executor 간 drift 방지가 더 명시적이다. 현재도 planner가 candidate ID/ID 규칙을 검사하고 executor가 candidate 기반으로 workload, lane, batch/ubatch를 정하며 raw 설정에 최종 명령을 기록한다.
- `--help` 검증 시 argument default 외에 실제 전달 후보 값도 체크하면 `ubatch=256` 지원 검증이 명시된다.

### 변경하면 안 되는 사항

- R0/R1/R2 외 candidate 추가, R3 정의, candidate 재정렬/ID 또는 one-variable delta 변경.
- Q6_K artifact/SHA, FP16 KV, V100 GPU mapping, context/parallel/unified KV, pinned llama.cpp/LiteLLM image 및 routing, workload 변경.
- NGRAM parameter override/tuning, graph-disable option, MTP/MTP_NGRAM 후보 추가.
- 기존 WBS2/3/4 호출의 기본 workload/launcher 동작, `results/raw` 보존성 변경.

현재 코드에는 WBS5 전용 `prepare_wbs5_plan.py`와 기존 `run_1gpu_litellm.py --wbs5-candidate` 경로가 모두 있다. 기존 runner에 C2 전용 명시적 candidate override를 추가하고 WBS5 planner에서 재검사하는 구조는 WBS2/3/4 기본 흐름을 보존한다. 별도 WBS5 measured runner를 새로 만드는 것은 필수로 보이지 않는다.

## F. measured inference 전 체크리스트

- [ ] GitHub 원격 `main` HEAD 확인 및 로컬 검토 커밋과 차이 확인.
- [ ] P520에서 정확한 model path/SHA, pinned llama.cpp image digest/build/commit, LiteLLM image/version 확인.
- [ ] pinned `llama-server --help`에서 `--ubatch-size 256`, `ngram-simple`, 기본 NGRAM 12/48/1을 확인하고 evidence로 보존.
- [ ] R0 → R1 → R2 순서로 fresh experiment ID/디렉터리를 쓰고 exact command/workload SHA/후보 ID를 계획 결과와 대조. 기존 raw artifact 경로가 없음을 확인.
- [ ] backend GPU0/GPU1 배정, ctx 131072, parallel 1, unified KV/per-slot 131072, FA/Jinja/reasoning/no-warmup 및 LiteLLM 단일 gateway, least-busy, max-parallel=1, retries=0 확인.
- [ ] C2 직전 max_tokens=16의 짧은 routing preflight만 수행하고 routing-settled admission으로 backend 분배를 증명. full-size warmup 금지.
- [ ] `performance/v1.json`이 mode performance, 독립 Project A/B, context 131072, output 4096/minimum 1024, temperature 0/top_p 1/seed 520, diversified identifiers 계약을 유지하는지 SHA 확인.
- [ ] 출력 integrity, actual tokens, TTFT/prefill/decode/aggregate/end-to-end/batch wall, overlap/queue-only, routing/backend, post-health, power/temp/clocks와 0.5초 VRAM sampling evidence를 저장할 경로 확인.
- [ ] R2의 speculative draft/generated/accepted/acceptance evidence가 pre/post runtime counters에서 수집되는지 확인.
- [ ] candidate별 측정 전후 호스트 사용 중 GPU 프로세스/port 확인. 자동 retry 또는 candidate 변경 금지.

VRAM peak는 `nvidia-smi memory.used`를 0.5초 간격으로 샘플링한다. 샘플 사이의 순간 peak는 놓칠 수 있다. 별도 telemetry loop의 power/temperature/clock 기록은 2초 간격이다.

## G. 최종 판정

**BLOCKED** — source와 기존 plan-only 산출물은 세 frozen command delta 및 workload/identity를 충족한다. 그러나 원격 GitHub `main` HEAD와 pinned binary의 현재 help/default evidence를 이번 실행 환경에서 확인하지 못했다. 위 F의 remote provenance 및 pinned CLI 항목을 완료한 뒤 measured run 전 local validation을 마쳐야 한다. 이 판정은 추론 또는 benchmark를 실행했다는 뜻이 아니다.
