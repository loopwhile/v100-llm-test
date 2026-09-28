# Current execution

## WBS 5 Ornith 1.5 35B llama.cpp measured results publication — 2026-09-29

- 현재 단계: **PARTIAL_MEASURED_RESULTS_PUBLISHED**. 공식 WBS5 performance report/CSV는 총 11건(Qwen llama.cpp 4건, Ornith 1.5 9B llama.cpp 3건, Ornith 1.5 35B llama.cpp 4건)이며 11건 모두 저장된 최종 verdict `PASS_C2_ACTIVE`다.
- Ornith 35B `5.3.3.1` R0, `5.3.3.2` R1 재실행, `5.3.3.3` R2, `5.3.3.4` R3의 유효한 measured raw 4건을 공식 reporter로 report 4개와 `results/summary.csv` / `reports/comparison.csv`에 반영했다. 네 건 모두 두 요청 output PASS, `active_overlap=true`, `queue_only=false`, post-health healthy다.
- R1 첫 시도 `EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-001`은 측정 전 18080 포트 충돌로 `INCONCLUSIVE`; raw만 보존하고 성능 report/CSV에서 제외했다. 사용자 지시로 동일 frozen configuration의 `EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002`를 실행했고 raw의 `runtime/retry-receipt.json` 및 report/CSV에 재실행 출처를 기록했다.
- Ornith 35B R1 MTP counter는 `OBSERVED`: draft 2,426, accepted 1,838, acceptance ratio 0.7576. R0/R1/R2/R3의 성능 비교, 증거 해석 및 final recipe 승격은 **아직 수행하지 않았다**. `5.3.3.5` track result review는 **PENDING**이다.
- Qwen llama.cpp `5.3.1.7`과 Ornith 9B llama.cpp `5.3.2.4` track review도 미완료다. 다음 measured child를 자동 실행하지 않는다.

## WBS 5 recovered measured results publication — 2026-09-28 (historical snapshot)

- WBS 2: **DONE**.
- WBS 3: **DONE**.
- WBS 4: **DONE**.
- WBS 5: llama.cpp 4개 + 1Cat-vLLM 3개, 총 **7개 model/runtime track candidate selection 완료**.
- 7개 frozen candidate plan 문서화 완료.
- `docs/WBS.md`에 7개 frozen plan을 공식 실행계획으로 반영 완료.
- 현재 단계: **PARTIAL_MEASURED_RESULTS_PUBLISHED — Qwen llama.cpp 5.3.1.1~5.3.1.4 4건 + Ornith 1.5 9B llama.cpp 5.3.2.1~5.3.2.3 3건, 총 7건을 공식 reporter로 publication 완료**.
- 현재 상태: Ornith 1.5 9B llama.cpp R0/R1/R2 measured publication까지 완료. 다음 measured child를 자동 실행하지 않으며, Qwen `5.3.1.7`과 Ornith `5.3.2.4` track review/final recipe 승격은 미완료다.
- Qwen 1Cat R2: **BLOCKED_BY_HOST_TOOLCHAIN** (nvcc/개발 toolkit 없음; isolated CUDA12.8 development toolkit host change 승인 대기).
- Ornith9 1Cat R0~R3: **CONDITIONAL_PENDING_GATE — G0**; Gemma llama R3: **CONDITIONAL_PENDING_GATE — Gate B**.
- 준비 당시 검증: 전체 pytest **146 PASS + 25 subtests**, validate_repo **PASS**. 회수 raw의 slot sampler 오류/로그 overlap 보정 및 첫 R0 evidence snapshot 차이는 `docs/WBS.md` 5.3.1에 기록했다.
- 준비 결과: `docs/WBS-5-preparation-readiness.md`; plans: `results/plans/wbs5-preparation-20260928/manifest.json`.
- 이전 Qwen publication 검증: `validate_repo.py` PASS; reporter/harness/WBS5/measurement-policy 관련 pytest **74 PASS + 25 subtests** (격리된 `/tmp` 저장소에서 확인). 원본 checkout에서는 당시 dry-plan 테스트 1개가 이미 회수된 raw 경로의 부재를 가정해 실패했으며, raw나 테스트 코드는 변경하지 않았다. Report/CSV 값 대조 및 raw 144개 파일 SHA256 보존 확인 완료.
- 이번 Ornith 1.5 9B publication 검증: 공식 reporter로 raw 3건에서 report 3개와 `results/summary.csv` / `reports/comparison.csv` 행을 생성했고 `python3 scripts/validate_repo.py` **PASS**를 확인했다.
- 확인된 완료 experiment: Qwen llama.cpp 4건 (`EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-001`, `-002`, `EXP-V100-WBS5-QWEN-LLAMA-R1-PERF-20260928-001`, `EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001`) + Ornith 1.5 9B llama.cpp 3건 (`EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001`, `EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001`, `EXP-V100-ORN15-9B-LLAMA-NGRAM-B512-UB128-1GPU2-C2-PERF-20260928-001`). 총 7건 모두 raw 최종 verdict **PASS_C2_ACTIVE**; report와 summary/comparison 반영 완료. 그 밖의 WBS5 measured child 및 optional confirm은 완료 처리하지 않았다.
- Qwen llama.cpp **5.3.1.5 / 5.3.1.6: SKIP — USER_DECISION** (2026-09-28). R1/R2 optional confirm은 실행하지 않으며, 5.3.1.7 track review는 기존 measured 4건만 대상으로 한다.
- Ornith 1.5 9B llama.cpp **5.3.2.1 / 5.3.2.2 / 5.3.2.3: DONE — PASS_C2_ACTIVE**. 세 run 모두 project-a → backend-0, project-b → backend-1로 distinct routing이 확인됐고 `active_overlap=true`, `backend_active_in_common_decode_window=true`, `queue_only=false`, post-health healthy다. R1 UB256은 R0 대비 TTFT 182.02s → 139.20s, Prefill 697.74 → 912.19 tok/s, Batch Wall 215.90s → 173.34s로 개선됐다. R2 NGRAM은 R0와 유사한 성능이며 speculative counter가 `OBSERVED`이지만 draft/accepted/draft_count 모두 0이라 NGRAM draft activity는 관측되지 않았다. `5.3.2.4` track review는 **PENDING**.
- Ornith R0 최초 구 HEAD attempt는 llama.cpp `/slots`의 `next_token: []`를 처리하지 못한 slot evidence parser 예외로 중단된 **HARNESS_INVALID / INCONCLUSIVE** 실행이다. 해당 attempt는 공식 performance evidence나 CSV/report에 포함하지 않았고, 수정된 harness/fresh snapshot으로 얻은 R0 rerun만 publication했다.
- WBS 6 관련 기존 상태/결과는 아래 기록을 그대로 유지한다.

## WBS 3 authoritative workload reset — 2026-09-25

- User approved redesigning the flawed C2 workload and rerunning **all runnable WBS 3 lanes**, including Qwen3.8 and Ornith 9B.
- Authoritative WBS 3 workload: `workloads/concurrency/v2.json`; semantic oracle: `workloads/concurrency/v2-ground-truth.json`.
- `workloads/concurrency/v1.json` and all existing v1 raw artifacts remain immutable historical evidence.
- v2 uses one seeded defect per project anchor, one-time anchor inclusion, safe `{{SECTION}}`-variant calibration padding, structured 300+ token engineering output, and pre-registered semantic criteria.
- Harness concurrency evidence is now independent of output verdict; output underfill/wrong semantics cannot erase observed `QUEUE_ONLY` or active-overlap topology.
- WBS 3.1 llama.cpp v2 scope: Qwen TARGET/NGRAM; Ornith 9B TARGET/NGRAM/MTP/MTP_NGRAM; Ornith 35B TARGET/NGRAM/MTP/MTP_NGRAM; Gemma4 TARGET/NGRAM/corrected-MTP/corrected-MTP_NGRAM.
- WBS 3.2 1Cat v2 scope: Qwen3.8 B200-aligned E4M3, Ornith 9B MTP1/FP16, Ornith 35B target-only/E5M2. Gemma4 remains ineligible from C1 FAIL_TIMEOUT.
- v100-skinny remains CLOSED/UNSUPPORTED and is not rerun.
- Historical v1 Qwen/Ornith9 C2 results remain diagnostics, not authoritative v2 acceptance.
- No GPU experiment is launched by these design commits. Use fresh experiment IDs for v2.
- Execution runners are now wired for both shared-TP2 families: `scripts/run_c2_llama.py` and `scripts/run_c2_onecat.py`.
- Do not advance to WBS 4/5 until WBS 3 v2 matrix is complete.

## Previous execution record

- WBS 2.1.1 Qwen3.8-27B llama.cpp C1: DONE.
- WBS 2.1.2 Ornith 1.5 9B llama.cpp C1: DONE.
- WBS 2.1.3 Ornith 1.5 35B-A3B llama.cpp C1: DONE.
- WBS 2.1.4 Gemma4 26B-A4B llama.cpp C1: DONE.
- All WBS 2.1 llama.cpp C1 model items are complete.
- WBS 2.2 execution contract is prepared in `docs/WBS-2.2-execution-manifest.md`.
- WBS 2.2 measured runner: `scripts/run_c1_onecat.py`.
- 2.2.1 Qwen3.8 STOCK: CLOSED — 128K CAPACITY PASS / OUTPUT INTEGRITY FAIL. Attempts 002~007 reproduced repetition failure. A later B200-aligned E4M3 diagnostic preserved 128K capacity and completed non-repetitively, but post-hoc semantic audit found that the 280-token answer did not substantiate the requested concrete cross-file/component correctness risk; its raw harness PASS is preserved while publication remains FAIL_OUTPUT.
- 2.2.2 Ornith 9B STOCK: DONE — PASS_C1_128K (EXP-V100-ORN15-9B-1CAT-F16-MTP1-C1-128K-20260924-003; TTFT 165.43s, Decode 8.98 tok/s, Wall 201.64s).
- 2.2.3 Ornith 35B STOCK: DONE — PASS_C1_128K (EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C1-128K-20260924-002; TTFT 62.05s, Decode 10.45 tok/s, Wall 118.88s).
- 2.2.4 Gemma4 26B STOCK: CLOSED — FAIL_TIMEOUT (Bounded Recovery Closed).
  - Historical NVFP4 run: `EXP-V100-GEMMA4-26B-1CAT-F16-TARGET-C1-128K-20260924-002` failed at startup because 1Cat-vLLM 1.5.0 SM70 TurboMind NVFP4 MoE does not support Gemma4 MoE architecture shape (2816, 704, 128, 8) and gelu_pytorch_tanh activation.
  - Revalidation AWQ INT4 initial run: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001` failed at startup (`FAIL_STARTUP`) due to transformers 5.16.1 heterogeneous attention head_dim initialization defect.
  - Bounded Recovery Attempt 1: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-002` — `FAIL_CRASH` (heterogeneous hook fixed all 30 layers; shard loaded 100%; startup healthy; crashed during 128K prefill with Triton CUDA OOM; peak VRAM 15,243 MiB).
  - Bounded Recovery Attempt 2: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-003` — `FAIL_CRASH` (`--language-model-only` disabled vision tower; but `gpu_memory_utilization=0.90` expanded KV cache to 4.78 GiB, leaving 1.13 GiB free VRAM; Triton kernel spilled 10,896 B/thread requiring 1.66 GiB driver local stack, causing `cuLaunchKernel` OOM; peak VRAM 15,253 MiB).
  - Bounded Recovery Attempt 3 (Final): `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-004` — `FAIL_TIMEOUT` (`gpu_memory_utilization=0.80`, `VLLM_SM70_TRITON_ATTN_PREFILL_TILE_SIZE=16`, `SAFE_DEFAULTS=1`; startup healthy, VRAM rock solid at 13,663 MiB with 2.7 GiB headroom; no OOM, no crash, post-health 100% OK; but 128K chunked prefill with 512-dim attention on SM70 took > 1,800s, reaching client HTTP timeout).
- Previous task: WBS 3.2 (1Cat-vLLM STOCK C2 v2) execution complete:
  - 3.2.1 Qwen3.8-27B (`EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C2-128K-20260925-002`): QUEUE_ONLY / FAIL_OUTPUT (Project A passed, Project B failed length/repetition; queue_only confirmed).
  - 3.2.2 Ornith 1.5 9B (`EXP-V100-ORN15-9B-1CAT-F16-MTP1-C2-128K-20260925-003`): PASS_C2_ACTIVE (Peak processing 2.0, resident true, active_overlap true; TTFT 310.90s, Aggregate decode 15.60 tok/s; Project A 865 tok PASS, Project B 1460 tok PASS).
  - 3.2.3 Ornith 1.5 35B-A3B (`EXP-V100-ORN15-35B-1CAT-FP8E5M2-TARGET-C2-128K-20260925-001`): PASS_C2_ACTIVE (Peak processing 2.0, resident true, active_overlap true; TTFT 113.71s, Aggregate decode 9.57 tok/s; Project A 947 tok PASS, Project B 1181 tok PASS).
- Previous task: WBS 3.1 llama.cpp C2 v2 matrix execution complete ([DONE]):
  - 3.1.1 Qwen3.8-27B [DONE]:
    - TARGET (`EXP-V100-Q38-LLAMA-Q80-TARGET-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 925.17s, Aggregate decode 1.83 tok/s, Batch Wall 1,446.44s; Project A 886 tok PASS, Project B 842 tok PASS).
    - NGRAM (`EXP-V100-Q38-LLAMA-Q80-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 925.67s, Aggregate decode 2.16 tok/s, Batch Wall 1,489.30s; Project A 886 tok PASS, Project B 1249 tok PASS; NGRAM draft 288/86 A, 561/117 B).
  - 3.1.2 Ornith 1.5 9B [DONE]:
    - TARGET (`EXP-V100-ORN15-9B-LLAMA-F16-TARGET-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 264.40s, Aggregate decode 9.17 tok/s, Batch Wall 425.82s; Project A 1190 tok PASS, Project B 1402 tok PASS; Peak VRAM 8,235 MiB).
    - NGRAM (`EXP-V100-ORN15-9B-LLAMA-F16-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 264.44s, Aggregate decode 7.76 tok/s, Batch Wall 417.21s; Project A 897 tok PASS, Project B 1235 tok PASS; Peak VRAM 8,311 MiB; NGRAM draft 288/76 A, 350/65 B).
    - MTP (`EXP-V100-ORN15-9B-LLAMA-F16-MTP-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 325.09s, Aggregate decode 7.85 tok/s, Batch Wall 509.80s; Project A 894 tok PASS, Project B 1686 tok PASS, B decode 41.29 tok/s; Peak VRAM 10,009 MiB; MTP draft 1023/552 54.0% A, 1911/1048 54.8% B).
    - MTP_NGRAM (`EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 324.95s, Aggregate decode 6.45 tok/s, Batch Wall 498.39s; Project A 879 tok PASS, Project B 1168 tok PASS, B decode 39.83 tok/s; Peak VRAM 10,071 MiB; draft 1173/558 47.6% A, 1554/747 48.1% B).
  - 3.1.3 Ornith 1.5 35B-A3B [DONE]:
    - TARGET (`EXP-V100-ORN15-35B-LLAMA-Q80-TARGET-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 815.97s, Aggregate decode 3.07 tok/s, Batch Wall 1,183.89s; Project A 917 tok PASS, Project B 1217 tok PASS, B decode 29.91 tok/s; Peak VRAM 12,831 MiB GPU0 / 12,309 MiB GPU1).
    - NGRAM (`EXP-V100-ORN15-35B-LLAMA-Q80-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 816.17s, Aggregate decode 2.83 tok/s, Batch Wall 1,183.06s; Project A 867 tok PASS, Project B 1098 tok PASS, B decode 27.83 tok/s; Peak VRAM 12,831 MiB; draft 312/80 25.6% A, 272/68 25.0% B).
    - MTP (`EXP-V100-ORN15-35B-LLAMA-Q80-MTP-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 857.77s, Aggregate decode 3.50 tok/s, Batch Wall 1,251.11s; Project A 1030 tok PASS, Project B 1566 tok PASS, B decode 34.97 tok/s; Peak VRAM 12,897 MiB GPU0 / 13,737 MiB GPU1; draft 574/455 79.3% A, 888/677 76.2% B).
    - MTP_NGRAM (`EXP-V100-ORN15-35B-LLAMA-Q80-MTP-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 860.09s, Aggregate decode 2.70 tok/s, Batch Wall 1,240.18s; Project A 905 tok PASS, Project B 1065 tok PASS, A decode 29.38 tok/s; Peak VRAM 12,897 MiB GPU0 / 13,737 MiB GPU1; draft 759/445 58.6% A, 858/463 54.0% B).
  - 3.1.4 Gemma4 26B-A4B [DONE]:
    - TARGET (`EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 447.02s, Aggregate decode 4.77 tok/s, Batch Wall 667.36s; Project A 924 tok PASS, Project B 1068 tok PASS; Peak VRAM 10,039 MiB GPU0 / 10,537 MiB GPU1).
    - NGRAM (`EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 457.15s, Aggregate decode 4.86 tok/s, Batch Wall 689.16s; Project A 1066 tok PASS, Project B 1055 tok PASS; Peak VRAM 10,039 MiB GPU0 / 10,607 MiB GPU1; draft 527/186 35.3% A, 528/141 26.7% B).
    - MTP (`EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 458.73s, Aggregate decode 4.66 tok/s, Batch Wall 697.62s; Project A 1066 tok PASS, Project B 1016 tok PASS; Peak VRAM 10,345 MiB GPU0 / 10,981 MiB GPU1; draft 1160/777 67.0% A, 1112/738 66.4% B, overall 66.7%).
    - MTP_NGRAM (`EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001`): **PASS_C2_ACTIVE** (Peak processing 2.0, resident true, active_overlap true; TTFT 462.43s, Aggregate decode 4.59 tok/s, Batch Wall 703.74s; Project A 1058 tok PASS, Project B 1016 tok PASS; Peak VRAM 10,345 MiB GPU0 / 11,051 MiB GPU1; draft 1564/800 51.2% A, 1557/748 48.0% B, overall 49.6%).
- Current status: WBS 4 (Ornith 1.5 9B 1GPU×2 + LiteLLM topology) 전체 평가 완료.
  - 4.1.1 TARGET C1: **`PASS_C1_128K`** (`EXP-V100-ORN15-9B-LLAMA-F16-TARGET-1GPU2-C1-128K-20260926-002`; TTFT 190.01s, Prefill 679.04 tok/s, Decode 43.34 tok/s, Batch Wall 202.08s, Peak VRAM GPU0 10,891 MiB / GPU1 10,769 MiB).
  - 4.1.1 TARGET C2: **`PASS_C2_ACTIVE`** (`EXP-V100-ORN15-9B-LLAMA-F16-TARGET-1GPU2-C2-128K-20260926-001`; TTFT 186.45s, Prefill 692.18 tok/s, Mean Decode 43.51 tok/s, Aggregate Decode 77.40 tok/s, Batch Wall 220.01s, Peak VRAM GPU0 10,893 MiB / GPU1 10,893 MiB).
  - 4.1.2 NGRAM C2: **`PASS_C2_ACTIVE`** (`EXP-V100-ORN15-9B-LLAMA-F16-NGRAM-1GPU2-C2-128K-20260926-001`; TTFT 186.98s, Prefill 690.25 tok/s, Mean Decode 44.31 tok/s, Aggregate Decode 77.66 tok/s, Batch Wall 220.96s, NGRAM 수락률 24.75%, Peak VRAM GPU0 10,895 MiB / GPU1 10,895 MiB).
  - 4.1.3 MTP C2: **`PASS_C2_ACTIVE`** (`EXP-V100-ORN15-9B-LLAMA-F16-MTP-1GPU2-C2-128K-20260926-001`; TTFT 208.55s, Prefill 618.85 tok/s, Mean Decode 51.01 tok/s (+17.2%), Aggregate Decode 75.34 tok/s, Batch Wall 235.74s, MTP 수락률 53.27%, Peak VRAM GPU0 11,903 MiB / GPU1 11,903 MiB).
  - 4.1.4 MTP_NGRAM C2: **`PASS_C2_ACTIVE`** (`EXP-V100-ORN15-9B-LLAMA-F16-MTP-NGRAM-1GPU2-C2-128K-20260926-001`; TTFT 208.74s, Prefill 618.26 tok/s, Mean Decode 49.96 tok/s, Aggregate Decode 79.35 tok/s, Batch Wall 234.89s, Speculative 수락률 45.30%, Peak VRAM GPU0 11,905 MiB / GPU1 11,905 MiB).
  - 4.2.1 STOCK MTP1 C2 (1Cat-vLLM): **`FAIL_STARTUP`** (`EXP-V100-ORN15-9B-1CAT-F16-MTP1-1GPU2-C2-128K-20260926-001`; 1GPU TP1 128K FP16 KV 캐시 필요량 4.68 GiB가 가용 VRAM 2.61 GiB를 초과하여 기동 불가, 최대 시퀀스 한도 ~71.2K로 1GPU 128K 수용 불가 입증 및 CLOSED).
- Conclusion: WBS 4 전체 완료 [DONE]. llama.cpp는 1GPUx2 + LiteLLM topology에서 128K C1/C2 전 레인 완전 통과. 1Cat-vLLM은 현재 exact pinned profile (1Cat-vLLM 1.5.0, Ornith 1.5 9B NVFP4, STOCK MTP1, FP16 KV, TP1, V100 16GB)에서 128K startup 불가 확인 (CLOSED — FAIL_STARTUP). 다음 단계는 WBS 5(최종 서빙 레시피 확정).

## Root-Cause Diagnostic: Qwen3.8-27B 1Cat-vLLM 128K Realistic Workload (2026-09-25)
- Purpose: Distinguish whether Qwen3.8 128K repetition collapse is artifact of synthetic repetition-heavy workload (1,333 duplicate sections) or general 1Cat-vLLM 128K path issue.
- Measured Inference: Exactly 1 run executed (`EXP-V100-Q38-1CAT-FP8E4M3-TARGET-DIAG-REALISTIC-128K-20260925-003`).
- Workload: 116 unique source/test/config/doc files (Python 101, JSON 8, MD 6, Shell 1) across 4 repositories; 0 duplicate sections, no benchmark meta-instructions in context. Post-template prompt tokens: 128,832.
- Hardware / Serving: 2x V100 16GB TP2 shared, KV `fp8_e4m3`, context 131,072, `temperature=0.7`, `top_p=0.8`, `presence_penalty=0.0`, `seed=520`, `thinking=True`, `reasoning_effort="medium"`.
- Results:
  - Hardware Capacity: PASS (128,832 tokens prefill in 739.29s, decode 9.76 tok/s, Peak VRAM 15,287 MiB GPU0/1 symmetric, OOM none, post-health 200 OK).
  - Output Integrity: **FAIL_OUTPUT** (Items 18~26 repeated 5 times in an infinite periodic collapse until 2,048 token length limit).
- Conclusion: The hypothesis that exact duplicate-heavy synthetic padding is a **necessary cause** is rejected because repetition collapse also reproduced on a 116-file diversified snapshot. Broader prompt-composition / ultra-long code-dump effects remain possible. Qwen3.8-specific long-context runtime/checkpoint/KV/kernel interaction hypotheses are strengthened, but no single root cause is proven.
- Note: WBS 2.2.1 verdict remains `CLOSED — 128K CAPACITY PASS / OUTPUT INTEGRITY FAIL` (unchanged). Single measured inference budget exhausted; stopped.

## 128K Recovery Validation: Qwen3.8-27B 1Cat-vLLM E5M2/GDN Triton Path (2026-09-25)
- Purpose: Verify whether combining the historically clean Qwen 1Cat execution path (fp8_e5m2 KV, GDN Triton prefill, VLLM_SM70_GDN_DECODE_FLASHQLA=0, FLASH_ATTN_V100, thinking=false, temp=0, top_p=1, seed=38) with proven 128K capacity settings (--language-model-only, util=0.92, partition 256) recovers 128K output integrity.
- Measured Inference: Exactly 1 run attempted (`EXP-V100-Q38-1CAT-FP8E5M2-TARGET-RECOVERY-C1-128K-20260925-001`).
- Hardware / Serving: 2x V100 16GB TP2 shared, KV `fp8_e5m2`, context 131,072, `temperature=0`, `top_p=1`, `seed=38`, `thinking=False`, `--language-model-only`, `gpu_memory_utilization=0.92`, `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`, `VLLM_SM70_GDN_DECODE_FLASHQLA=0`, `--additional-config '{"gdn_prefill_backend":"triton"}'`.
- Results:
  - Final Verdict: **FAIL_STARTUP** (Capacity: **FAIL_CAPACITY**, Integrity: **NOT_REACHED**).
  - Cause: During engine core initialization profiling, Triton prefill kernel memory overhead reduced available KV cache memory to 1.5 GiB, which is insufficient for 131,072 max_model_len requiring 2.15 GiB (`ValueError: To serve at least one request with the model's max seq len (131072), (2.15 GiB KV cache is needed, which is larger than the available KV cache memory (1.5 GiB). Based on the available memory, the estimated maximum model length is 87808.`). Server exited prematurely before measured inference.
  - Peak VRAM: GPU0 13,987 MiB / GPU1 13,987 MiB during profile crash.
- Conclusion:
  - The E5M2 + GDN Triton prefill candidate is **not capacity-compatible with 128K on 2× V100 16GB** (ceiling is ~87.8K tokens).
  - Existing E4M3 128K capacity PASS evidence remains preserved as an independent configuration (`E4M3 128K = Capacity PASS / Output Integrity FAIL`).
  - E5M2-GDN 128K recovery candidate is closed as `FAIL_STARTUP / FAIL_CAPACITY`.
  - Qwen 1Cat 128K recovery test is concluded as failed. Qwen 1Cat is not eligible for WBS 5 throughput optimization.
- Policy Enforcement: Exactly 1 measured inference completed. All further automatic sweeps, retries, and tuning are strictly STOPPED per policy.

## 128K Recipe Diagnostic: Qwen3.8-27B 1Cat-vLLM B200-Aligned Candidate (2026-09-25)
- Purpose: Test a B200-aligned candidate configuration (reasoning-parser qwen3, tool-call-parser qwen3_coder, default-chat-template-kwargs enable_thinking=false, top_k=20, presence_penalty=0.15) on V100 16GB TP2 E4M3. The raw artifact does not preserve an upstream URL/revision receipt, so 'official' provenance is not independently asserted here.
- Measured Inference: Exactly 1 run executed (`EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001`).
- Hardware / Serving: 2x V100 16GB TP2 shared, KV `fp8_e4m3`, context 131,072, `temperature=1.0`, `top_p=0.95`, `top_k=20`, `presence_penalty=0.15`, `frequency_penalty=0.05`, `thinking=False`, `--language-model-only`, `gpu_memory_utilization=0.92`, `VLLM_FLASH_V100_DECODE_PARTITION_SIZE=256`, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder`, `--default-chat-template-kwargs '{"enable_thinking": false}'`.
- Results:
  - Hardware Capacity: **PASS** (128,834 prompt tokens prefill in 740.60s, decode 9.27 tok/s, Peak VRAM 15,567 MiB GPU0/1, OOM none, post-health 200 OK).
  - Mechanical output integrity: **PASS** for this run (280 tokens, `finish_reason=stop`, no repetition loop/periodic collapse observed).
  - Semantic correctness: **FAIL_OUTPUT**. The answer did not substantiate the requested concrete cross-file/component correctness risk; it only described a generic possible `apply_record` / `stage_artifact` mismatch.
  - Raw harness verdict: `PASS_C1_128K`; authoritative publication verdict after semantic audit: **FAIL_OUTPUT**.
- Conclusion:
  - This run is valid evidence that the tested configuration can hold 128K and can terminate without the earlier repetition collapse in at least one measured execution.
  - It does **not** prove which setting removed repetition, that the effect is repeatable, or that task-level output correctness is recovered.
  - Qwen 1Cat remains **not eligible** for formal C2 promotion or WBS 5 throughput optimization until a user-authorized fresh 128K semantic revalidation passes.

## Gemma4 26B-A4B 1Cat-vLLM AWQ INT4 C1 Revalidation & Bounded Recovery (2026-09-25)
- Purpose: Revalidate Gemma4 26B-A4B on 1Cat-vLLM 1.5.0 using the AWQ INT4 (`compressed-tensors`) artifact (`cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4@18a3c7285c33ee39d3e5e16ee6fb2c18f4955ef9`), followed by up to 3 user-authorized bounded recovery attempts.
- Backend Verification Reality:
  - Dense / mixed-precision linear: `Using MarlinLinearKernel for CompressedTensorsWNA16` and `Using MarlinLinearKernel for mixed-precision linear` (Marlin active).
  - Gemma4 MoE: `Using CompressedTensorsWNA16MoEMethod` (generic MoE, **not** `CompressedTensorsWNA16MarlinMoEMethod`). Past documentation referring to "SM70 Marlin MoE path" was an overstatement and is corrected.
  - Attention backend: `TRITON_ATTN`.
- Execution Sequence & Outcomes (Max 3 retries exhausted):
  1. `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001` — **FAIL_STARTUP**:
     - Model weight loading crashed at 0% shard progress with `AssertionError: Attempted to load weight (torch.Size([512])) into parameter (torch.Size([256]))`.
     - Root cause: `transformers 5.16.1` moved `global_head_dim` into `per_layer_config`, leaving `Gemma4TextConfig` without the global attribute. `gemma4.py` defaulted full-attention layers (5, 11, 17, 23, 29) to `head_dim=256` instead of `512`.
  2. Attempt 1: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-002` — **FAIL_CRASH**:
     - Key modification: Implemented repo-local runtime hook (`scripts/runtime_hooks/sitecustomize.py`) to preserve `global_head_dim=512` and dynamically wrap `Gemma4DecoderLayer.__init__` to instantiate full-attention layers with 512/2 and sliding layers with 256/8.
     - Outcome: All 30 layers correctly instantiated; checkpoint shard 100% loaded (16.20s, 9.85 GiB VRAM); server healthy startup achieved. Measured 128K request sent, but crashed during attention prefill with `RuntimeError: Triton Error [CUDA]: out of memory` in `triton_unified_attention.py:1080` (`kernel_unified_attention`). Peak VRAM: 15,243 MiB.
  3. Attempt 2: `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-003` — **FAIL_CRASH**:
     - Key modification: Enabled `--language-model-only` via `config/models/gemma4-26b-a4b.json`, turning the multimodal vision tower into `StageMissingLayer` and removing multimodal encoder cache.
     - Outcome: Model memory decreased, but with `gpu_memory_utilization=0.90`, vLLM expanded KV cache to 4.78 GiB (294,344 tokens), leaving device free memory still at only 1,131 MiB. Triton attention prefill kernel spilled 10,896 bytes/thread to local memory (`n_local`), requiring 1.66 GiB driver local stack, exceeding the 1.13 GiB free memory and causing `cuLaunchKernel` to throw `Triton Error [CUDA]: out of memory`. Peak VRAM: 15,253 MiB.
  4. Attempt 3 (Final): `EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-004` — **FAIL_TIMEOUT**:
     - Key modification: Decreased `gpu_memory_utilization` to `0.80` (expanding free VRAM headroom to 3.28 GiB while reserving 195,000 KV tokens, well above 128K) and configured SM70 Triton Attention tuning: `VLLM_SM70_TRITON_ATTN_PREFILL_TILE_SIZE=16`, `VLLM_SM70_TRITON_ATTN_SAFE_DEFAULTS=1`.
     - Outcome: Server started cleanly. VRAM usage remained completely stable at 13,663 MiB (2.7 GiB headroom). No OOM, no crash. Both GPUs sustained 100% compute continuously. However, 128K chunked prefill (31 chunks) with 512 head dimension and tile size 16 on SM70 Volta required > 1,800 seconds, exceeding the benchmark adapter HTTP timeout (`terminal_s: 1800.44s`). Post-test server health check confirmed server remained 100% healthy (`post_health: {"healthy": true}`).
- Conclusion:
  - Gemma4 26B-A4B 1Cat-vLLM AWQ INT4 fails to complete C1 128K measured inference within the 1,800s timeout on 2x V100 SXM2 TP2 (`FAIL_TIMEOUT`).
  - All 3 user-authorized bounded recovery retries are exhausted. Per policy and user instruction, no fourth retry will be attempted.
  - Gemma4 1Cat-vLLM remains **not eligible** for C2 capacity testing or WBS 5 throughput optimization.
- Policy Enforcement: Stopped per contract. Raw evidence is preserved under `results/raw/EXP-V100-GEMMA4-26B-1CAT-AWQINT4-F16-TARGET-C1-128K-20260925-001/` through `-004/`.

## WBS 6 CPU+RAM Dual-Resident Feasibility & Preflight (2026-09-26)

- Scope: WBS 6.1 (CPU Docker build), WBS 6.4 (artifact verification), Preflight A/B, and WBS 6.5 (Dual-Resident Startup Gate). 32K measured runs (WBS 6.6) prepared and gated (`[READY]`), requiring explicit `--run-32k-measured` opt-in.
- Models verified:
  - Gemma 4 26B-A4B: `gemma-4-26B-A4B-it-UD-Q6_K_XL.gguf` (23,295,391,456 B, SHA256 `b01ee10a1423c17f9c4384f1fc569726b8782c5403557ff138ceb9468ca49d6b`, `unsloth/gemma-4-26B-A4B-it-GGUF@c099eb48e663fd284577b04978a94ffccb261841`).
  - Ornith 1.5 35B-A3B: `Ornith-1.5-35B-Q4_K_M.gguf` (21,713,463,040 B, SHA256 `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`, `ornith-ai/Ornith-1.5-35B-A3B-GGUF@12393612fd4f730ff5aadc23e9b8f9648aa49ceb`).
- Preflight A/B Comparison (`results/raw/WBS6-PREFLIGHT-AB/preflight_ab_result.json`):
  - P520 Xeon W-2135 native build (`GGML_NATIVE=ON`, `GGML_CUDA=OFF`, single native backend).
  - Comparison on Ornith 35B (760 prompt tokens, 128 completion tokens, 4 threads, cpuset `1,2,3,4`):
    - `b10428` (`885c5bbe`): TTFT 21.67s, Prompt Eval 35.07 tok/s, Decode 10.05 tok/s, Duration 34.33s.
    - `b10775` (`67a17c17`): TTFT 21.61s, Prompt Eval 35.18 tok/s, Decode 10.02 tok/s, Duration 34.29s.
  - Winner: No material CPU regression observed for `b10775` relative to `b10428` in the pinned preflight workload (prompt 35.18 vs 35.07 tok/s, decode 10.02 vs 10.05 tok/s). Pinned image: `p520-cpu-llama:b10775` (`p520-cpu-llama@sha256:8ee3818eee9df3690a64177b976692cffd509972cb31c0907f7136b567a4729b`).
- WBS 6.5 Dual-Resident Startup Gate (`results/raw/WBS6-STARTUP-GATE/startup_gate.json`):
  - Verdict: **`PASS_STARTUP_GATE`**.
  - Server A: `p520-cpu-gemma` (Port 8082, Gemma 4 26B UD-Q6_K_XL, server ctx-size 131,072).
  - Server B: `p520-cpu-ornith` (Port 8083, Ornith 1.5 35B Q4_K_M, server ctx-size 131,072).
  - Both servers simultaneously healthy (`/health` 200 OK).
  - CPU Coexistence: logical CPU IDs 1, 2, 3, 4 (mapped to physical CORE 1, 2, 3, 4); Core 0, 5 & SMT siblings preserved for host OS / GPU serving.
  - GPU VRAM Isolation: CPU-only Docker with no GPU devices passed, `GGML_CUDA=OFF`, `--n-gpu-layers 0`; GPU VRAM allocation = 0.0 MiB, Compute Apps = 0. GPU0/GPU1 serving may exist independently.
  - Memory Evidence & Limits: Host Total 62.56 GiB, Available 31.59 GiB at snapshot. SwapTotal 4,194,300 kB, SwapFree 528 kB (~4GB swap in use). Startup gate proved dual server startup, health, and 0B VRAM isolation; it did not measure `pswpin`/`pswpout`/`pgmajfault` deltas, so absence of swap thrash is unproven at gate time. Due to `mmap`, initial MemAvailable does not guarantee physical RAM headroom once working sets fault in; memory pressure and stability will be measured during 32K request execution.
  - Post-gate cleanup: Both containers cleanly removed after verification per contract.
- Status: WBS 6.1~6.8 [DONE]. WBS 6.9 combined optimized CPU true-4K [READY — NOT EXECUTED].
  - Gemma 4 26B-A4B 32K Serial Request: **`PASS`** (`EXP-P520-CPU-GEMMA4-26B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001`; TTFT 4,927.28s, Prefill 6.44 tok/s, Decode 2.72 tok/s, Wall 5,189.72s, Peak VRAM 0 MiB, SwapUsed delta +14.5 MiB, pswpin +1,704, pswpout +4,466, pgmajfault +8,844, 지속적 swap thrashing 미관찰, Post-health PASS; smaps_rollup 수집 실패로 개별 프로세스 RSS/PSS는 0으로 기록됨).
  - Ornith 1.5 35B-A3B 32K Serial Request: **`PASS`** (`EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-32K-20260926-001`; TTFT 4,160.26s, Prefill 7.63 tok/s, Decode 3.15 tok/s, Wall 4,443.18s, Peak VRAM 0 MiB, SwapUsed delta +12.4 MiB, pswpin +113, pswpout +2,101, pgmajfault +1,433, 지속적 swap thrashing 미관찰, Post-health PASS; smaps_rollup 수집 실패로 개별 프로세스 RSS/PSS는 0으로 기록됨).
  - Verdict: Both models awarded **`PASS_CPU_128K_SERVER_32K_REQUEST_DUAL_RESIDENT`**. 64GB RAM / 4-core CPU envelope에서 두 128K 서버 동시 상주 및 32K 실사용 리서치 워크로드 처리 성공(경미한 swap 증분 외 지속적 thrashing 없음 확인), V100 GPU 서빙 자원 100% 보존 확인.
  - Post-cleanup: 두 컨테이너 `p520-cpu-gemma`, `p520-cpu-ornith` 완전 정리 완료.

## WBS 6.8 CPU prefill batch/ubatch True-2K 결과 및 최종 종결 (2026-09-27)

- 최초 6.8.1 `001~004` (922 tokens)는 legacy short-prompt diagnostic으로 보존됨.
- 신규 True-2K 4-case screening (`EXP-P520-CPU-ORN15-35B-LLAMA-Q80-NGRAM-MOD-C1-2K-20260927-005~008`) 완료.
  - live tokenizer 검증: 네 케이스 모두 정확히 **2,000 prompt tokens** (동일 raw prompt SHA256 `27760d5ac9...`).
  - 결과:

    | Case | ID | `-b` | `-ub` | prompt_tokens | prompt_tps | TTFT | decode_tps | wall_s |
    |:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
    | **A** | 005 | 1024 | 256 | 2,000 | **31.72 tok/s** | 63.05s | 9.28 tok/s | 90.55s |
    | **B** | 006 | 2048 | 512 | 2,000 | 31.32 tok/s | 63.87s | 9.33 tok/s | 91.22s |
    | **C** | 007 | 4096 | 512 | 2,000 | 31.34 tok/s | 63.81s | 9.35 tok/s | 91.12s |
    | **D** | 008 | 4096 | 1024 | 2,000 | 30.64 tok/s | 65.27s | 9.31 tok/s | 92.67s |

  - 판정 및 선정:
    - 최고 prompt eval tps: Case A (31.72 tok/s).
    - 2% tie floor: 31.09 tok/s. Case A, B, C가 동률(±2% 이내). Case D는 30.64 tok/s로 3.4% 느림.
    - ±2% 동률 시 최소 b/ub 우선 정책에 따라 **Case A (`-b 1024 -ub 256`)가 최종 Winner**로 선정됨 (`results/raw/WBS68-TRUE2K-WINNER.json`).
  - 32K 후속 규칙 적용:
    - 사전 정의된 contract에 따라, baseline 대비 2%를 초과 개선하는 non-baseline winner가 부재하므로 불필요한 32K 재실행을 생략하고 6.8을 종결함.
    - 증명된 범위: Xeon W-2135 4-core 조건에서 정확히 2,000-token prompt 기준 b/ub 확대 효과가 관찰되지 않았다. 이 결론은 2K local result이며 4K 이상에 일반화하지 않는다. 실제로 WBS 6.9의 동일 4,086-token / cache_n=0 setup diagnostic에서는 큰 b/ub가 더 높은 prefill throughput을 보였다. WBS 6.6 수치를 CPU의 절대적인 32K prefill ceiling으로도 단정하지 않는다.
- WBS 6 (6.1~6.8) 전체 **[DONE]**.


## WBS 6.9 combined optimized CPU true-4K 결과 (2026-09-27)

- Goal: weight/KV quantization은 그대로 두고 serving-side 최적화들을 한 optimized stack으로 묶어 Ornith 35B Q4_K_M true-4K 성능을 측정하고자 함.
- Image Build: `docker/cpu-optimized/Dockerfile`을 통해 `p520-cpu-llama-opt:b10775` 빌드 성공 (`GGML_BACKEND_DL=ON`, `GGML_CPU_ALL_VARIANTS=ON`, OpenVINO 2026.3.1, OpenBLAS).
- Preflight: `results/raw/WBS69-OPT4K-PREFLIGHT.json` — OpenBLAS 및 OPENVINO0 디바이스 인식 통과 (`openvino_device_visible: true`).
- OpenVINO Execution & Verdict: **`CLOSED — FAIL / INCOMPATIBLE`**
  - Case A (`EXP-P520-CPU-ORN15-35B-OPTSTACK-C1-4K-20260927-001`): 서버 헬스체크 통과 후 4K compile warmup 중 `HTTP 500 / llama_decode ret = -3` 크래시.
  - Root Cause:
    1. `ScatterBase` rank mismatch: Ornith 1.5 35B의 2D KV cache `cache_k_l3 [131072, 512]`에 대해 OpenVINO `translate_set_rows`가 4D updates 텐서를 생성하여 OpenVINO core 검증(`scatter_base.cpp:52`)에서 `rank(data)=2, rank(indices)=1, rank(updates)=4` 위반.
    2. Recurrent/Conv dynamic state inference 실패: SSM/Conv 상태 노드의 동적 차원 추론 실패로 정적 shape 고정 및 shape mismatch 예외 발생.
  - Policy: native-GGML fallback을 거부하고 fail-fast 중단. 하드웨어 읽기 전용 유지, 컨테이너 정리 완료.
  - WBS 6.9 종결: Ornith 1.5 35B 하이브리드 아키텍처는 현재 llama.cpp b10775의 OpenVINO 백엔드와 구조적 비호환이 확인되어 OpenVINO 스택은 closed 처리함.
- OpenBLAS + LTO True-4K Screening (Cases A~D): **`DONE`**
  - OpenBLAS + LTO + Flash Attention + Prompt Cache stack(`p520-cpu-llama-opt:b10775-blas`)으로 최종 accepted matrix `005~008` 완료.
  - 네 케이스 모두 4,071 total prompt tokens / 동일 prompt-prefix hash를 사용했지만 cache_n은 A 1,363 / B 1,107 / C 1,107 / D 595로 달랐다. 따라서 실제 evaluated prompt_n도 2,708 / 2,964 / 2,964 / 3,476으로 다르며 measured prompt TPS 차이를 순수 b/ub 효과로 단독 해석하지 않는다.
  - measured 결과:
    - A 1024/256: 18.48 tok/s, TTFT 146.57s, wall 185.03s.
    - B 2048/512: 21.62 tok/s, TTFT 137.11s, wall 184.30s.
    - C 4096/512: 22.27 tok/s, **TTFT 133.12s(best)**, wall 180.58s.
    - D 4096/1024: **24.69 tok/s(selection winner)**, TTFT 140.78s, **wall 180.10s(best)**.
  - 동일 uncached setup diagnostic(4,086 prompt tokens, cache_n=0, prompt_n=4,086): A 19.91 / B 23.55 / C 23.74 / D **26.02 tok/s**. 이 보조 evidence에서는 D가 A보다 약 30.7% 높고, B→C 차이는 작으며 C→D의 ub 512→1024에서 약 9.6% 상승했다.
  - 결론: 2K에서는 b/ub 확대 효과가 없었지만 4K에서는 context-length-dependent 효과가 관찰되었다. D는 throughput-oriented, C는 cached TTFT-oriented recipe로 구분한다.
  - `+33.6%`는 cache_n이 서로 다른 measured scenario의 관찰 차이이며 순수 b/ub 개선율로 주장하지 않는다.
  - pre-final `001`은 이전 prefix contract에서 completed 후 superseded, `002`는 cache_n 507로 acceptance fail. 따라서 “4회”는 최종 accepted 005~008 matrix를 의미한다.
- WBS 6 전체 **[DONE]**.


## WBS 6.10 optimized CPU true-32K 결과 (2026-09-27)

- Goal: WBS 6.9의 C(`4096/512`) / D(`4096/1024`) 후보가 true-32K에서 실질적인 CPU prefill 가속을 제공하는지 검증.
- measured cache: OFF (`--cache-ram 0 --no-cache-prompt`).
- stack: Ornith 35B Q4_K_M / Q8_0, `p520-cpu-llama-opt:b10775-blas`, OpenBLAS+LTO, FA ON, repack, 4 physical cores, 128K server, ngram-mod, no GPU offload.
- 초기 `...-001`: required harness identity 누락으로 measured submission 전 validation 종료. partial preparation evidence만 보존.
- corrected C32 `EXP-P520-CPU-ORN15-35B-OPTBLAS-C1-32K-20260927-003`: **PASS**.
  - `b=4096 / ub=512`.
  - prompt 31,743 tokens.
  - Prefill **7.3849 tok/s**, TTFT **4,298.53s**, Decode **3.1405 tok/s**, Wall **4,553.92s**, Peak VRAM 0/0 MiB.
  - raw prompt SHA256 `75f3de663d9196805b399c70da3f1dd048629c9fca71b7337f0893b6b4527147`.
- 기존 WBS 6.6 Ornith 32K observed result(31,743 tokens, 7.6303 tok/s, TTFT 4,160.26s, decode 3.1495, wall 4,443.18s) 대비 C32는 prefill -3.22%, TTFT +3.32%, decode -0.28%, wall +2.49%.
  - 단, WBS 6.6(native + dual-resident)과 WBS 6.10(combined optimized + single-server)은 동일 controlled A/B가 아니므로 특정 개별 최적화의 효과로 귀속하지 않는다.
  - 결론 범위: **현재 combined optimized C32 configuration이 기존 32K observed result를 상회하지 못함**.
- runtime progress: cumulative prompt TPS 4K 23.32 → 8K 18.39 → 12K 14.61 → 16K 12.05 → 20K 10.28 → 24K 8.99 → 28K 7.99 → final 약 7.39. 4K 결과의 32K 일반화는 불가.
- `--prio 1` / `--prio-batch 1`: runtime permission denied로 실제 priority 상승 미적용.
- D32 `...-004`: **NOT RUN — INTENTIONALLY STOPPED**. C32 결과 후 추가 장시간 실행의 기대 가치가 낮아 사용자 결정으로 중단.
- D32가 없으므로 C-vs-D full comparison 및 aggregate `WBS610-OPTBLAS-32K-C-VS-D.json`은 생성하지 않음.
- 상세 보고서: `docs/WBS-6.10-execution-report.md`.
- Status: **CLOSED — C32 PASS / C32 DID NOT OUTPERFORM PRIOR 32K OBSERVATION / D32 NOT RUN**.

## Next planned work

- WBS 2: DONE
- WBS 3: DONE
- WBS 4: DONE
- WBS 5: 7개 model/runtime track candidate selection 및 frozen plan 문서화 완료; 공식 WBS integration 완료.
- WBS 5 next: 8A~8D 완료 -> ChatGPT pre-run final validation; measured runs 자동 시작 금지.
- WBS 5 GPU measured runs: NOT STARTED.
- WBS 6.1~6.9: DONE (6.9 OpenVINO CLOSED / OpenBLAS+LTO 4K DONE).
- WBS 6.10: CLOSED — C32 PASS; prior 32K observed result를 상회하지 못했고 D32는 의도적으로 미실행.





