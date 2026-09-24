---
name: benchmark-orchestrator
description: >-
  V100 LLM 벤치마크 테스트 오케스트레이션 스킬.
  사용자가 벤치마크 실험을 실행하거나, 모델 성능을 테스트하거나,
  C1/C2 128K 컨텍스트 용량 검증을 요청할 때 이 스킬을 활성화한다.
  오케스트레이터(메인 에이전트)가 전체 흐름을 관리하고,
  서브에이전트 1개를 호출하여 실제 벤치마크 실행을 위임한다.
---

# V100 LLM Benchmark Orchestrator

이 스킬은 벤치마크 테스트를 **오케스트레이터 + 서브에이전트** 패턴으로 실행한다.

## 역할 분리

### 오케스트레이터 (메인 에이전트 = 너)

- 사용자 요청을 해석하고 실험 파라미터를 결정한다
- 실행 전 상태를 검증한다 (WBS, state/current.md, 기존 결과)
- `benchmark-runner` 서브에이전트를 정의하고 호출한다
- 서브에이전트의 진행 상황을 모니터링한다
- 실험 완료 후 결과를 사용자에게 보고한다
- 오류 발생 시 판단하고 재시도 여부를 결정한다

### 서브에이전트 (Benchmark Runner)

- 실제 벤치마크 라이프사이클을 실행한다
- 서버 기동, 워크로드 캘리브레이션, 측정, 정리를 수행한다
- 결과 JSON을 수집하고 리포트를 생성한다
- 진행 상황과 결과를 오케스트레이터에게 보고한다

---

## 실행 절차

### Step 1: 사전 검증 (오케스트레이터)

사용자의 요청을 받으면, 먼저 다음 파일들을 읽어서 현재 상태를 파악한다:

1. **`state/current.md`** — 현재 프로젝트 진행 상태 및 다음 예정 작업
2. **`docs/WBS.md`** — 전체 작업 분해 구조 및 완료/미완료 상태
3. **`results/summary.csv`** — 기존 완료된 실험 목록
4. **`config/profiles/acceptance-128k.json`** — 합격 기준
5. 해당 모델의 설정 파일: `config/models/<model>.json`
6. **WBS 2.2를 실행할 때는 반드시 `docs/WBS-2.2-execution-manifest.md`** — 이미 확정된 1Cat-vLLM artifact/KV/spec/backend/experiment ID와 stop condition

WBS 2.2에서는 manifest에 이미 기록된 upstream 조사와 configuration 판단을 반복하지 않는다. 실제 host evidence가 manifest와 충돌할 때만 그 충돌을 보고한다.

이 정보를 기반으로:

- 요청된 실험이 WBS에서 어떤 단계에 해당하는지 확인
- 이미 완료된 실험인지 중복 확인
- 실험 ID를 결정 (네이밍 컨벤션 참조)
- 필요한 파라미터를 추출 (모델, 런타임, 레인, 토폴로지, 동시성)

### Step 2: 실험 파라미터 확정 (오케스트레이터)

사용자에게 실험 계획을 요약하여 확인받는다.

**예외:** 사용자가 명시적으로 "WBS 2.2 전체"를 위임한 경우 `docs/WBS-2.2-execution-manifest.md` 자체를 사전 승인된 실행 계획으로 취급한다. 2.2.1~2.2.4 사이에 반복 확인을 요구하거나 configuration을 다시 조사하지 않는다. 단, 실패한 item의 설정을 변경해 재시도하는 것은 별도 사용자 승인이 필요하며, WBS 2.2 밖의 작업은 자동 시작하지 않는다.

일반적인 단일 실험 계획 형식:

```
📋 실험 계획
- 실험 ID: EXP-V100-{MODEL}-{RUNTIME}-{KV}-{SPEC}-{CONCURRENCY}-128K-{DATE}-{SEQ}
- 모델: {model_name}
- 런타임: {runtime}
- 레인: {lane}
- 토폴로지: {topology}
- 동시성: C{n}
- 워크로드: {workload_manifest}
```

### Step 3: 서브에이전트 정의 및 호출 (오케스트레이터)

`define_subagent`로 `benchmark-runner` 서브에이전트를 정의한 후, `invoke_subagent`로 호출한다.

#### 서브에이전트 정의

```
define_subagent:
  name: benchmark-runner
  description: V100 LLM 벤치마크 실험을 실행하는 서브에이전트.
               서버 기동, 워크로드 빌드, 측정, 증거 수집, 리포트 생성을 수행한다.
  enable_write_tools: true
  system_prompt: (아래 '서브에이전트 시스템 프롬프트' 섹션 참조)
```

#### 서브에이전트 시스템 프롬프트

서브에이전트에게 전달할 시스템 프롬프트는 다음 내용을 포함해야 한다:

```
너는 V100 LLM 벤치마크 러너 에이전트다.
오케스트레이터가 전달한 실험 파라미터에 따라 벤치마크를 실행한다.

## 프로젝트 위치
워크스페이스: /home/loopwhile/Data/Workspace_VSCode/v100-llm-test

## 핵심 원칙
1. 하드웨어 읽기 전용: GPU 클럭, 전력 제한, persistence mode를 절대 변경하지 않는다.
2. 측정 정책 준수: warmup 금지, 반복 횟수 1회, 재시도 시 반드시 사유 기록.
3. 모든 증거를 JSON으로 기록한다.
4. 서버가 완전히 정리(cleanup)된 후에만 완료를 보고한다.

## 실행 라이프사이클

### Phase A: 레포 검증
python3 scripts/validate_repo.py 를 실행하여 레포 계약을 검증한다.

WBS 2.2에서는 `docs/WBS-2.2-execution-manifest.md`의 **Execution host and repository flow**를 그대로 따른다:
- Git checkout/closeout은 ThinkPad에서 수행한다.
- measured 1Cat runner는 반드시 `p520-llm`의 `/home/loopwhile/v100-llm-test-wbs22-20260924` snapshot에서 SSH로 실행한다.
- `V100_1CAT_PYTHON=/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python`을 사용한다.
- P520 snapshot에는 `.git`이 없으므로 P520에서 `git pull`을 실행하지 않는다.
- 각 item 뒤 raw directory를 ThinkPad checkout으로 rsync한 뒤 report/WBS/state/Git closeout을 수행한다.

### Phase B: 서버 기동
오케스트레이터가 전달한 파라미터를 기반으로 적절한 러너 스크립트를 실행한다:
- llama.cpp Qwen: python3 scripts/run_c1_qwen.py
- llama.cpp 기타 모델: python3 scripts/run_c1_llama.py
- 1Cat-vLLM STOCK: python3 scripts/run_c1_onecat.py

러너 스크립트에 전달할 인자:
- llama.cpp: `--experiment-id {EXP_ID} --model {model_key} --lane {lane} --port {port}`
- 1Cat-vLLM STOCK: `--experiment-id {EXP_ID} --model {model_key} --port {port}`

WBS 2.2의 exact experiment ID와 model key는 execution manifest를 그대로 사용한다.

### Phase C: 모니터링
실행 중 다음을 주기적으로 확인한다:
- results/raw/{EXP_ID}/runtime/progress.json 의 phase 상태
- GPU 메모리 사용량 (nvidia-smi)
- 서버 로그 (results/raw/{EXP_ID}/runtime/server-0.log)

### Phase D: 결과 수집
실행 완료 후 다음 파일들을 읽고 요약한다:
- results/raw/{EXP_ID}/metrics.json — 핵심 성능 지표
- results/raw/{EXP_ID}/completion.json — 최종 판정
- results/raw/{EXP_ID}/requests.json — 요청별 상세
- results/raw/{EXP_ID}/gpu-peak.json — GPU 피크 사용량

### Phase E: 리포트 생성
P520 raw evidence를 ThinkPad checkout의 `results/raw/{EXP_ID}`로 회수한 뒤:

`python3 scripts/report_experiment.py results/raw/{EXP_ID}`

를 실행하여 Markdown 리포트와 CSV 요약을 생성한다.

### Phase F: 오케스트레이터에 보고
다음 형식으로 결과를 보고한다:

실험 완료 보고
- 실험 ID: {EXP_ID}
- 판정(verdict): {verdict}
- TTFT: {ttft_ms} ms
- Prefill 속도: {prefill_tps} tok/s
- Decode 속도: {decode_tps} tok/s
- Batch Wall Time: {wall_s} s
- Peak VRAM: GPU0 {gpu0_mib} MiB / GPU1 {gpu1_mib} MiB
- 리포트 경로: reports/{model_slug}/{EXP_ID}.md

## 오류 처리
- 서버 기동 실패: progress.json에 기록하고 즉시 오케스트레이터에 보고
- OOM: gpu-peak.json과 서버 로그를 첨부하여 보고
- 타임아웃: 경과 시간과 마지막 상태를 포함하여 보고
- 예상치 못한 오류: 전체 에러 로그를 캡처하여 보고
```

### Step 4: 모니터링 (오케스트레이터)

서브에이전트가 작업 중일 때:

- 서브에이전트의 메시지를 기다린다 (자동 알림)
- 필요 시 `send_message`로 추가 지시를 전달한다
- 장시간 무응답 시 타이머를 설정하여 상태를 확인한다

### Step 5: 결과 보고 (오케스트레이터)

서브에이전트로부터 결과를 수신하면:

1. **결과 검증**: metrics.json, completion.json을 직접 읽어 서브에이전트의 보고와 대조
2. **WBS 업데이트**: docs/WBS.md의 해당 항목 상태를 업데이트
3. **state/current.md 업데이트**: 현재 상태와 다음 작업을 반영
4. **사용자 보고**: 아티팩트로 상세 결과 리포트를 생성하여 전달

보고 형식:

```markdown
## 🏁 벤치마크 결과: {EXP_ID}

| 항목 | 값 |
|------|-----|
| 판정 | {verdict} |
| TTFT | {ttft_ms} ms |
| Prefill | {prefill_tps} tok/s |
| Decode (요청당) | {req_decode_tps} tok/s |
| Decode (집계) | {agg_decode_tps} tok/s |
| E2E Output | {e2e_tps} tok/s |
| Wall Time | {wall_s} s |
| Peak VRAM | GPU0: {gpu0} MiB / GPU1: {gpu1} MiB |

### 리포트
- 상세: [reports/{model_slug}/{EXP_ID}.md](file:///.../reports/{model_slug}/{EXP_ID}.md)
- Raw: [results/raw/{EXP_ID}/](file:///.../results/raw/{EXP_ID}/)
```

### Step 6: 후속 작업 판단 (오케스트레이터)

실험 완료 후:

- **PASS**: 일반 단일 실행 요청이면 다음 항목 진행 여부를 사용자에게 확인한다.
- **FAIL**: 설정을 바꾸는 재시도는 자동 수행하지 않는다.
- **사용자가 WBS 2.2 전체를 명시적으로 위임한 경우**: 현재 item의 결과를 먼저 완전히 closeout한 뒤, manifest에 고정된 다음 독립 item으로 진행할 수 있다. 실패한 item은 설정 변경 없이 종료하며 다음 item의 contract를 재설계하지 않는다.
- **그 외 연속 실행 요청 시**: 다음 실험의 파라미터를 준비하고 Step 2로 돌아간다.

> [!IMPORTANT]
> 명시적인 다중-item 위임이 없는 경우 자동으로 다음 실험을 시작하지 않는다. WBS 2.2 전체 위임도 WBS 2.2 밖으로 확장되지 않는다.

---

## 실험 ID 네이밍 컨벤션

```
EXP-V100-{MODEL}-{RUNTIME}-{KV}-{SPEC}-{CONCURRENCY}-{CONTEXT}-{DATE}-{SEQ}
```

| 필드 | 값 예시 |
|------|---------|
| MODEL | `Q38`, `ORN15-9B`, `ORN15-35B`, `GEMMA4-26B` |
| RUNTIME | `LLAMA`, `1CAT`, `VLLM` |
| KV | `Q80`, `F16`, `FP8` |
| SPEC | `TARGET`, `NGRAM`, `MTP`, `MTP-NGRAM` |
| CONCURRENCY | `C1`, `C2` |
| CONTEXT | `128K` |
| DATE | `YYYYMMDD` (UTC) |
| SEQ | `001`, `002`, ... (시도 번호) |

---

## 모델-런타임-레인 매핑

| 모델 | 런타임 | 가능한 레인 | 러너 스크립트 |
|------|--------|------------|--------------|
| Qwen3.8-27B | llama.cpp | TARGET, NGRAM | `run_c1_qwen.py` |
| Ornith 1.5 9B | llama.cpp | TARGET, NGRAM, MTP, MTP_NGRAM | `run_c1_llama.py` |
| Ornith 1.5 35B-A3B | llama.cpp | TARGET, NGRAM, MTP, MTP_NGRAM | `run_c1_llama.py` |
| Gemma4 26B-A4B | llama.cpp | TARGET, NGRAM, MTP, MTP_NGRAM | `run_c1_llama.py` |
| Qwen3.8 / Ornith 9B / Ornith 35B / Gemma4 26B | 1Cat-vLLM | STOCK | `run_c1_onecat.py` |

---

## 참조 문서

실행 중 다음 문서들을 참고한다:

- [방법론](./../../docs/methodology.md) — 실험 순서, 분류 기준, 증거 규칙
- [런타임 정책](./../../docs/runtime-policy.md) — 런타임 고정 및 격리 규칙
- [런타임 레인](./../../docs/runtime-lanes.md) — CLI 플래그 청사진
- [워크로드 계약](./../../docs/workload-contract.md) — 프롬프트 구성 규칙
- [테스트 매트릭스](./../../docs/test-matrix.md) — 전체 실험 목록
- [WBS](./../../docs/WBS.md) — 작업 진행 상태
- [WBS 2.2 실행 manifest](./../../docs/WBS-2.2-execution-manifest.md) — 1Cat STOCK 사전 확정 contract, experiment ID, gate/stop 규칙

---

## 주의사항

> [!CAUTION]
> - `state/current.md`에 "자동 시작 금지" 지시가 있으면 반드시 준수한다.
> - 이전 테스트 레포(qwen3.8-bench, p520-inference-lab)의 결과를 상속하지 않는다.
> - GPU 하드웨어 설정을 변경하지 않는다 (읽기 전용 모니터링만).
> - 한 번에 하나의 실험만 실행한다 (experiment.lock으로 보장).
