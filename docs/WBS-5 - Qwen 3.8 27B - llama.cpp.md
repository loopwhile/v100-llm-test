대상 프로젝트:
- Repository: loopwhile/v100-llm-test
- Model: Qwen3.8-27B
- Runtime: llama.cpp
- Phase: WBS5
- 작업 종류: Frozen candidate set의 로컬 실행 가능성 검증만 수행

중요:
이번 작업에서는 GPU measured inference를 절대 실행하지 마라.
128K prompt를 전송하지 마라.
benchmark workload를 실행하지 마라.
새 raw experiment를 실제 measured run으로 생성하지 마라.
server를 장시간 구동하지 마라.
기존 raw artifact/report를 수정하지 마라.
candidate를 추가하거나 변경하지 마라.

현재 Frozen candidate set은 정확히 아래 3개뿐이다.

R0:
Q38-LLAMA-WBS5-R0-TARGET-B512-UB128
- TARGET
- --spec-type none
- --batch-size 512
- --ubatch-size 128

R1:
Q38-LLAMA-WBS5-R1-NGRAM-DEFAULT
- R0 대비 유일한 serving 변경:
  --spec-type none
  ->
  --spec-type ngram-simple
- ngram-simple pinned defaults 유지:
  size_n=12
  size_m=48
  min_hits=1
- 명시적 세부 NGRAM override를 추가하지 말 것

R2:
Q38-LLAMA-WBS5-R2-TARGET-UB256
- R0 대비 유일한 serving 변경:
  --ubatch-size 128
  ->
  --ubatch-size 256
- --batch-size 512는 반드시 유지

고정 invariant:

Model:
- unsloth/Qwen3.8-27B-GGUF
- revision 4ca720788d1e01f1bff70c033e0d0028fd02e502

Artifact:
- /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf
- SHA256 322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482
- weight quant UD-Q4_K_M

KV:
- cache-type-k q8_0
- cache-type-v q8_0

Runtime:
- llama.cpp build 10775
- commit 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
- 현재 repo가 고정한 exact container image digest 유지

Topology:
- Shared TP2
- --split-mode layer
- --tensor-split 1,1
- --ctx-size 262144
- --parallel 2
- --kv-unified
- --kv-unified-per-slot 131072
- -ngl all
- --flash-attn on
- --jinja
- --reasoning off
- --metrics
- --slots
- --no-warmup

Environment:
- GGML_CUDA_P2P를 설정하지 말 것
- GGML_CUDA_DISABLE_GRAPHS를 설정하지 말 것
- 기존 validated environment를 성능 목적으로 임의 변경하지 말 것

WBS5 formal workload:
- workloads/performance/v1.json
- context_tokens 131072/request
- output reserve 4096/request
- min_output_tokens 1024/request
- 2 independent requests
- deterministic sampling contract 유지

확인해야 할 사항:

1. 현재 main HEAD와 WBS5 관련 파일 상태를 확인하라.

2. 현재 runner/runtime launcher 구조에서 R0/R1/R2를 정확히 표현할 수 있는지 확인하라.
   - 아직 measured execution은 하지 마라.
   - 가능하면 command generation 또는 dry-run 수준에서만 검증하라.

3. 각 candidate의 예상 exact llama-server command를 출력하라.
   R0/R1/R2 사이 command diff가 frozen specification과 정확히 일치하는지 검증하라.

4. R0:
   - --spec-type none
   - b512
   - ub128
   가 정확히 생성되는지 확인하라.

5. R1:
   - R0 대비 --spec-type ngram-simple만 달라지는지 확인하라.
   - size_n=12 / size_m=48 / min_hits=1이 pinned b10775의 default인지 source 또는 binary help로 확인하라.
   - 별도 draft model이나 MTP 관련 option이 추가되지 않는지 확인하라.

6. R2:
   - R0 대비 --ubatch-size 256 하나만 달라지는지 확인하라.
   - --batch-size 512가 유지되는지 확인하라.
   - runner 또는 runtime_launcher가 ubatch를 다시 128로 덮어쓰는 구조가 없는지 확인하라.

7. pinned binary/source capability를 확인하라.
   - --spec-type none
   - --spec-type ngram-simple
   - --batch-size
   - --ubatch-size
   - --kv-unified
   - --kv-unified-per-slot
   - --flash-attn
   가 실제 pinned build에서 사용 가능한지 확인하라.
   단, 이 확인을 위해 measured model inference는 하지 마라.

8. CUDA Graph 관련:
   - 현재 pinned source/build가 CUDA Graph capable인지 확인하라.
   - 기존 WBS3 raw server log의 `graphs reused` evidence를 보존하라.
   - 새로운 graph 옵션을 candidate에 추가하지 마라.
   - WBS5 runner가 run 종료 후 graph reuse count를 report/raw evidence에 보존할 수 있는지만 확인하라.

9. 하드웨어/telemetry preflight 설계를 확인하라.
   measured run 전에 다음을 기록할 수 있어야 한다:
   - GPU model
   - GPU total VRAM
   - 시작 free/used VRAM
   - temperature
   - power
   - clocks
   - GPU-util
   - 기존 GPU process
   - host memory/swap 상태

   expected hardware는:
   - Tesla V100-SXM2-16GB ×2
   - 각 16384 MiB

10. workload runner가 다음 WBS5 결과를 저장할 수 있는지 확인하라:
   - TTFT
   - prefill tok/s
   - mean request decode tok/s
   - aggregate decode tok/s
   - end-to-end output tok/s
   - total output tokens
   - batch wall
   - GPU0/GPU1 peak VRAM
   - power/temp/clocks
   - output integrity
   - graph reuse count
   - R1의 draft / accepted / acceptance ratio

11. R0 repetition policy를 지원할 수 있는지 확인하라.
   - R0는 동일 candidate를 서로 다른 experiment ID로 2회 measured execution할 예정
   - 기존 raw artifact를 덮어쓰면 안 됨
   - 이 단계에서는 실제 두 run을 실행하지 마라

12. candidate별 confirm policy가 구현 가능한지 확인하라.
   - R1/R2는 screening 1회 후 필요할 때 동일 configuration confirm run 1회
   - confirm은 새 candidate가 아니라 동일 candidate의 fresh repetition임

13. 다음 항목은 절대 추가하지 마라:
   - P2P candidate
   - Graph OFF candidate
   - NGRAM size_n/size_m/min_hits tuning candidate
   - ub512
   - batch-size tuning
   - MTP/MTP_NGRAM
   - alternate NGRAM implementation
   - tensor split
   - KV 변경
   - quant 변경
   - runtime rebuild

14. 기존 runner가 WBS5 formal workload를 지원하지 않아 코드 수정이 필요하다면:
   - 필요한 수정 파일
   - 최소 변경 범위
   - 왜 필요한지
   - 기존 WBS2/WBS3 동작을 깨지 않는 방법
   을 제안하라.
   실제 GPU measured inference는 하지 마라.

최종 보고 형식:

A. 현재 main / relevant file 상태

B. Frozen candidate별 실행 가능성
- R0: READY / BLOCKED
- R1: READY / BLOCKED
- R2: READY / BLOCKED

C. 각 candidate의 예상 exact command와 R0 대비 diff

D. pinned binary/source capability 확인 결과

E. WBS5 workload/metric capture 준비 상태

F. measured inference 전에 해결해야 하는 blocker

G. 필요한 최소 코드 수정안
- 없다면 NONE

H. 최종 결론
- `READY_FOR_WBS5_MEASURED_RUN`
또는
- `BLOCKED`
- BLOCKED라면 정확한 이유 명시

다시 강조:
이 작업은 로컬 실행 가능성 검증만 한다.
GPU measured inference, 128K request 제출, benchmark 실행은 금지한다.
