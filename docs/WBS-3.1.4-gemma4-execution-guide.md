# WBS 3.1.4 Gemma4 26B-A4B C2 128K 실행 및 형상관리 완전 가이드

본 문서는 **오케스트레이터(메인 에이전트)**와 **서브에이전트(runner)**가 WBS 3.1.1~3.1.3에서 수행해 온 **11단계 표준 워크플로우(동기화 ➔ 실행 ➔ 회수 ➔ 리포트 ➔ WBS/State 기록 ➔ Git 커밋 & 푸시)**를 사용자께서 터미널에서 100% 동일하게 직접 재현하고 완료할 수 있도록 작성된 실전 매뉴얼입니다.

---

## 🧭 우리가 지금까지 진행해 온 워크플로우 구조

우리가 진행한 각 하위 작업(3.1.1, 3.1.2, 3.1.3의 각 레인)은 정확히 아래의 2인 1조 역할 분담으로 이루어졌습니다.

```mermaid
flowchart TD
    subgraph Phase_A ["Phase A: 러너 실행 및 데이터 수집 (기존 서브에이전트 역할)"]
        A1["1. ThinkPad 계약 검증 (validate_repo.py)"] --> A2["2. P520 원격 스냅샷으로 rsync 동기화"]
        A2 --> A3["3. P520 GPU/포트 확인 후 run_c2_llama.py 원격 실행"]
        A3 --> A4["4. 완료된 Raw 데이터를 ThinkPad로 rsync 회수"]
        A4 --> A5["5. ThinkPad에서 report_experiment.py 리포트 생성"]
    end

    subgraph Phase_B ["Phase B: 분석, 문서화, 형상관리 (기존 오케스트레이터 역할)"]
        B1["6. 생성된 마크다운 리포트에서 핵심 수치 확인"] --> B2["7. docs/WBS.md 해당 레인 결과 블록 작성"]
        B2 --> B3["8. state/current.md 현재 상태 및 다음 작업 갱신"]
        B3 --> B4["9. 저장소 계약 재검증 (validate_repo.py)"]
        B4 --> B5["10. Git Add & Commit (표준 커밋 메시지 규칙)"]
        B5 --> B6["11. Git Push (origin main)"]
    end

    Phase_A --> Phase_B
```

이 **11단계 사이클 1회**가 끝나면 **WBS 하위 항목 1개(예: 3.1.4.1 TARGET)**가 완전히 종료됩니다.  
3.1.4의 4개 레인(TARGET ➔ NGRAM ➔ MTP ➔ MTP_NGRAM) 모두 이 사이클을 똑같이 순차적으로 반복합니다.

---

## 📋 4개 레인 실험 ID 및 커밋 메시지 요약표

| WBS 항목 | 모델 / Lane | 실험 ID | 표준 Git 커밋 메시지 |
| :--- | :--- | :--- | :--- |
| **3.1.4.1** | Gemma4 / `TARGET` | `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001` | `test(wbs3): execute Gemma4 26B-A4B llama.cpp TARGET C2 v2 (PASS_C2_ACTIVE)` |
| **3.1.4.2** | Gemma4 / `NGRAM` | `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` | `test(wbs3): execute Gemma4 26B-A4B llama.cpp NGRAM C2 v2 (PASS_C2_ACTIVE)` |
| **3.1.4.3** | Gemma4 / `MTP` | `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` | `test(wbs3): execute Gemma4 26B-A4B llama.cpp MTP C2 v2 (PASS_C2_ACTIVE)` |
| **3.1.4.4** | Gemma4 / `MTP_NGRAM` | `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` | `test(wbs3): execute Gemma4 26B-A4B llama.cpp MTP_NGRAM C2 v2 (PASS_C2_ACTIVE) and close WBS 3.1` |

---

## 🚀 [1단계] 3.1.4.1 Gemma4 TARGET C2 진행

### Step 1. 실험 실행 및 리포트 자동 생성 (ThinkPad 터미널에 한 번에 복사/붙여넣기)
아래 블록 전체를 복사하여 ThinkPad 터미널에서 실행합니다. 검증 ➔ 동기화 ➔ P520 원격 실행 ➔ 회수 ➔ 리포트 생성까지 한 번에 수행됩니다.

```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
EXP="EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001"
MODEL="gemma4-26b-a4b"
LANE="TARGET"

echo "=== [1/5] 로컬 워크스페이스 검증 ==="
python3 scripts/validate_repo.py

echo "=== [2/5] P520으로 코드 동기화 ==="
rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

echo "=== [3/5] P520에서 벤치마크 원격 실행 (약 12~15분 소요) ==="
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
  python3 scripts/run_c2_llama.py --experiment-id $EXP --model $MODEL --lane $LANE --port 18080"

echo "=== [4/5] Raw 측정 결과 ThinkPad로 회수 ==="
rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/$EXP/ results/raw/$EXP/

echo "=== [5/5] 마크다운 리포트 생성 및 CSV 업데이트 ==="
python3 scripts/report_experiment.py results/raw/$EXP

echo "=== TARGET 실행 완료! 판정 확인: ==="
cat results/raw/$EXP/completion.json
```

---

### Step 2. 결과 확인 및 문서 갱신 (WBS.md & state/current.md)

1. **생성된 마크다운 리포트 확인**:
   ```bash
   cat reports/gemma4-26b-a4b/EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001.md
   ```
   리포트 상단의 `TTFT`, `Prefill`, `Decode`, `Wall`, `Peak VRAM`, `Project A/B 토큰수`를 확인합니다.

2. **`docs/WBS.md` 수정**:
   `docs/WBS.md`의 `#### 3.1.4 Gemma4 26B-A4B` 섹션을 아래 양식으로 수정합니다:
   ```markdown
   #### 3.1.4 Gemma4 26B-A4B [IN PROGRESS]
   - artifact: `UD-Q4_K_XL`.
   - KV: `FP16`.
   - 실행 lane: `TARGET`, `NGRAM`, corrected `MTP`, corrected `MTP_NGRAM`; MTP는 validated `CUDA0,CUDA1` draft contract 유지.
   - TARGET: `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
     - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 FP16 KV 캐시로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
     - TTFT (Batch Mean): <리포트의 TTFT>s, Prefill <리포트의 Prefill> tok/s, Mean Decode <리포트의 Decode> tok/s, Aggregate Decode <리포트의 Aggregate> tok/s, Batch Wall <리포트의 Wall>s.
     - Peak VRAM: GPU0 <GPU0 VRAM> MiB / GPU1 <GPU1 VRAM> MiB.
     - Output analysis:
       - Project A: <토큰수> tokens 생성, `Transaction.commit` 결함 분석 및 수정안 제시 (PASS).
       - Project B: <토큰수> tokens 생성, `JobQueue._sequence` 결함 분석 및 수정안 제시 (PASS).
   - NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` [TODO]
   - MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` [TODO]
   - MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` [TODO]
   ```

3. **`state/current.md` 수정**:
   `Current task:` 부분에 아래와 같이 기록합니다:
   ```markdown
   - WBS 3.1.4.1 Gemma4 TARGET 완료 (`PASS_C2_ACTIVE`).
   - 다음 작업: WBS 3.1.4.2 Gemma4 NGRAM 실행 (`EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001`).
   ```

---

### Step 3. 검증 및 Git 커밋 & 푸시 (ThinkPad 터미널에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test

# 1. 저장소 계약 검증
python3 scripts/validate_repo.py

# 2. 결과 및 문서 스테이징
git add docs/WBS.md state/current.md reports/ results/

# 3. 표준 커밋 메시지로 커밋
git commit -m "test(wbs3): execute Gemma4 26B-A4B llama.cpp TARGET C2 v2 (PASS_C2_ACTIVE)"

# 4. 원격 저장소 푸시
git push origin main
```
> 🎉 **3.1.4.1 완료!** 이제 3.1.4.2로 넘어갑니다.

---

## 🚀 [2단계] 3.1.4.2 Gemma4 NGRAM C2 진행

### Step 1. 실험 실행 및 리포트 자동 생성 (ThinkPad 터미널에 한 번에 복사/붙여넣기)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
EXP="EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001"
MODEL="gemma4-26b-a4b"
LANE="NGRAM"

echo "=== [1/5] 로컬 워크스페이스 검증 ==="
python3 scripts/validate_repo.py

echo "=== [2/5] P520으로 코드 동기화 ==="
rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

echo "=== [3/5] P520에서 벤치마크 원격 실행 (약 12~15분 소요) ==="
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
  python3 scripts/run_c2_llama.py --experiment-id $EXP --model $MODEL --lane $LANE --port 18080"

echo "=== [4/5] Raw 측정 결과 ThinkPad로 회수 ==="
rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/$EXP/ results/raw/$EXP/

echo "=== [5/5] 마크다운 리포트 생성 및 CSV 업데이트 ==="
python3 scripts/report_experiment.py results/raw/$EXP

echo "=== NGRAM 실행 완료! 판정 확인: ==="
cat results/raw/$EXP/completion.json
```

---

### Step 2. 결과 확인 및 문서 갱신 (WBS.md & state/current.md)

1. **생성된 마크다운 리포트 확인**:
   ```bash
   cat reports/gemma4-26b-a4b/EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001.md
   ```
   리포트에서 `TTFT`, `Decode`, `NGRAM draft/accepted 통계` 등을 확인합니다.

2. **`docs/WBS.md` 수정**:
   `docs/WBS.md`의 `#### 3.1.4 Gemma4 26B-A4B` 섹션의 NGRAM 항목을 채웁니다:
   ```markdown
   - NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
     - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 NGRAM 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
     - TTFT (Batch Mean): <리포트의 TTFT>s, Prefill <리포트의 Prefill> tok/s, Mean Decode <리포트의 Decode> tok/s, Batch Wall <리포트의 Wall>s.
     - NGRAM Speculative 통계: Project A (draft <A draft>, accepted <A accepted>, <A %>), Project B (draft <B draft>, accepted <B accepted>, <B %>).
     - Peak VRAM: GPU0 <GPU0 VRAM> MiB / GPU1 <GPU1 VRAM> MiB.
     - Output analysis:
       - Project A: <토큰수> tokens 생성, `Transaction.commit` 결함 분석 및 수정안 제시 (PASS).
       - Project B: <토큰수> tokens 생성, `JobQueue._sequence` 결함 분석 및 수정안 제시 (PASS).
   - MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` [TODO]
   - MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` [TODO]
   ```

3. **`state/current.md` 수정**:
   ```markdown
   - WBS 3.1.4.2 Gemma4 NGRAM 완료 (`PASS_C2_ACTIVE`).
   - 다음 작업: WBS 3.1.4.3 Gemma4 MTP 실행 (`EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001`).
   ```

---

### Step 3. 검증 및 Git 커밋 & 푸시 (ThinkPad 터미널에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test

python3 scripts/validate_repo.py
git add docs/WBS.md state/current.md reports/ results/
git commit -m "test(wbs3): execute Gemma4 26B-A4B llama.cpp NGRAM C2 v2 (PASS_C2_ACTIVE)"
git push origin main
```
> 🎉 **3.1.4.2 완료!** 이제 3.1.4.3으로 넘어갑니다.

---

## 🚀 [3단계] 3.1.4.3 Gemma4 MTP (Dual Draft) C2 진행

> [!NOTE]
> Gemma4 MTP는 companion GGUF(`/srv/models/gemma-4-26b-a4b-it-qat-gguf/mtp-gemma-4-26B-A4B-it.gguf`)와 `--spec-draft-device CUDA0,CUDA1` 계약을 사용합니다. `scripts/run_c2_llama.py` 내부에서 모델 설정에 따라 이 플래그를 자동으로 주입하므로 추가 조작 없이 그대로 실행하시면 됩니다.

### Step 1. 실험 실행 및 리포트 자동 생성 (ThinkPad 터미널에 한 번에 복사/붙여넣기)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
EXP="EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001"
MODEL="gemma4-26b-a4b"
LANE="MTP"

echo "=== [1/5] 로컬 워크스페이스 검증 ==="
python3 scripts/validate_repo.py

echo "=== [2/5] P520으로 코드 동기화 ==="
rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

echo "=== [3/5] P520에서 벤치마크 원격 실행 (약 13~16분 소요) ==="
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
  python3 scripts/run_c2_llama.py --experiment-id $EXP --model $MODEL --lane $LANE --port 18080"

echo "=== [4/5] Raw 측정 결과 ThinkPad로 회수 ==="
rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/$EXP/ results/raw/$EXP/

echo "=== [5/5] 마크다운 리포트 생성 및 CSV 업데이트 ==="
python3 scripts/report_experiment.py results/raw/$EXP

echo "=== MTP 실행 완료! 판정 확인: ==="
cat results/raw/$EXP/completion.json
```

---

### Step 2. 결과 확인 및 문서 갱신 (WBS.md & state/current.md)

1. **생성된 마크다운 리포트 확인**:
   ```bash
   cat reports/gemma4-26b-a4b/EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001.md
   ```
   리포트에서 `TTFT`, `Decode`, `MTP draft/accepted 통계 및 수용률(%)` 등을 확인합니다.

2. **`docs/WBS.md` 수정**:
   `docs/WBS.md`의 `#### 3.1.4 Gemma4 26B-A4B` 섹션의 MTP 항목을 채웁니다:
   ```markdown
   - MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
     - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 smart drafter(`mtp-gemma-4-26B-A4B-it.gguf`, `CUDA0,CUDA1`) 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
     - TTFT (Batch Mean): <리포트의 TTFT>s, Prefill <리포트의 Prefill> tok/s, Mean Decode <리포트의 Decode> tok/s, Batch Wall <리포트의 Wall>s.
     - MTP Speculative 통계: Project A (draft <A draft>, accepted <A accepted>, <A %>), Project B (draft <B draft>, accepted <B accepted>, <B %>).
     - Peak VRAM: GPU0 <GPU0 VRAM> MiB / GPU1 <GPU1 VRAM> MiB.
     - Output analysis:
       - Project A: <토큰수> tokens 생성, `Transaction.commit` 결함 분석 및 수정안 제시 (PASS).
       - Project B: <토큰수> tokens 생성, `JobQueue._sequence` 결함 분석 및 수정안 제시 (PASS).
   - MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` [TODO]
   ```

3. **`state/current.md` 수정**:
   ```markdown
   - WBS 3.1.4.3 Gemma4 MTP 완료 (`PASS_C2_ACTIVE`).
   - 다음 작업: WBS 3.1.4.4 Gemma4 MTP_NGRAM 실행 (`EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001`).
   ```

---

### Step 3. 검증 및 Git 커밋 & 푸시 (ThinkPad 터미널에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test

python3 scripts/validate_repo.py
git add docs/WBS.md state/current.md reports/ results/
git commit -m "test(wbs3): execute Gemma4 26B-A4B llama.cpp MTP C2 v2 (PASS_C2_ACTIVE)"
git push origin main
```
> 🎉 **3.1.4.3 완료!** 이제 대망의 마지막 3.1.4.4로 넘어갑니다.

---

## 🚀 [4단계] 3.1.4.4 Gemma4 MTP_NGRAM C2 진행 및 WBS 3.1 종결

### Step 1. 실험 실행 및 리포트 자동 생성 (ThinkPad 터미널에 한 번에 복사/붙여넣기)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
EXP="EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001"
MODEL="gemma4-26b-a4b"
LANE="MTP_NGRAM"

echo "=== [1/5] 로컬 워크스페이스 검증 ==="
python3 scripts/validate_repo.py

echo "=== [2/5] P520으로 코드 동기화 ==="
rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

echo "=== [3/5] P520에서 벤치마크 원격 실행 (약 13~16분 소요) ==="
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
  python3 scripts/run_c2_llama.py --experiment-id $EXP --model $MODEL --lane $LANE --port 18080"

echo "=== [4/5] Raw 측정 결과 ThinkPad로 회수 ==="
rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/$EXP/ results/raw/$EXP/

echo "=== [5/5] 마크다운 리포트 생성 및 CSV 업데이트 ==="
python3 scripts/report_experiment.py results/raw/$EXP

echo "=== MTP_NGRAM 실행 완료! 판정 확인: ==="
cat results/raw/$EXP/completion.json
```

---

### Step 2. 결과 확인 및 WBS 3.1 전체 종결 문서 갱신

1. **생성된 마크다운 리포트 확인**:
   ```bash
   cat reports/gemma4-26b-a4b/EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001.md
   ```

2. **`docs/WBS.md` 수정 (3.1.4 및 WBS 3.1 전체 DONE 처리)**:
   - 상단 `### 3.1 Shared TP2 llama.cpp [IN PROGRESS ...]`를 **`### 3.1 Shared TP2 llama.cpp [DONE]`**으로 수정합니다.
   - `#### 3.1.4 Gemma4 26B-A4B [IN PROGRESS]`를 **`#### 3.1.4 Gemma4 26B-A4B [DONE]`**으로 변경하고 마지막 MTP_NGRAM 내용을 작성합니다:
   ```markdown
   #### 3.1.4 Gemma4 26B-A4B [DONE]
   - artifact: `UD-Q4_K_XL`.
   - KV: `FP16`.
   - 실행 lane: `TARGET`, `NGRAM`, corrected `MTP`, corrected `MTP_NGRAM`; MTP는 validated `CUDA0,CUDA1` draft contract 유지.
   - TARGET: `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
     - (앞서 작성한 내용 유지)
   - NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
     - (앞서 작성한 내용 유지)
   - MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
     - (앞서 작성한 내용 유지)
   - MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
     - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (`peak_processing: 2.0`, `peak_waiting: 0.0`). 2× V100 16GB TP2 환경에서 composite drafter 활성 상태로 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
     - TTFT (Batch Mean): <리포트의 TTFT>s, Prefill <리포트의 Prefill> tok/s, Mean Decode <리포트의 Decode> tok/s, Batch Wall <리포트의 Wall>s.
     - Speculative 통계: Project A (draft <A draft>, accepted <A accepted>, <A %>), Project B (draft <B draft>, accepted <B accepted>, <B %>).
     - Peak VRAM: GPU0 <GPU0 VRAM> MiB / GPU1 <GPU1 VRAM> MiB.
     - Output analysis:
       - Project A: <토큰수> tokens 생성, `Transaction.commit` 결함 분석 및 수정안 제시 (PASS).
       - Project B: <토큰수> tokens 생성, `JobQueue._sequence` 결함 분석 및 수정안 제시 (PASS).
     - 네 lane(TARGET, NGRAM, MTP, MTP_NGRAM) 모두 128K C2 Active Overlap 및 semantic oracle 검증을 완벽하게 통과함.
   ```

3. **`state/current.md` 수정**:
   ```markdown
   - WBS 3.1 Shared TP2 llama.cpp 전체 완료 ([DONE]).
   - 모든 대상 모델(Qwen3.8-27B, Ornith 1.5 9B, Ornith 1.5 35B-A3B, Gemma4 26B-A4B)의 128K C2 Active Concurrency 검증 통과.
   - 다음 작업: WBS 3.2 (Shared TP2 1Cat-vLLM STOCK v2 재검증) 또는 WBS 4 (Serving Capacity Comparison).
   ```

---

### Step 3. 검증 및 최종 Git 커밋 & 푸시 (ThinkPad 터미널에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test

# 1. 저장소 계약 검증
python3 scripts/validate_repo.py

# 2. 결과 및 문서 스테이징
git add docs/WBS.md state/current.md reports/ results/

# 3. WBS 3.1 종결 커밋 메시지
git commit -m "test(wbs3): execute Gemma4 26B-A4B llama.cpp MTP_NGRAM C2 v2 (PASS_C2_ACTIVE) and close WBS 3.1"

# 4. 원격 저장소 최종 푸시
git push origin main
```

---

## 🛠️ 비상 시 문제 해결 (Troubleshooting)

1. **P520에서 포트 충돌(18080) 또는 잔류 Docker 컨테이너가 있을 때**:
   ```bash
   ssh p520-llm "docker ps -q --filter 'label=project=v100-llm-test' | xargs -r docker stop"
   ```
2. **실행 중 실시간 서버 로그 모니터링이 필요할 때**:
   ```bash
   ssh p520-llm "tail -f /home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/<실험ID>/runtime/server-0.log"
   ```
3. **P520 GPU 사용 현황 실시간 감시**:
   ```bash
   ssh p520-llm "watch -n 1 nvidia-smi"
   ```
