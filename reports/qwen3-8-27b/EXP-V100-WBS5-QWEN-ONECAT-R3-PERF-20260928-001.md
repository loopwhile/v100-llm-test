# EXP-V100-WBS5-QWEN-ONECAT-R3-PERF-20260928-001

## 실험 식별 정보

- 실행 일시: 2026-09-29T07:03:09.880470+00:00
- 판정: **QUEUE_ONLY**
- 모델: Qwen3.8-27B
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
- WBS5 candidate: R3-E5M2-128K-KV-ROUTE (R3)
- Authoritative workload: /home/loopwhile/v100-llm-test-wbs5/6cc8afdf5858/workloads/performance/v1.json (SHA256 e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca)
- Exact launch configuration:
```sh
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --enforce-eager --language-model-only --host 127.0.0.1 --port 18080
```

## Capacity / Concurrency

- C2 resident: false
- C2 active: false
- Queue only: true
- Overlap source: 1Cat-vLLM server metrics/slots sampler
- Submission skew: 0.005s (routing-settled admission stagger)
- Server sampler: peak processing 1 / peak waiting 1 (9,949 samples). 따라서 두 요청의 동시 처리 evidence는 없다.
- Request evidence: project-a 126,975 prompt / 3,692 output tokens; project-b 126,976 prompt / 4,096 output tokens. 두 요청의 harness verdict는 PASS다.

## 성능 결과

- TTFT: 470113.0824769998
- Prefill tok/s: 457.9685714686759
- Mean request decode tok/s: 9.490280022747811
- Aggregate decode tok/s: 7.855785111867246
- End-to-end output tok/s: 6.711449537574053
- Batch wall: 1160.4050595029998
- Peak VRAM: GPU0 16,117 MiB / GPU1 16,117 MiB
- Peak VRAM sampling: nvidia-smi memory.used sampled every 0.5s; transient peaks between samples may be missed.


## Output / candidate evidence

- Target-only 실행이며 speculative counters는 `UNKNOWN`이다.
- `wbs5-evidence.json`의 mechanical output verdict는 `PASS` (합계 7,788 tokens)다. Task-level semantic correctness는 별도 검토 전이므로 미판정이다.
- R0 대비 normalized delta는 KV dtype `fp8_e4m3` → `fp8_e5m2` 하나다. `graph-evidence.json`은 `UNKNOWN`이며 R3는 eager 설정이다.
- 관측한 성능값은 queue-only 배치 수치다. C2 ACTIVE 처리량이나 E5M2 final recipe 이득으로 해석하지 않는다.

## 증거 경로

- Raw artifact: results/raw/EXP-V100-WBS5-QWEN-ONECAT-R3-PERF-20260928-001
- Evidence files: config.json, identity.json, workload.json, payloads.json, tokenization.json, requests.json, overlap-evidence.json, metrics.json, completion.json, gpu-peak.json, health-before.json, health-after.json, server-before.json, server-after.json, speculative-evidence.json, wbs5-evidence.json, graph-evidence.json
- Runtime files: runtime/planned-config.json, runtime/server-0.log, runtime/measurement.log, runtime/cleanup.json, runtime/exit.json, runtime/preflight.json, runtime/gpu-telemetry.jsonl

## 결론

R3는 두 long-context 요청을 순차 처리했으며 C2 ACTIVE 요건을 충족하지 못했다. Task-level acceptance와 recipe 승격은 5.4.1.5 review에서 판단한다. 이 보고서는 해당 실험의 raw evidence에 한정한다.
