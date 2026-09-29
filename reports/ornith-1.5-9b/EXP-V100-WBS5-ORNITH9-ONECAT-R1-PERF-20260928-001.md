# EXP-V100-WBS5-ORNITH9-ONECAT-R1-PERF-20260928-001

## 실험 식별 정보

- 실행 일시: 2026-09-29T08:49:28.135791+00:00
- 판정: **FAIL_OUTPUT** (performance diagnostic; G0 semantic FAIL)
- 모델: Ornith-1.5-9B
- 런타임: 1Cat-vLLM
- Runtime revision: 1.5.0 wheel sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b

## 서빙 설정

- Weight: NVFP4
- KV: FP16
- Speculative: MTP
- ngram: N/A
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C2
- Prefix cache: cold-independent
- measured_repetitions: 1
- WBS5 candidate: ORN15-9B-1CAT-WBS5-R1-MBT8192 (R1)
- Authoritative workload: /home/loopwhile/v100-llm-test-wbs5/8b0c43079ad9/workloads/performance/v1.json (SHA256 e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca)
- Exact launch configuration:
```sh
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-9b-nvfp4 --served-model-name Ornith-1.5-9B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype float16 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 8192 --gpu-memory-utilization 0.90 --enforce-eager --speculative-config '{"method":"mtp","num_speculative_tokens":1,"attention_backend":"TRITON_ATTN"}' --host 127.0.0.1 --port 18080
```

## Capacity / Concurrency

- C2 resident: true
- C2 active: true
- Queue only: false
- Overlap source: 1Cat-vLLM server metrics/slots sampler
- Submission skew: 0.005s (routing-settled admission stagger)

## 성능 결과

- TTFT: 299384.6081284991
- Prefill tok/s: 424.1282423513575
- Mean request decode tok/s: 10.014220067177494
- Aggregate decode tok/s: 14.852740934791967
- End-to-end output tok/s: 5.603548047913886
- Batch wall: 478.98224072500125
- Peak VRAM: GPU0 13,995 MiB / GPU1 13,995 MiB
- Peak VRAM sampling: nvidia-smi memory.used sampled every 0.5s; transient peaks between samples may be missed.


## Speculative evidence

- Draft tokens: 1552.0
- Accepted tokens: 1131.0
- Acceptance ratio: 0.7287371134020618
- Verification steps: None
- Counters: backend-level /metrics deltas across the measured request window.
## 증거 경로

- Raw artifact: results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-R1-PERF-20260928-001
- Evidence files: config.json, identity.json, workload.json, payloads.json, tokenization.json, requests.json, overlap-evidence.json, metrics.json, completion.json, gpu-peak.json, health-before.json, health-after.json, server-before.json, server-after.json, acceptance-review.json, speculative-evidence.json
- Runtime files: runtime/planned-config.json, runtime/server-0.log, runtime/measurement.log, runtime/cleanup.json, runtime/exit.json, runtime/preflight.json

## 결론 및 Semantic Audit

- **Output Integrity**: Project A PASS; Project B FAIL_OUTPUT in performance/v1. G0 semantic admission also failed.
- **실패 원인 및 진단 요약**: Performance observations are diagnostic only; final recipe promotion remains blocked by G0 and output integrity.
- 상세 감사 기록: `results/raw/EXP-V100-WBS5-ORNITH9-ONECAT-R1-PERF-20260928-001/acceptance-review.json`
- 이 보고서는 해당 실험의 raw evidence에 한정한다. 다른 runtime/model/context/concurrency로 결과를 일반화하지 않는다.
