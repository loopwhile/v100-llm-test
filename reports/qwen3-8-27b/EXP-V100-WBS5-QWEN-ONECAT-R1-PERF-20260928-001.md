# EXP-V100-WBS5-QWEN-ONECAT-R1-PERF-20260928-001

## 실험 식별 정보

- 실행 일시: 완료 시각 미기록 (identity 생성: 2026-09-29T06:37:44.978948+00:00)
- 판정: **FAIL_STARTUP**
- 모델: Qwen3.8-27B
- 런타임: 1Cat-vLLM
- Runtime revision: 1.5.0 wheel sha256:2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b

## 서빙 설정

- Weight: NVFP4
- KV: fp8_e4m3
- Speculative: target-only
- ngram: N/A
- Topology: tp2-shared
- Context per agent: 131072
- Concurrency: C2
- Prefix cache: cold-independent
- measured_repetitions: 1
- WBS5 candidate: R1-E4M3-128K-CUDAGRAPH-C1 (R1)
- Authoritative workload: /home/loopwhile/v100-llm-test-wbs5/6cc8afdf5858/workloads/performance/v1.json (SHA256 e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca)
- Exact launch configuration:
```sh
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4 --served-model-name Qwen3.8-27B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e4m3 --max-model-len 131072 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.92 --language-model-only --host 127.0.0.1 --port 18080 --compilation-config '{"cudagraph_capture_sizes":[1]}'
```

## Capacity / Concurrency

- C2 resident: 측정 없음
- C2 active: 측정 없음
- Queue only: 측정 없음
- 서버 시작 전 종료돼 C1/C2 측정 요청과 overlap 관측값은 없다.

## 성능 결과

- TTFT / prefill / decode / batch wall / measured peak VRAM: 측정 없음.


## Startup failure / graph evidence

- R0 대비 frozen delta: `--enforce-eager` 제거와 `--compilation-config '{"cudagraph_capture_sizes":[1]}'` 추가.
- `runtime/server-0.log`: EngineCore 초기화의 Torch Inductor compile 중 GPU0에서 CUDA OOM. 1.19 GiB allocation 시점에 free 911.50 MiB였다.
- `graph-evidence.json`은 `UNKNOWN`; capture/replay 성공은 확인되지 않았다. Startup failure로 인해 출력 무결성과 C1/C2 capacity도 판정할 수 없다.

## 증거 경로

- Raw artifact: results/raw/EXP-V100-WBS5-QWEN-ONECAT-R1-PERF-20260928-001
- Evidence files: config.json, identity.json, metrics.json, completion.json, speculative-evidence.json, wbs5-evidence.json, graph-evidence.json
- Runtime files: runtime/planned-config.json, runtime/server-0.log, runtime/cleanup.json, runtime/exit.json, runtime/preflight.json, runtime/gpu-telemetry.jsonl
- Failure reason: server exited during startup

## 결론

R1은 startup 단계에서 종료되어 measured performance와 graph 이득을 판단할 수 없다. 이 보고서는 해당 실험의 raw evidence에 한정한다.
