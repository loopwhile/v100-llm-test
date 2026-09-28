# EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002

## 실험 식별 정보

- 실행 일시: 2026-09-28T09:40:21.082469+00:00
- 판정: **PASS_C2_ACTIVE**
- 모델: Qwen3.8-27B
- 런타임: llama.cpp
- Runtime revision: 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb

## 서빙 설정

- Weight: UD-Q4_K_M
- KV: Q8_0
- Speculative: target-only
- ngram: off
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C2
- Prefix cache: cold-independent
- measured_repetitions: 1
- WBS5 candidate: Q38-LLAMA-WBS5-R0-TARGET-B512-UB128 (R0)
- Authoritative workload: /home/loopwhile/v100-llm-test-wbs5-manual-45ee01cb2d9e/workloads/performance/v1.json (SHA256 e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca)
- Exact launch configuration:
```sh
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5-manual-45ee01cb2d9e/results/raw/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002/runtime/container-0.cid --label experiment=EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002 --rm --pull=never --name exp-v100-wbs5-qwen-llama-r0-perf-20260928-002-backend-0 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

## Capacity / Concurrency

- C2 resident: true
- C2 active: true
- Queue only: false
- Overlap source: llama.cpp server metrics/slots sampler + llama.cpp server-log decode interleaving fallback
- Submission skew: 0.005s (routing-settled admission stagger)

## 성능 결과

- TTFT: 904118.8030390004
- Prefill tok/s: 178.2297101865325
- Mean request decode tok/s: 5.3847668118595395
- Aggregate decode tok/s: 3.9580385293631517
- End-to-end output tok/s: 2.7323120833581394
- Batch wall: 1580.3465593479996
- Peak VRAM: GPU0 13,159 MiB / GPU1 14,245 MiB
- Peak VRAM sampling: nvidia-smi memory.used sampled every 0.5s; transient peaks between samples may be missed.


## Speculative evidence

- Draft tokens: 0.0
- Accepted tokens: 0.0
- Acceptance ratio: None
- Verification steps: None
- Counters: backend-level /metrics deltas across the measured request window.
## 증거 경로

- Raw artifact: results/raw/EXP-V100-WBS5-QWEN-LLAMA-R0-PERF-20260928-002
- Evidence files: config.json, identity.json, workload.json, payloads.json, tokenization.json, requests.json, overlap-evidence.json, metrics.json, completion.json, gpu-peak.json, health-before.json, health-after.json, server-before.json, server-after.json, speculative-evidence.json
- Runtime files: runtime/planned-config.json, runtime/server-0.log, runtime/measurement.log, runtime/cleanup.json, runtime/exit.json, runtime/preflight.json

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
