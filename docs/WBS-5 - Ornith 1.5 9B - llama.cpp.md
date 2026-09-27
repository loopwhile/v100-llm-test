Repository:
https://github.com/loopwhile/v100-llm-test

고정 변수:
- MODEL = Ornith 1.5 9B
- RUNTIME = llama.cpp
- WBS = WBS5
- Round 1 candidate set = FROZEN

이번 작업은 GPU benchmark 실행이 아니라 **로컬 실행 가능성 검증만** 하는 작업이다.

절대로 measured inference를 실행하지 마라.
128K performance request, benchmark request, full generation을 보내지 마라.
기존 raw artifact를 수정하거나 덮어쓰지 마라.
새 recipe candidate를 임의 추가하지 마라.

현재 Frozen candidate는 정확히 다음 3개뿐이다.

R0 = TARGET_BASELINE
- topology: 1GPU x2 + LiteLLM
- lane: TARGET
- batch-size: 512
- ubatch-size: 128
- workload: workloads/performance/v1.json

R1 = TARGET_UB256
- R0 대비 유일한 변경:
  --ubatch-size 128 -> 256

R2 = NGRAM_DEFAULT
- R0 대비 유일한 변경:
  --spec-type none -> --spec-type ngram-simple
- batch-size=512
- ubatch-size=128
- NGRAM size_n / size_m은 pinned default 사용
- NGRAM parameter tuning 금지

R3는 정의하지 않는다.

반드시 보존할 invariant:

- Model artifact:
  /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf
- SHA256:
  79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480
- Weight quantization: Q6_K
- KV: FP16
- llama.cpp build: 10775
- llama.cpp commit:
  67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
- V100 SXM2 16GB x2
- backend 0 = GPU0
- backend 1 = GPU1
- backend context = 131072
- backend parallel = 1
- kv-unified enabled
- kv-unified-per-slot = 131072
- Flash Attention ON
- Jinja enabled
- reasoning/thinking OFF
- LiteLLM 1.101.0
- single LiteLLM gateway endpoint
- least-busy routing
- backend max_parallel_requests = 1
- num_retries = 0
- routing-settled admission behavior 유지
- WBS5 performance workload:
  workloads/performance/v1.json
- existing raw artifacts immutable

해야 할 일:

1. 현재 GitHub main HEAD를 확인한다.

2. 아래 파일을 직접 읽고 현재 구조를 파악한다.
   - docs/WBS.md
   - config/models/ornith-1.5-9b.json
   - config/runtime-lock.json
   - config/profiles/runtime-lanes.json
   - config/profiles/topologies.json
   - workloads/performance/v1.json
   - scripts/runtime_launcher.py
   - scripts/bench_harness.py
   - scripts/run_1gpu_litellm.py
   - WBS5와 연관된 다른 runner/config 파일이 있다면 필요한 만큼 확인

3. 현재 runner가 WBS5를 그대로 실행할 수 있는지 판단한다.

특히 확인:
- run_1gpu_litellm.py가 현재 C2에서 concurrency/v2.json을 hard-code하는가?
- performance/v1.json을 authoritative workload로 선택할 경로가 이미 존재하는가?
- runtime_launcher.py가 batch=512 / ubatch=128을 hard-code하는가?
- R1의 ubatch=256을 다른 invariant 변경 없이 전달할 방법이 있는가?
- candidate ID와 exact launch configuration을 raw config / planned-config / report에 남길 수 있는가?
- R0/R1/R2 각각 fresh experiment directory를 만들 수 있는가?
- 기존 raw artifact overwrite 방지가 유지되는가?

4. R0/R1/R2에 대해 **dry plan / command generation만** 검증한다.

실제 server에서 128K request를 보내거나 performance inference를 실행하면 안 된다.

가능하다면 코드 실행 없이 source-level로 plan을 비교하고,
필요하다면 safe preflight/help/version/checksum 수준만 사용한다.

R0 expected:
- TARGET
- --batch-size 512
- --ubatch-size 128
- performance/v1.json
- WBS4 validated serving invariants 그대로

R1 expected:
R0 대비 정확히 하나만 달라야 한다.
- --ubatch-size 128 -> 256

다른 llama-server argument가 하나라도 바뀌면 문제로 보고한다.

R2 expected:
R0 대비 정확히 lane만 달라야 한다.
- --spec-type none
  ->
  --spec-type ngram-simple

batch/ubatch/topology/KV/context 등은 R0와 같아야 한다.

5. pinned binary/source support를 확인한다.

확인할 항목:
- --ubatch-size가 pinned binary에서 지원되는가
- ngram-simple이 지원되는가
- pinned ngram-simple default size_n / size_m 값
- candidate별 effective command가 exact pinned image를 사용하는가
- CUDA Graph disable option 등을 새 candidate로 추가하지 말 것
- MTP/MTP_NGRAM을 다시 candidate로 추가하지 말 것

6. telemetry/evidence capture가 WBS5에 충분한지 점검한다.

최소 보존 대상:
- TTFT
- prefill tok/s
- mean request decode tok/s
- aggregate decode tok/s
- end-to-end output tok/s
- batch wall time
- actual output tokens/request
- peak VRAM GPU0/GPU1
- power
- temperature
- SM/memory clocks
- output integrity
- C2 active overlap / queue-only
- routing deployment/backend evidence
- post-health
- NGRAM candidate에서는 draft/generated/accepted/acceptance evidence

GPU peak는 현재 nvidia-smi memory.used 0.5s sampling이라는 limitation도 기록해야 한다.

7. warm-up policy를 확인한다.

현재 계약은:
- --no-warmup
- cold-independent
- full-size benchmark warm-up 없음
- C2 이전 short routing-preflight request만 허용

이를 임의 변경하지 않는다.

8. performance/v1.json 구조를 확인한다.

예상 계약:
- mode=performance
- C2 independent Project A/B
- context 131072
- max output 4096
- min output 1024
- temperature 0
- top_p 1
- seed 520
- diversified identifiers

이 workload를 변경하지 않는다.

9. 필요한 코드 수정이 있다면 직접 수정하지 말고,
먼저 “필수 수정안”으로 제시한다.

각 수정안마다:
- 파일
- 함수/구간
- 수정 이유
- 최소 변경 내용
- R0/R1/R2 중 영향을 받는 candidate
- 기존 WBS2/3/4 runner에 regression 가능성이 있는지
를 기록한다.

WBS5 전용 runner를 새로 만드는 것이 더 안전한지,
기존 runner에 명시적 performance/candidate override를 추가하는 것이 더 안전한지도 비교한다.

기준은:
- 기존 WBS2/3/4 behavior 보존
- raw artifact immutable
- candidate identity 명시
- workload identity 명시
- one-variable delta 보장
- 재현 가능한 exact command 보존

10. 최종 보고 형식:

A. 현재 main HEAD

B. R0 실행 가능성
- PASS / BLOCKED
- exact generated command
- 문제점

C. R1 실행 가능성
- PASS / BLOCKED
- R0와의 exact diff
- 문제점

D. R2 실행 가능성
- PASS / BLOCKED
- R0와의 exact diff
- 문제점

E. WBS5 runner gap
- 반드시 수정해야 하는 것
- 선택적으로 보강할 것
- 수정하면 안 되는 것

F. measured inference 전 체크리스트

G. 최종 판정
- READY_FOR_IMPLEMENTATION
- 또는 BLOCKED
중 하나

주의:
READY_FOR_IMPLEMENTATION은 “GPU benchmark 실행 가능”이라는 뜻이 아니다.
필요한 runner 변경을 구현할 준비가 됐다는 뜻이다.

이번 작업에서는:
- GPU measured inference 금지
- 128K full request 금지
- performance benchmark 금지
- 새 candidate 생성 금지
- recipe 확정 금지
