# WBS 5.5 — Final recipe publication

Date: 2026-09-30 · **UPDATED — 6 VALIDATED_RECIPES / 5 TRACKS; 2 TRACKS NO ELIGIBLE RECIPE**

**2026-09-30 publication update:** Ornith 35B / 1Cat R1 동일 설정 재측정이 `PASS_C2_ACTIVE`(A/B 모두 mechanical output PASS, C2 active, post-health healthy)로 완료되어 R1을 현재 final recipe로 승격한다. 2026-09-29 원측정 `FAIL_OUTPUT`은 historical evidence로 보존하고 R0는 reference로 내린다. Graph capture/replay는 두 R1 실행 모두 `UNKNOWN`이므로 CUDA Graph 자체의 speedup은 별도로 증명되지 않았다. [후속 review](WBS-5.4.3.4-result-review.md#7-2026-09-30-r1-재측정-addendum).

현재 publication은 기존 7개 track review와 2026-09-30 사용자 요청 R1 재측정을 함께 반영한다. 전체 winner/자동 배포를 선택하지 않으며, final recipe 총수는 R0→R1 교체이므로 6개로 유지한다.

## 최종 레시피

모두 요청당 128K ceiling, 독립 요청 2개의 C2 active, output mechanical PASS 2/2, post-health healthy를 확인했다. 아래 성능은 각 설정의 유효 측정 1회 관찰값이다. 모델별 output 길이가 달라 행 순서를 모델 간 성능 순위로 해석하지 않는다.

| Track / recipe | 용도 | TTFT s | Prefill tok/s | Mean decode tok/s | Aggregate decode tok/s | E2E tok/s | Wall s | Output tokens | Peak VRAM GPU0/GPU1 MiB |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| [qwen-llama R2](../reports/recipes/qwen-llama-r2.md) | LONG_PREFILL_LATENCY_ORIENTED | 679.05 | 264.11 | 5.59 | 4.51 | 3.46 | 1337.27 | 4623 | 13447/14533 |
| [ornith9-llama R1](../reports/recipes/ornith9-llama-r1.md) | LONG_PREFILL_LATENCY_ORIENTED | 139.20 | 912.19 | 43.99 | 80.90 | 16.20 | 173.34 | 2808 | 10945/10945 |
| [ornith35-llama R1](../reports/recipes/ornith35-llama-r1.md) | DECODE_ORIENTED | 833.07 | 182.78 | 17.33 | 5.71 | 3.43 | 1242.84 | 4265 | 12897/13737 |
| [ornith35-llama R2](../reports/recipes/ornith35-llama-r2.md) | LONG_PREFILL_LATENCY_ORIENTED | 670.09 | 229.75 | 15.70 | 7.23 | 4.51 | 1038.99 | 4681 | 13103/12581 |
| [gemma-llama R0](../reports/recipes/gemma-llama-r0.md) | BASELINE | 439.10 | 359.09 | 22.54 | 7.54 | 4.78 | 671.54 | 3213 | 10039/10537 |
| [ornith35-onecat R1](../reports/recipes/ornith35-onecat-r1.md) | GRAPH_AUTO | 108.01 | 1484.15 | 30.51 | 30.32 | 22.16 | 218.77 | 4849 | 14825/14825 |

각 레시피 문서에는 exact repository/revision/local SHA, runtime commit 또는 wheel/image identity, quant/KV/spec, topology/context/batch, 실제 launch command와 환경, gateway config, 요청별 수치, power/temp/clocks, 출력 판정과 제약을 기록했다. [Machine-readable receipt](../state/wbs5-final-recipes.json)는 원본 명령과 정밀 수치, promotion checks 및 근거 파일 SHA256을 보존한다.

## 승격 판단과 제한

- **Qwen llama.cpp R2**: UB256으로 long-prefill/TTFT 개선. Decode는 유지 + 약한 개선 신호이며, WBS7 MTP/GQA2는 별도 후속 범위다.
- **Ornith 9B llama.cpp R1**: 1GPU×2 + 필수 LiteLLM, UB256. 원본 repository 이름은 **UNRESOLVED**로 유지한다. 고정 local GGUF SHA256과 revision receipt 범위에서 승격하며 upstream 다운로드 재현성을 보증하지 않는다.
- **Ornith 35B llama.cpp R1/R2**: native MTP1의 decode 지향 레시피와 UB256의 long-prefill 지향 레시피를 각각 보존한다. MTP1은 TTFT/wall 및 VRAM trade-off가 있으며 두 설정의 결합은 검증하지 않았다.
- **Gemma llama.cpp R0**: TARGET b512/ub128. NGRAM/b1024에서 유효 개선이 없어 baseline을 확정한다. Gate B 미충족으로 graph-off 후보는 미실행이다.
- **Ornith 35B 1Cat R1**: E5M2, graph-auto(`--enforce-eager` 제거), MBT4096, max-num-seqs 2. 2026-09-30 동일 설정 재측정이 A/B output PASS와 C2 active를 충족해 current final recipe로 승격한다. 원측정의 B `FAIL_OUTPUT`은 historical evidence로 남긴다. Graph capture/replay는 `UNKNOWN`이므로 graph 자체의 가속 효과는 검증 범위에 포함하지 않는다. R0는 reference로, MBT8192는 no-benefit으로 유지한다.
- **Qwen 1Cat: NO ELIGIBLE RECIPE**. R0/R3는 QUEUE_ONLY, R1은 compile OOM FAIL_STARTUP, R2는 toolchain BLOCKED 미실행. Queue-only 및 semantic qualification 부재를 C2 recipe로 승격하지 않는다. [5.4.1.5 review](WBS-5.4.1.5-result-review.md).
- **Ornith 9B 1Cat: NO ELIGIBLE RECIPE**. G0 semantic admission FAIL; R0~R3 diagnostic 모두 Project B FAIL_OUTPUT. [5.4.2.6 review](WBS-5.4.2.6-result-review.md).

Performance workload에는 WBS3의 semantic oracle이 없다. 이 publication의 `VALIDATED_RECIPE`는 해당 workload의 serving/mechanical integrity 범위이며 semantic coding 품질 인증을 추가하지 않는다. Aggregate decode는 earliest first token부터 latest end까지의 overlap window metric이고 mean request decode × concurrency와 같지 않다. 단일 screening으로 작은 차이의 통계적 유의성은 주장하지 않는다.

## 7개 track / 25개 candidate 종결 상태

| Track | Candidate ID | Final disposition |
|---|---|---|
| qwen-llama | `Q38-LLAMA-WBS5-R0-TARGET-B512-UB128` | `REFERENCE_ONLY` |
| qwen-llama | `Q38-LLAMA-WBS5-R1-NGRAM-DEFAULT` | `CLOSED_NO_QUALIFYING_BENEFIT` |
| qwen-llama | `Q38-LLAMA-WBS5-R2-TARGET-UB256` | `VALIDATED_RECIPE` |
| ornith9-llama | `TARGET_BASELINE` | `REFERENCE_ONLY` |
| ornith9-llama | `TARGET_UB256` | `VALIDATED_RECIPE` |
| ornith9-llama | `NGRAM_DEFAULT` | `CLOSED_NO_DRAFT_ACTIVITY` |
| ornith35-llama | `ORN35-LLAMA-WBS5-R0-TARGET` | `REFERENCE_ONLY` |
| ornith35-llama | `ORN35-LLAMA-WBS5-R1-MTP1` | `VALIDATED_RECIPE` |
| ornith35-llama | `ORN35-LLAMA-WBS5-R2-UB256` | `VALIDATED_RECIPE` |
| ornith35-llama | `ORN35-LLAMA-WBS5-R3-QUEUE4X` | `CLOSED_NO_MEASURABLE_BENEFIT` |
| gemma-llama | `G4-LCPP-WBS5-R0-TARGET-B512-UB128` | `VALIDATED_RECIPE` |
| gemma-llama | `G4-LCPP-WBS5-R1-NGRAM-DEFAULT-B512-UB128` | `CLOSED_PERFORMANCE_REGRESSION` |
| gemma-llama | `G4-LCPP-WBS5-R2-TARGET-B1024-UB128` | `CLOSED_NO_QUALIFYING_BENEFIT` |
| gemma-llama | `G4-LCPP-WBS5-R3-TARGET-B512-UB128-GRAPHOFF` | `SKIPPED_GATE_B_NOT_TRIGGERED` |
| qwen-onecat | `R0-E4M3-128K-SEMANTIC-BASELINE` | `NO_ELIGIBLE_RECIPE_QUEUE_ONLY` |
| qwen-onecat | `R1-E4M3-128K-CUDAGRAPH-C1` | `CLOSED_FAIL_STARTUP` |
| qwen-onecat | `R2-E4M3-128K-ORIGINAL-FLASHQLA-PREFILL` | `BLOCKED_BY_HOST_TOOLCHAIN_NOT_RUN` |
| qwen-onecat | `R3-E5M2-128K-KV-ROUTE` | `NO_ELIGIBLE_RECIPE_QUEUE_ONLY` |
| ornith9-onecat | `ORN15-9B-1CAT-WBS5-R0-BASELINE` | `NO_ELIGIBLE_RECIPE_G0_FAIL_OUTPUT` |
| ornith9-onecat | `ORN15-9B-1CAT-WBS5-R1-MBT8192` | `NO_ELIGIBLE_RECIPE_G0_FAIL_OUTPUT` |
| ornith9-onecat | `ORN15-9B-1CAT-WBS5-R2-TARGET-GRAPH` | `NO_ELIGIBLE_RECIPE_G0_FAIL_OUTPUT` |
| ornith9-onecat | `ORN15-9B-1CAT-WBS5-R3-MTP2` | `NO_ELIGIBLE_RECIPE_G0_FAIL_OUTPUT` |
| ornith35-onecat | `R0-BASELINE-EAGER-MBT4096` | `REFERENCE_ONLY` — superseded by R1 on 2026-09-30 |
| ornith35-onecat | `R1-GRAPH-AUTO-MBT4096` | `VALIDATED_RECIPE` — authoritative 2026-09-30 remeasurement |
| ornith35-onecat | `R2-EAGER-MBT8192` | `CLOSED_NO_QUALIFYING_BENEFIT` |

미실행 candidate/optional confirm은 검증된 것으로 표시하지 않는다. Qwen R1/R2 optional confirm은 기존 SKIP 결정을 유지한다. Ornith35 llama R1의 측정 전 포트 충돌 -001은 INCONCLUSIVE로 보존하고, 사용자 지정 재실행 -002만 승격 근거로 사용했다.

Gemma4 1Cat은 선행 C1 FAIL_TIMEOUT으로 WBS5 7개 track에 포함되지 않았다. 필수 **v100-skinny** 결과는 WBS1.4의 **FAIL_OOM_MODEL_LOAD**로 유지한다(현재 2×16GB model load 실패, server boot/C1/C2 NOT_REACHED). Non-Qwen skinny는 pinned model contract가 없어 UNSUPPORTED다. 이 제외 상태를 recipe PASS로 대체하지 않는다.

## Frozen contract 및 evidence audit

1. `config/wbs5-input-lock.json`의 전체 고정 파일 hash 일치를 확인했다. 7개 frozen source 문서에서 25개 candidate ID를 대조했다.
2. 저장된 28개 dry-plan instance(25개 후보 + Qwen 반복/optional confirm)를 frozen planner의 normalized invariant 및 OFAT allowlist와 비교했다. 2026-09-30 R1 재측정은 새 candidate가 아니라 기존 frozen R1의 동일 serving delta를 새 experiment ID로 독립 재실행한 후속 측정이다. Serving 설정 변경은 없으며 snapshot별 PYTHONPATH root 차이는 별도로 보존한다.
3. 승격 대상 6건의 measured plan/실제 command를 대조했다. Docker cidfile/name/experiment label은 실행 식별 메타데이터로 분리하고 model/runtime/serving argv 및 환경은 frozen 값과 확인했다. Ornith9 gateway configuration과 distinct backend routing evidence도 확인했다.
4. 측정 전 artifact hash/revision, runtime version/preflight, live tokenizer의 128K budget, 서로 다른 prompt hash, output reserve/minimum, output PASS 2/2, C2 active, post-health, telemetry 보존을 확인했다. Runtime-only graph/route/cache 불확실성은 관측된 수준으로만 기록했다.
5. 기존 개별 report, `results/summary.csv`, `reports/comparison.csv`에 승격 대상 experiment가 각 1회, PASS_C2_ACTIVE로 발행돼 있는지 확인했다. 원본 raw/report/CSV의 verdict를 recipe 상태로 덮어쓰지 않는다.

Workload 파일 byte SHA256은 `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`다. Materialized workload의 `source_manifest_sha256`은 canonical JSON SHA256 `8da23ccbaa8f6334916243199ce3cff0a49979cc7f72d86aa2dca160de3a2824`로, 두 hash의 의미를 구분해 대조했다.

VRAM은 0.5초 간격 sampled peak, power/temp/clocks는 2초 간격 telemetry다. Graph reuse count는 server lifetime 범위라 measured-window hit 수와 동일시하지 않는다. Qwen llama R2의 slot sampler 한계와 log overlap 보정은 해당 레시피와 원본 evidence에 명시했다.

WBS5 publication은 완료됐다. WBS7의 별도 후보는 이 결과에 포함하지 않으며 이 publication을 통해 자동 실행하지 않는다.
