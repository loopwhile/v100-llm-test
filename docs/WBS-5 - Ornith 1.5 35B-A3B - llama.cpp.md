# Task: Ornith 1.5 35B-A3B / llama.cpp WBS5 로컬 실행 가능성 검증

현재 단계에서는 GPU measured inference를 절대 실행하지 마라.

목적은 이미 Freeze된 WBS5 candidate R0~R3가 현재 P520 로컬 환경과 pinned runtime에서 정확히 실행 가능한 형태인지 정적/비추론 검증하는 것이다.

새 optimization candidate를 추가하거나 recipe를 변경하지 마라.

## Frozen candidates

R0:
- ID: ORN35-LLAMA-WBS5-R0-TARGET
- TARGET
- batch=512
- ubatch=128
- speculative disabled

R1:
- ID: ORN35-LLAMA-WBS5-R1-MTP1
- R0 대비 유일한 변경:
  - --spec-type draft-mtp
  - --spec-draft-n-max 1

R2:
- ID: ORN35-LLAMA-WBS5-R2-UB256
- R0 대비 유일한 변경:
  - --ubatch-size 128 -> 256
- --batch-size 512는 그대로 유지

R3:
- ID: ORN35-LLAMA-WBS5-R3-QUEUE4X
- R0 대비 유일한 변경:
  - CUDA_SCALE_LAUNCH_QUEUES=4x

## 반드시 보존할 invariant

Model:
- repository: ornith-ai/Ornith-1.5-35B-A3B-GGUF
- revision: 12393612fd4f730ff5aadc23e9b8f9648aa49ceb
- local artifact:
  /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf
- SHA256:
  42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f

Quantization:
- weight Q4_K_M
- KV K/V Q8_0

Runtime:
- llama.cpp build 10775
- pinned commit:
  67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
- OCI:
  kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149

Hardware/topology:
- Tesla V100-SXM2-16GB x2
- tp2-shared
- -ngl all
- --split-mode layer
- --tensor-split 1,1

Context:
- --ctx-size 262144
- --parallel 2
- --kv-unified
- --kv-unified-per-slot 131072

Other:
- --flash-attn on
- --jinja
- --reasoning off
- --metrics
- --slots
- --no-warmup

Workload:
- workloads/performance/v1.json
- 128K x2
- 4096 output reserve
- minimum actual output 1024/request
- cold-independent lane

## 검증해야 할 것

1. 현재 로컬 Git checkout과 GitHub main의 관계를 확인하라.
   - commit/dirty state를 기록하라.
   - historical raw artifact는 수정하지 마라.

2. exact OCI image가 로컬에 존재하고 digest가 일치하는지 확인하라.

3. inference를 실행하지 않고 `llama-server --version` 및 `--help` 수준에서 다음 feature를 확인하라.
   - --kv-unified
   - --kv-unified-per-slot
   - --batch-size
   - --ubatch-size
   - --spec-type
   - draft-mtp
   - --spec-draft-n-max

4. model artifact SHA256을 다시 확인하라.

5. GPU inventory를 확인하라.
   - Tesla V100-SXM2-16GB x2
   - total VRAM
   - 현재 GPU compute process 유무
   - driver/CUDA-visible 상태

6. 다음 topology evidence를 수집하라.
   - nvidia-smi topo -m
   - 지원된다면 nvidia-smi nvlink -s
   단, P2P/NVLink 설정을 변경하지 마라.

7. R0~R3 각각에 대해 최종 launch command를 "계획만" 생성하라.
   실제 llama-server model load 또는 inference는 실행하지 마라.

8. candidate별 command diff가 정확히 다음 하나만 존재하는지 검증하라.
   - R1: TARGET -> MTP n=1
   - R2: ubatch 128 -> 256
   - R3: CUDA_SCALE_LAUNCH_QUEUES=4x 추가

9. R1이 별도 MTP companion GGUF를 주입하지 않고 embedded native MTP를 사용하는 계획인지 확인하라.

10. R3의 container environment에 CUDA_SCALE_LAUNCH_QUEUES=4x가 실제 전달될 수 있는지 비추론 방식으로 확인하라.
    필요한 경우 container에서 env 출력만 확인해도 된다.
    모델을 load하지 마라.

11. performance/v1용 runner/harness가 현재 존재하는지 확인하라.
    존재하지 않거나 C2 runner가 concurrency/v2에 hard-code되어 있다면 정확히 보고하라.
    이 경우 measured inference를 시작하지 말고 WBS5 runner에서 필요한 최소 변경점을 제안하라.

12. WBS5 runner가 최소한 다음 evidence를 저장할 수 있는지 확인하라.
    - per-request TTFT
    - per-request prefill TPS
    - per-request decode TPS
    - mean_request_decode_tps
    - aggregate_decode_tps
    - end_to_end_output_tps
    - batch wall
    - peak GPU0/GPU1 VRAM
    - power / temperature / SM clock / memory clock
    - output integrity
    - active overlap / queue status
    - speculative draft/accepted/acceptance for MTP
    - per-slot n_prompt_tokens_processed timeline 또는 동등한 prompt-progress evidence

13. aggregate_decode_tps 산식을 임의 변경하지 마라.
    현재 harness의 의미는:
    total output tokens /
    (latest request completion - earliest first-token)
    이며 submission->TTFT를 포함하는 end-to-end metric은 별도의 end_to_end_output_tps다.

14. 기존 WBS3에서 128K x2 prefill이 사실상 직렬 처리된 evidence를 고려하라.
    WBS5에서도 per-slot prompt progress를 기록하여 이 scheduling behavior를 관찰 가능하게 만들어라.
    단, 이를 고치기 위한 새로운 optimization candidate를 만들지 마라.

15. measured repetition은 자동으로 늘리지 마라.
    현재 project policy상 반복 측정 >1은 사용자 명시 승인이 필요하다.

## 금지사항

- GPU measured inference 실행 금지
- 128K workload 제출 금지
- 짧은 test inference도 실행하지 말 것
- raw historical artifact 수정 금지
- candidate R4/R5 등을 새로 추가 금지
- MTP n=2 실행/추가 금지
- NGRAM tuning 금지
- CUDA Graph tuning 금지
- GGML_CUDA_P2P 강제 금지
- prefix-cache tuning 금지
- batch/ubatch grid 생성 금지
- runtime/image 재빌드 금지

## 최종 출력 형식

A. 로컬 환경 검증 결과
B. invariant 일치 여부
C. R0~R3 candidate별 launch-plan 검증
D. 필요한 WBS5 runner/harness 최소 변경
E. measured inference 전에 남은 blocker
F. 최종 verdict:
   - READY_FOR_MEASURED_INFERENCE
   - NOT_READY
   중 하나

중요:
READY_FOR_MEASURED_INFERENCE는 "실행해도 된다"는 기술적 준비 상태 판정일 뿐 실제 inference 실행 승인이 아니다.
실제 GPU measured inference는 별도의 사용자 명령 전까지 절대 시작하지 마라.
