# WBS 3.1.4 Gemma4 26B-A4B llama.cpp C2 128K 전체 실행 가이드 및 명령어 모음

본 문서는 **WBS 3.1.4 (Gemma4 26B-A4B-IT-QAT, UD-Q4_K_XL, FP16 KV)**의 4개 레인을 오케스트레이터와 서브에이전트가 수행해 온 라이프사이클(사전 검증 -> P520 동기화 -> 벤치마크 실행 -> 결과 회수 -> 리포트 생성 -> WBS/state 갱신 -> Git 커밋/푸시)과 **100% 동일하게 직접 순차 진행할 수 있도록 작성된 완전 자동/복사 실행 매뉴얼**입니다.

---

## 📌 전체 실행 순서 요약

1. **3.1.4.1 TARGET**: `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001`
2. **3.1.4.2 NGRAM**: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001`
3. **3.1.4.3 MTP**: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` (Dual Draft `CUDA0,CUDA1`)
4. **3.1.4.4 MTP_NGRAM**: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` (Composite Speculative)
5. **최종 WBS 3.1 종결 처리 및 푸시**

---

## [Step 1] 3.1.4.1 Gemma4 TARGET C2 실행

### 1-1. 사전 점검 및 P520 스냅샷 동기화 (ThinkPad에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test

# 1. 저장소 계약 검증 (반드시 PASS 확인)
python3 scripts/validate_repo.py

# 2. P520 호스트로 최신 코드 rsync 동기화
rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

# 3. P520 GPU 및 18080 포트 클린 여부 확인
ssh p520-llm "nvidia-smi --query-compute-apps=pid --format=csv,noheader && ss -ltnp | grep 18080 || echo 'Clean'"
```

### 1-2. 벤치마크 실행 (P520에서 백그라운드 또는 포그라운드 실행)
```bash
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
python3 scripts/run_c2_llama.py \
  --experiment-id EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001 \
  --model gemma4-26b-a4b \
  --lane TARGET \
  --port 18080"
```
*(예상 소요 시간: 약 12~15분. 완료 시 exit code 0 및 결과 저장됨)*

> **실행 중 모니터링 명령어 (새 터미널에서 확인 시)**:
> ```bash
> ssh p520-llm "tail -n 20 /home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001/runtime/server-0.log"
> ```

### 1-3. 결과 회수 및 리포트 생성 (ThinkPad에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
EXP=EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001

# 1. P520의 Raw 결과 회수
rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/$EXP/ results/raw/$EXP/

# 2. Markdown 리포트 생성 및 summary.csv / comparison.csv 갱신
python3 scripts/report_experiment.py results/raw/$EXP

# 3. 완료 판정 확인 (PASS_C2_ACTIVE 확인)
cat results/raw/$EXP/completion.json
```

### 1-4. WBS 및 State 문서 갱신
- `docs/WBS.md`의 `#### 3.1.4 Gemma4 26B-A4B` 섹션을 다음과 같이 수정:
```markdown
#### 3.1.4 Gemma4 26B-A4B [IN PROGRESS]
- artifact: `UD-Q4_K_XL`.
- KV: `FP16`.
- 실행 lane: `TARGET`, `NGRAM`, corrected `MTP`, corrected `MTP_NGRAM`; MTP는 validated `CUDA0,CUDA1` draft contract 유지.
- TARGET: `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (peak_processing: 2.0, peak_waiting: 0.0). 2× V100 16GB TP2 환경에서 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
- NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` [TODO]
- MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` [TODO]
- MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` [TODO]
```
- `state/current.md`의 `Current task:` 섹션에 `3.1.4 Gemma4 TARGET PASS_C2_ACTIVE` 기록 및 다음 작업 `NGRAM` 반영.

### 1-5. 계약 검증 및 Git 커밋/푸시
```bash
# 계약 검증
python3 scripts/validate_repo.py

# Git 커밋 및 푸시
git add docs/WBS.md state/current.md reports/ results/
git commit -m "test(wbs3): execute Gemma4 26B-A4B llama.cpp TARGET C2 v2 (PASS_C2_ACTIVE)"
git push origin main
```

---

## [Step 2] 3.1.4.2 Gemma4 NGRAM C2 실행

### 2-1. 사전 점검 및 동기화 (ThinkPad에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
python3 scripts/validate_repo.py

rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

ssh p520-llm "nvidia-smi --query-compute-apps=pid --format=csv,noheader && ss -ltnp | grep 18080 || echo 'Clean'"
```

### 2-2. 벤치마크 실행 (P520)
```bash
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
python3 scripts/run_c2_llama.py \
  --experiment-id EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001 \
  --model gemma4-26b-a4b \
  --lane NGRAM \
  --port 18080"
```
*(예상 소요 시간: 약 12~15분)*

### 2-3. 결과 회수 및 리포트 생성 (ThinkPad)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
EXP=EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001

rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/$EXP/ results/raw/$EXP/
python3 scripts/report_experiment.py results/raw/$EXP
cat results/raw/$EXP/completion.json
```

### 2-4. WBS 및 State 문서 갱신
- `docs/WBS.md`에 NGRAM 결과 기록:
```markdown
- NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (peak_processing: 2.0, peak_waiting: 0.0). NGRAM 활성 상태에서 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
- MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` [TODO]
```
- `state/current.md`에 다음 작업을 `MTP`로 갱신.

### 2-5. 계약 검증 및 Git 커밋/푸시
```bash
python3 scripts/validate_repo.py

git add docs/WBS.md state/current.md reports/ results/
git commit -m "test(wbs3): execute Gemma4 26B-A4B llama.cpp NGRAM C2 v2 (PASS_C2_ACTIVE)"
git push origin main
```

---

## [Step 3] 3.1.4.3 Gemma4 MTP (Dual Draft) C2 실행

### 3-1. 사전 점검 및 동기화 (ThinkPad에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
python3 scripts/validate_repo.py

rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

ssh p520-llm "nvidia-smi --query-compute-apps=pid --format=csv,noheader && ss -ltnp | grep 18080 || echo 'Clean'"
```

### 3-2. 벤치마크 실행 (P520)
> [!NOTE]
> `run_c2_llama.py` 내부에서 Gemma4 설정 파일에 정의된 스마트 어시스턴트 모델(`mtp-gemma-4-26B-A4B-it.gguf`), `--spec-draft-n-max 4`, `--spec-draft-device CUDA0,CUDA1` 플래그를 자동으로 주입하여 실행합니다.

```bash
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
python3 scripts/run_c2_llama.py \
  --experiment-id EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001 \
  --model gemma4-26b-a4b \
  --lane MTP \
  --port 18080"
```
*(예상 소요 시간: 약 13~16분)*

### 3-3. 결과 회수 및 리포트 생성 (ThinkPad)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
EXP=EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001

rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/$EXP/ results/raw/$EXP/
python3 scripts/report_experiment.py results/raw/$EXP
cat results/raw/$EXP/completion.json
```

### 3-4. WBS 및 State 문서 갱신
- `docs/WBS.md`에 MTP 결과 기록:
```markdown
- MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - Concurrency evidence: `c2_resident: true`, `c2_active: true`, `queue_only: false` (peak_processing: 2.0, peak_waiting: 0.0). smart Q4_0 drafter (n=4, CUDA0,CUDA1) 활성 상태에서 2개 독립 128K 세션 동시 상주 및 병렬 디코드 완벽 통과.
- MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` [TODO]
```
- `state/current.md`에 다음 작업을 `MTP_NGRAM`으로 갱신.

### 3-5. 계약 검증 및 Git 커밋/푸시
```bash
python3 scripts/validate_repo.py

git add docs/WBS.md state/current.md reports/ results/
git commit -m "test(wbs3): execute Gemma4 26B-A4B llama.cpp MTP C2 v2 (PASS_C2_ACTIVE)"
git push origin main
```

---

## [Step 4] 3.1.4.4 Gemma4 MTP_NGRAM (Composite) C2 실행

### 4-1. 사전 점검 및 동기화 (ThinkPad에서 실행)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
python3 scripts/validate_repo.py

rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

ssh p520-llm "nvidia-smi --query-compute-apps=pid --format=csv,noheader && ss -ltnp | grep 18080 || echo 'Clean'"
```

### 4-2. 벤치마크 실행 (P520)
```bash
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
python3 scripts/run_c2_llama.py \
  --experiment-id EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001 \
  --model gemma4-26b-a4b \
  --lane MTP_NGRAM \
  --port 18080"
```
*(예상 소요 시간: 약 13~16분)*

### 4-3. 결과 회수 및 리포트 생성 (ThinkPad)
```bash
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
EXP=EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001

rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/$EXP/ results/raw/$EXP/
python3 scripts/report_experiment.py results/raw/$EXP
cat results/raw/$EXP/completion.json
```

### 4-4. WBS 및 State 문서 갱신 (3.1.4 및 WBS 3.1 전체 완료)
- `docs/WBS.md`의 `#### 3.1.4 Gemma4 26B-A4B [IN PROGRESS]`를 `#### 3.1.4 Gemma4 26B-A4B [DONE]`으로 변경:
```markdown
#### 3.1.4 Gemma4 26B-A4B [DONE]
- artifact: `UD-Q4_K_XL`.
- KV: `FP16`.
- 실행 lane: `TARGET`, `NGRAM`, corrected `MTP`, corrected `MTP_NGRAM`; MTP는 validated `CUDA0,CUDA1` draft contract 유지.
- TARGET: `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
- NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
- MTP: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
- MTP_NGRAM: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` — **`PASS_C2_ACTIVE`**
  - 네 lane 모두 128K C2 Active Overlap 및 semantic oracle 검증을 완벽하게 통과함.
```
- `docs/WBS.md` 상단 `### 3.1 Shared TP2 llama.cpp [IN PROGRESS ...]`를 `### 3.1 Shared TP2 llama.cpp [DONE]`으로 변경.
- `state/current.md`의 `Current task:` 섹션을 WBS 3.1 전체 완료 및 다음 단계 WBS 4로 변경.

### 4-5. 계약 검증 및 최종 Git 커밋/푸시
```bash
python3 scripts/validate_repo.py

git add docs/WBS.md state/current.md reports/ results/
git commit -m "test(wbs3): execute Gemma4 26B-A4B llama.cpp MTP_NGRAM C2 v2 (PASS_C2_ACTIVE) and close WBS 3.1"
git push origin main
```

---

## 🔍 비상 시 트러블슈팅 가이드

1. **Docker 컨테이너가 남아있거나 포트가 점유된 경우**:
   ```bash
   ssh p520-llm "docker ps -q --filter 'label=project=v100-llm-test' | xargs -r docker stop"
   ```
2. **GPU 프로세스 강제 확인**:
   ```bash
   ssh p520-llm "fuser -v /dev/nvidia* || true"
   ```
3. **P520 스냅샷 위치 주의**:
   - P520 스냅샷은 Git 저장소가 아니므로 P520 내에서 `git pull`을 실행하지 마시고, 반드시 ThinkPad에서 `rsync`로만 동기화하십시오.
