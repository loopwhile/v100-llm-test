# Qwen3.8-27B / 1Cat-vLLM WBS5 GDN decode static audit — 2026-09-28

판정: **ADD_BASELINE_INVARIANT**. `VLLM_SM70_GDN_DECODE_FLASHQLA=0`은 과거 B200-aligned 128K run에서 관찰된 serving route를 재현하는 공통 invariant(A)다. 생략과 명시적 0은 pinned source에서 같은 설정으로 resolve되지 않는다. 이는 모든 128K decode 성공에 0이 필수라는 인과 증명이나 semantic PASS 선언은 아니다.

검토 시작 main: `606d81f706ca1575dd1ea9b05a11d69aee756ec7`. [정적 source/hash 및 raw receipt](../state/wbs5-qwen-gdn-route-audit.json)에 installed 1Cat-vLLM 1.5.0의 세 파일 SHA, 해당 source line, 과거 로그, 이전/새 plan SHA를 보존했다. P520에서는 설치된 source/metadata만 읽었으며 runtime import, server startup, model load, GPU inference, benchmark를 수행하지 않았다.

## 과거 run과 현재 baseline 비교

대상: `EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001`의 [config.json](../results/raw/EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001/config.json), [planned-config.json](../results/raw/EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001/runtime/planned-config.json), [server log](../results/raw/EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001/runtime/server-0.log)와 [B200 runner](../scripts/run_b200recipe_onecat.py)를 직접 읽고 비교했다. 과거 config/planned config의 command environments는 일치하며 runner는 해당 env를 subprocess에 실제 전달한다.

| Environment | 과거 B200 C1 | 수정 전 WBS5 R0 | 수정 후 WBS5 R0 |
|---|---|---|---|
| `VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL` | 0 | 0 | 0 |
| `VLLM_FLASH_V100_DECODE_PARTITION_SIZE` | 256 | 256 | 256 |
| `VLLM_SM70_GDN_DECODE_FLASHQLA` | 0 | 생략 → source/default 1 | 0 |

Model/artifact는 `/srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4`, HF revision `15d2e47bffe5d8ad23928879f8f7d2f74909e259`; runtime은 pinned 1Cat-vLLM 1.5.0 wheel `sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b`다. 공통 serving 축은 half / FLASH_ATTN_V100 / TP2 / E4M3(R0) / context131072 / seq1 / MBT2048 / memory0.92 / eager(R0) / language-model-only다. [model config](../config/models/qwen3.8-27b.json), [WBS5 contract](../scripts/wbs5_contract.py), [WBS5 runner](../scripts/run_wbs5.py) 및 Qwen R0~R3 dry plans를 비교했다.

과거 `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder` 및 diagnostic sampling(temp1/top_p0.95/top_k20/presence0.15/frequency0.05/seed38)은 복사하지 않았다. 현재 performance/v1, temp0/top_p1/seed520, thinking=false/tool_parser=none, output reserve4096/min1024를 그대로 유지한다.

## Pinned source에서 생략과 0의 차이

- `vllm/envs.py:3251–3256`: `bool(int(os.getenv("VLLM_SM70_GDN_DECODE_FLASHQLA", "1")))`. 기본값은 **1/True**다.
- `vllm/config/vllm.py:1500–1512,1574–1606`: SM70 Flash-V100 baseline에서 env가 없으면 **1**을 auto-set한다. 명시적 0은 덮어쓰지 않는다. eager 모드라고 이 flag가 꺼지는 것은 아니다.
- `qwen_gdn_linear_attn.py:2447,3670–3693`: 명시적 0이면 `_can_use_flashqla_decode`는 device 검사 전에 `env_disabled`로 False를 반환한다. packed decode의 `6179–6223` 분기에서는 exact mixed-QKV fallback (`fused_sigmoid_gating_delta_rule_update_mixed_qkv_out`)을 선택한다.
- 생략하면 FlashQLA decode가 enabled/eligible이며 추가 dtype/layout/state/head128/TP/device/import 조건을 만족할 경우 native FlashQLA 분기로 들어간다. 추가 조건에 따라 같은 fallback을 탈 수도 있으므로 생략 시 항상 다른 kernel이 실행된다고 주장하지 않는다. 하지만 동일 경로가 보장되지 않으므로 KEEP_CURRENT 근거가 성립하지 않는다.

## 과거 로그가 증명하는 범위

대상 server log **167행**, 09-25 16:38:14 Worker_TP0: `SM70 exact mixed-QKV GDN decode route enabled.` **170행**에는 `fused_sigmoid_gating_delta_rule_update_kernel` Triton JIT가 기록돼 있다. literal flag=0 자체는 로그에 출력되지 않지만 config/env 전달 구현과 실제 decode 분기 로그를 함께 보면 과거 mixed-QKV 경로가 관찰된 것은 확인된다. 모든 worker/layer/timestep에서 같은 경로였다는 증명으로 확대하지 않는다.

37행 FlashQLA GDN **prefill** 로그는 decode 증거가 아니다. 169/172행 E4M3 `route=xqa_paged`는 full-attention KV decode 증거이며 GDN recurrent decode와 별도다.

과거 run은 128K decode/기계적 종료를 완료했다. 이후 semantic audit의 **FAIL_OUTPUT**은 유지한다. 이번 변경으로 과거 verdict나 성능 수치를 재해석하지 않는다.

## 도입 시점과 실패/성공 기록

| 기록 | GDN flag | 관찰 |
|---|---|---|
| TARGET C1 20260924-003 | 생략 → auto1 | 로그26행 auto1, 41행 constructor enabled; decode 완료. 이 로그만으로 실제 native kernel hit를 증명하지 않는다. |
| DIAG-REALISTIC 20260925-003 | 생략 → auto1 | 동일 auto1/constructor 로그, decode 완료 이후 repetition/output failure. |
| RECOVERY E5M2 20260925-001 | 0 | `run_recovery_onecat.py`, commit `3f13eaa` (09-25 16:14:05 KST)에서 저장소의 첫 확인 가능한 128K 명시적 0 도입. KV capacity startup 실패로 decode 증거 없음. |
| B200 C1 20260925-001 | 0 | commit `eb3f5da` (09-25 16:40:26 KST)에 유지; 16:38:14 실제 mixed-QKV decode 로그. |
| 이후 B200 C2 | runner에서 0 | saved config에는 override가 빠져 있지만 runner와 로그6591행은 mixed-QKV 경로를 보여준다. 과거 receipt gap은 수정하지 않는다. |

첫 확인 가능한 도입은 이 저장소에 보존된 기록 기준이다. 이전 외부 실험까지 포괄하는 주장은 아니다. flag1에서도 decode 완료 사례가 있으므로 0의 인과적 필수성은 미확정이다. 다만 대상 known-good serving 경로를 재현하기 위한 공통 설정으로 고정해야 한다. 불필요한 explicit default(B)가 아니며, source의 실제 dispatch를 바꾸므로 diagnostic-only(C)로 분류하지 않는다.

## 수정 및 dry-plan 결과

Qwen 1Cat dispatch에만 flag0을 R0~R3 공통으로 추가했다. OFAT delta에는 포함하지 않는다. R1 graph C1 / R2 Original Prefill0→1 / R3 E4M3→E5M2 및 frozen candidate ID/개수/의미는 유지했다. 네 candidate plan과 manifest의 Qwen configuration SHA만 재생성했다. 각 이전/새 normalized config 차이가 해당 env 한 항목뿐이고 argv, workload, candidate 간 delta, readiness status는 동일함을 검사했다.

| Candidate | 이전 normalized config SHA256 | 새 normalized config SHA256 |
|---|---|---|
| R0 | `50b91d5d98c4318ed87ad4ad7c71786c1b6e9f61232cca760af92e61194ed9ac` | `5e09c2a6711b48d9bddf63fc38ff79935d6f94449cd093bbf6c3bcdb2b18f17b` |
| R1 | `4e2de1776139f7290cd414808d2ba1d69e237b13b867982eba6979be59f4ca27` | `e3bd1ebdca0031972417e70432830f015efdaf016ef016371acf3bbda992dd72` |
| R2 | `ab2baf882c2cb03a985180c9f669b901bc70250c6bf72687296782aa5e0efa95` | `02440f20d913d4bbfcabd7369425e43f93efee49ee3864c0705a2032399a6712` |
| R3 | `ad3fb2d853f273e22d8a79743b667bb32ecca9def9e06431fa9c5074a1765361` | `f859c32e9b3553c27994a383c2d42d76e4524a5620e644bcbf92df4630d9946c` |

R0/R1/R3는 STATIC_READY, R2는 기존 BLOCKED_BY_HOST_TOOLCHAIN(nvcc/완전한 toolkit 부재)을 유지한다. input lock은 model/runtime/profile/workload/frozen 문서의 변경이 없고 WBS5 전용 dispatch code를 pin하지 않으므로 변경 대상이 아니다. 새 contract source SHA는 Qwen plans에 기록했다. 다른 여섯 track의 plan/정의/구현과 WBS3, model/runtime pin, 기존 raw/report는 변경하지 않았다.

## 검증 및 남은 runtime receipt

- 관련 pytest: **33 passed, 25 subtests passed**.
- 전체 pytest: **149 passed, 25 subtests passed**.
- `scripts/validate_repo.py`: **Repository contract: PASS**.
- Python AST/JSON validation, 보호 파일/다른 track 보존 검사, `git diff --check`: PASS.
- 테스트는 common invariant 전달, 제거/1로 변경/ambient1 drift 거부, OFAT 불변, source default AST 및 역사 로그 증거를 포함한다.

향후 승인된 startup/measured 단계에서는 각 TP worker의 effective flag, `enable_flashqla_decode`, resolved decode route 및 fallback reason, 실제 GDN kernel hit, graph capture/replay, VRAM fit, R2 Original Prefill hit, R3 E5M2 route/scales, output integrity를 확인해야 한다. 이 정적 audit가 runtime PASS를 대신하지 않는다. R2 toolkit 설치가 필요하다는 기존 승인 대기는 유지하며 이번 audit에서 host 변경을 하지 않았다.

GPU measured inference / server startup / model load / benchmark executed: **NO**. 다음 단계는 ChatGPT pre-run final validation이며 여기서 자동 measured test를 시작하지 않는다.
