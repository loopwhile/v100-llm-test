# WBS 3.1.4 Gemma4 26B-A4B llama.cpp C2 128K 실행 가이드 및 명령어 모음

본 문서는 **WBS 3.1.4 Gemma4 26B-A4B-IT-QAT** 모델을 2× Tesla V100 16GB TP2 환경에서 `llama.cpp` C2 (독립 128K 에이전트 2개 병렬)로 직접 실행하고 검증하기 위한 가이드 및 명령어 모음이다.

---

## 1. 개요 및 실험 계약 (Execution Contract)

- **대상 모델**: `Gemma4-26B-A4B-IT-QAT` (UD-Q4_K_XL)
- **KV 캐시 포맷**: `FP16` (float16)
- **런타임**: `llama.cpp` (pinned b10775 / `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`)
- **Docker 이미지**: `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`
- **호스트**: `p520-llm` (스냅샷: `/home/loopwhile/v100-llm-test-wbs22-20260924`)
- **컨텍스트 설정**: 슬롯당 131,072 토큰 (총 262,144 토큰 KV pool, `--kv-unified --kv-unified-per-slot 131072`)
- **동시성 (Concurrency)**: `C2` (독립 128K 세션 2개 동시 처리)
- **공식 워크로드**: `workloads/concurrency/v2.json`
- **시맨틱 오라클**: `workloads/concurrency/v2-ground-truth.json`

### 고유 특수 계약 (Important Gemma4 Specifics)
> [!IMPORTANT]
> - **MTP 어시스턴트 모델 필수**: Gemma4의 MTP 계열은 타깃 GGUF 내장 MTP가 아닌 별도 스마트 Q4_0 어시스턴트 GGUF(`/srv/models/gemma-4-26b-a4b-it-qat-gguf/mtp-gemma-4-26B-A4B-it.gguf`)가 필요하다.
> - **듀얼 드래프트 디바이스 (`--spec-draft-device CUDA0,CUDA1`)**: b10775 TP2 layer-split 환경에서 CUDA0 단독 드래프트는 기동 크래시(`FAIL_STARTUP`)를 유발하므로, 반드시 `CUDA0,CUDA1` 양쪽 GPU에 분산 적재해야 128K 기동이 성공한다.
> - **예상 VRAM**: GPU0 약 8,983 ~ 9,150 MiB, GPU1 약 9,120 ~ 9,300 MiB로 16GB 한도 내에서 2개 슬롯 모두 여유 있게 상주한다 (OOM 여유 ~7.0 GiB).

---

## 2. 레인별 실험 ID 및 매트릭스

| 번호 | 레인 | Speculative 설정 | 계획된 실험 ID | 예상 소요 시간 |
|---|---|---|---|---|
| **3.1.4.1** | `TARGET` | target-only (off) | `EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001` | 약 12~15분 |
| **3.1.4.2** | `NGRAM` | ngram-simple (`--draft-min 1 --draft-max 4`) | `EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001` | 약 12~15분 |
| **3.1.4.3** | `MTP` | smart Q4_0 companion, `n=4`, `CUDA0,CUDA1` | `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001` | 약 13~16분 |
| **3.1.4.4** | `MTP_NGRAM` | composite `draft-mtp,ngram-simple` | `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001` | 약 13~16분 |

---

## 3. 사전 준비 (Pre-execution)

실행 전 ThinkPad 워크스페이스에서 레포 계약을 검증하고 P520 호스트로 최신 코드를 동기화한다.

```bash
# 1. ThinkPad 로컬 계약 검증
cd /home/loopwhile/Data/Workspace_VSCode/v100-llm-test
python3 scripts/validate_repo.py

# 2. P520 호스트 스냅샷으로 rsync 동기화
rsync -avu --exclude='.git' --exclude='results/raw' --exclude='reports' \
  /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/ \
  p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/

# 3. P520 호스트의 GPU 상태 및 18080 포트 확인 (점유 프로세스 없어야 함)
ssh p520-llm "nvidia-smi && ss -ltnp | grep 18080 || echo 'Port 18080 is clean'"
```

---

## 4. 원클릭 자동 벤치마크 실행 명령어 (권장 방식)

`scripts/run_c2_llama.py` 스크립트는 Docker 컨테이너 기동, 128K 토크나이저 캘리브레이션, 동시성 측정(Active Overlap 샘플링), 시맨틱 오라클 판정, 컨테이너 종료 및 클린업을 완전 자동 수행한다.

### 4.1 TARGET 레인 실행
```bash
# SSH를 통한 P520 실행
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
python3 scripts/run_c2_llama.py \
  --experiment-id EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001 \
  --model gemma4-26b-a4b \
  --lane TARGET \
  --port 18080"
```

### 4.2 NGRAM 레인 실행
```bash
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
python3 scripts/run_c2_llama.py \
  --experiment-id EXP-V100-GEMMA4-26B-LLAMA-F16-NGRAM-C2-128K-20260925-001 \
  --model gemma4-26b-a4b \
  --lane NGRAM \
  --port 18080"
```

### 4.3 MTP 레인 실행
```bash
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
python3 scripts/run_c2_llama.py \
  --experiment-id EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C2-128K-20260925-001 \
  --model gemma4-26b-a4b \
  --lane MTP \
  --port 18080"
```

### 4.4 MTP_NGRAM 레인 실행
```bash
ssh p520-llm "cd /home/loopwhile/v100-llm-test-wbs22-20260924 && \
python3 scripts/run_c2_llama.py \
  --experiment-id EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C2-128K-20260925-001 \
  --model gemma4-26b-a4b \
  --lane MTP_NGRAM \
  --port 18080"
```

---

## 5. 사후 처리 및 리포트 생성 (Post-execution)

실험 완료 후 생성된 raw 증거를 ThinkPad 워크스페이스로 rsync하고 Markdown 리포트와 CSV를 생성한다.

```bash
EXP_ID="EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C2-128K-20260925-001" # 또는 해당 EXP_ID

# 1. Raw 결과 ThinkPad로 회수
rsync -avu p520-llm:/home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/${EXP_ID}/ \
  results/raw/${EXP_ID}/

# 2. Markdown 리포트 생성 및 results/summary.csv, reports/comparison.csv 자동 갱신
python3 scripts/report_experiment.py results/raw/${EXP_ID}

# 3. 완료 확인
cat results/raw/${EXP_ID}/completion.json
```

---

## 6. 수동 Docker 서버 단독 기동 명령어 (디버깅 / 단독 서빙용)

하네스 없이 `llama-server` 컨테이너만 수동으로 띄워 테스트하고자 할 때 사용하는 원본 Docker 명령어이다.

### 6.1 TARGET 단독 기동
```bash
docker run --rm --pull=never \
  --name v100-gemma4-target-c2 \
  --label project=v100-llm-test \
  --gpus '"device=0,1"' \
  -p 127.0.0.1:18080:8080 \
  -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro \
  --entrypoint llama-server \
  kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 \
  -m /model/target.gguf \
  --host 0.0.0.0 --port 8080 -ngl all \
  --split-mode layer --tensor-split 1,1 \
  --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 \
  --batch-size 512 --ubatch-size 128 \
  --cache-type-k f16 --cache-type-v f16 --flash-attn on \
  --spec-type none \
  --jinja --reasoning off --metrics --slots --no-warmup
```

### 6.2 MTP (Dual Draft) 단독 기동
```bash
docker run --rm --pull=never \
  --name v100-gemma4-mtp-c2 \
  --label project=v100-llm-test \
  --gpus '"device=0,1"' \
  -p 127.0.0.1:18080:8080 \
  -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro \
  -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/mtp-gemma-4-26B-A4B-it.gguf:/model/draft.gguf:ro \
  --entrypoint llama-server \
  kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 \
  -m /model/target.gguf \
  --host 0.0.0.0 --port 8080 -ngl all \
  --split-mode layer --tensor-split 1,1 \
  --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 \
  --batch-size 512 --ubatch-size 128 \
  --cache-type-k f16 --cache-type-v f16 --flash-attn on \
  --spec-type draft-mtp --spec-draft-n-max 4 --draft-min 1 --draft-max 4 \
  --model-draft /model/draft.gguf \
  --spec-draft-device CUDA0,CUDA1 \
  --jinja --reasoning off --metrics --slots --no-warmup
```

---

## 7. 실시간 모니터링 및 상태 확인

실행 중 P520에서 실시간 진행 상황을 점검하려면 다음 명령어를 활용한다:

```bash
# 1. 진행 단계 확인 (prepared, running, results_saved 등)
ssh p520-llm "cat /home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/${EXP_ID}/runtime/progress.json | jq"

# 2. 실시간 서버 로그 (prefill progress 및 decode 속도)
ssh p520-llm "tail -f /home/loopwhile/v100-llm-test-wbs22-20260924/results/raw/${EXP_ID}/runtime/server-0.log"

# 3. GPU VRAM 및 부하 상태
ssh p520-llm "nvidia-smi -l 2"
```
