# EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260928-001

## 실험 식별 정보

- 실행 일시: 2026-09-29T10:00:38.255034+00:00
- 판정: **FAIL_OUTPUT**
- 모델: Ornith-1.5-35B-A3B
- 런타임: 1Cat-vLLM
- Runtime revision: 1.5.0 wheel sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b

## 서빙 설정

- Weight: NVFP4
- KV: fp8_e5m2
- Speculative: target-only
- ngram: N/A
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C2
- Prefix cache: cold-independent
- measured_repetitions: 1
- WBS5 candidate: R1-GRAPH-AUTO-MBT4096 (R1)
- Authoritative workload: /home/loopwhile/v100-llm-test-wbs5/8b0c43079ad9/workloads/performance/v1.json (SHA256 e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca)
- Exact launch configuration:
```sh
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-35b-a3b-nvfp4 --served-model-name Ornith-1.5-35B-A3B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.90 --host 127.0.0.1 --port 18080
```

## Capacity / Concurrency

- C2 resident: true
- C2 active: true
- Queue only: false
- Overlap source: 1Cat-vLLM server metrics/slots sampler
- Submission skew: 0.005s (routing-settled admission stagger)

## 성능 결과

- TTFT: 109215.34295650054
- Prefill tok/s: 1459.6692180089922
- Mean request decode tok/s: 51.39581868634034
- Aggregate decode tok/s: 23.340141095219767
- End-to-end output tok/s: 16.505328504912484
- Batch wall: 205.02469847799875
- Peak VRAM: GPU0 14,921 MiB / GPU1 14,921 MiB
- Peak VRAM sampling: nvidia-smi memory.used sampled every 0.5s; transient peaks between samples may be missed.


## Speculative evidence

- Draft tokens: None
- Accepted tokens: None
- Acceptance ratio: None
- Verification steps: None
- Counters: backend-level /metrics deltas across the measured request window.
## 증거 경로

- Raw artifact: results/raw/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260928-001
- Evidence files: config.json, identity.json, workload.json, payloads.json, tokenization.json, requests.json, overlap-evidence.json, metrics.json, completion.json, gpu-peak.json, health-before.json, health-after.json, server-before.json, server-after.json, speculative-evidence.json
- Runtime files: runtime/planned-config.json, runtime/server-0.log, runtime/measurement.log, runtime/cleanup.json, runtime/exit.json, runtime/preflight.json

## 결론

이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
