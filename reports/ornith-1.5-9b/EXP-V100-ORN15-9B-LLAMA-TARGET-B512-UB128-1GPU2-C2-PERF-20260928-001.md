# EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001

## 실험 식별 정보

- 실행 일시: 2026-09-28T12:48:37.150851+00:00
- 판정: **PASS_C2_ACTIVE**
- 모델: Ornith-1.5-9B
- 런타임: llama.cpp
- Runtime revision: 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
- Gateway runtime: LiteLLM
- Gateway revision: 1.101.0 / 18243cd7af4c3325165ba68b21379e2719e051c7
- Gateway image: ghcr.io/berriai/litellm:v1.101.0
- Gateway endpoint: http://127.0.0.1:18079
- Gateway routing: least-busy
- Gateway backend max parallel: 1

## 서빙 설정

- Weight: Q6_K
- KV: FP16
- Speculative: target-only
- ngram: off
- Topology: 1gpu-x2-independent
- Context per agent: 131072
- Concurrency: C2
- Prefix cache: cold-independent
- measured_repetitions: 1
- WBS5 candidate: TARGET_BASELINE (R0)
- Authoritative workload: /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/workloads/performance/v1.json (SHA256 e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca)
- Exact launch configuration:
```sh
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001/runtime/container-0.cid --label experiment=EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001 --rm --pull=never --name exp-v100-orn15-9b-llama-target-b512-ub128-1gpu2-c2-perf-20260928-001-backend-0 --label project=v100-llm-test --gpus device=0 -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001/runtime/container-1.cid --label experiment=EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001 --rm --pull=never --name exp-v100-orn15-9b-llama-target-b512-ub128-1gpu2-c2-perf-20260928-001-backend-1 --label project=v100-llm-test --gpus device=1 -p 127.0.0.1:18081:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001/runtime/container-gateway.cid --label experiment=EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001 --rm --pull=never --name exp-v100-orn15-9b-llama-target-b512-ub128-1gpu2-c2-perf-20260928-001-gateway --label project=v100-llm-test --network host -v /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001/runtime/litellm-config.yaml:/app/config.yaml:ro ghcr.io/berriai/litellm:v1.101.0 --config /app/config.yaml --host 127.0.0.1 --port 18079
```

## Capacity / Concurrency

- C2 resident: true
- C2 active: true
- Queue only: false
- Overlap source: LiteLLM single gateway endpoint + backend runtime probes + deployment response headers
- Submission skew: 0.279s (routing-settled admission stagger)
- Routing preflight before measurement: true (2 short requests, max_tokens=16)
- Warmup: no full-size benchmark warmup (one measured 128K batch)

## 성능 결과

- TTFT: 182019.74704450002
- Prefill tok/s: 697.742014063411
- Mean request decode tok/s: 43.81319166249719
- Aggregate decode tok/s: 77.72594281484913
- End-to-end output tok/s: 13.034080743329922
- Batch wall: 215.89554763499837
- Peak VRAM: GPU0 10,893 MiB / GPU1 10,893 MiB
- Peak VRAM sampling: nvidia-smi memory.used sampled every 0.5s; transient peaks between samples may be missed.


## Speculative evidence

- Draft tokens: 0.0
- Accepted tokens: 0.0
- Acceptance ratio: None
- Verification steps: None
- Counters: backend-level /metrics deltas across the measured request window.
## 증거 경로

- Raw artifact: /home/loopwhile/Data/Workspace_VSCode/v100-llm-test/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB128-1GPU2-C2-PERF-20260928-001
- Evidence files: config.json, identity.json, workload.json, payloads.json, tokenization.json, requests.json, overlap-evidence.json, metrics.json, completion.json, gpu-peak.json, health-before.json, health-after.json, server-before.json, server-after.json, speculative-evidence.json
- Runtime files: runtime/routing-preflight.json, runtime/litellm-config.yaml, runtime/plan.json, runtime/planned-config.json, runtime/server-0.log, runtime/server-1.log, runtime/gateway.log, runtime/measurement.log, runtime/gpu-peak-lifecycle.json, runtime/cleanup.json, runtime/exit.json, runtime/progress.json, runtime/preflight.json

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
- WBS4 수치는 topology/capacity evidence이며, 정식 performance ranking은 WBS5 performance workload에서 다시 측정한다.
