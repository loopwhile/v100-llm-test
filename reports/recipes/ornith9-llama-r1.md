# TARGET_UB256

Publication: 2026-09-29 · **VALIDATED_RECIPE — LONG_PREFILL_LATENCY_ORIENTED**

근거 experiment: `EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001`. [측정 report](../../reports/ornith-1.5-9b/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001.md) · [track review](../../docs/WBS-5.3.2.4-result-review.md) · [기계 판독 레코드](../../state/wbs5-final-recipes.json)

## 검증 범위

P520 2× Tesla V100-SXM2-16GB에서 요청당 131,072-token ceiling, 독립 Project A/B C2 active, 두 요청 mechanical output PASS, post-health healthy. 이 승격은 performance/v1 serving 검증에 한정하며 task-level semantic PASS나 C3+ 지원을 뜻하지 않는다.

Topology: `1gpu-x2-independent`. GPU별 독립 backend 1 slot + 필수 LiteLLM 단일 gateway.

## Model / runtime provenance

- Repository: `UNRESOLVED (null)`
- Revision receipt: `5957ee5dcb88e9a9f4cd9a23c649320d20a574cd`
- Local artifact: `/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf`
- Weight / KV: `Q6_K` / `FP16`
- GGUF SHA256: `79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480`
- Runtime observed: `version: 0.3.0-dev (build 10775, commit 67a17c17c)
built with GNU 11.4.0 for Linux x86_64`
- Runtime pin: `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`
- Runtime commit: `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`
- [측정 전 artifact 검증](../../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/runtime/artifact-check.json) · [runtime 사전 검사](../../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/runtime/preflight.json)

```json
{
  "path": "/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf",
  "expected": "79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480",
  "actual": "79a9925bb7771dea3530d57b185e97b9713a73a7c06bdb9804f7d019aa42f480"
}
```

## Serving configuration

- Speculative: `target-only`, depth `0`.
- Batch/ubatch: `512/256`; MBT/max-num-seqs: `N/A/N/A`.
- Graph: default enabled, disable override 없음; lifetime reuse 2849회. Measured-window graph hit 수와 동일시하지 않는다.
- Configuration SHA256: `c6933aca605c596224e45f7bfffff65405703b225e62d3dd74685de2c56331ab`.

### 실제 측정 launch command

아래 명령은 당시 snapshot 경로와 experiment 식별자를 포함한 원문이다. 재실행 시 해당 경로가 필요하며 기존 raw experiment를 덮어쓰지 않는다. 이 publication에서는 명령을 실행하지 않았다.

```bash
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/runtime/container-0.cid --label experiment=EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001 --rm --pull=never --name exp-v100-orn15-9b-llama-target-b512-ub256-1gpu2-c2-perf-20260928-001-backend-0 --label project=v100-llm-test --gpus device=0 -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/runtime/container-1.cid --label experiment=EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001 --rm --pull=never --name exp-v100-orn15-9b-llama-target-b512-ub256-1gpu2-c2-perf-20260928-001-backend-1 --label project=v100-llm-test --gpus device=1 -p 127.0.0.1:18081:8080 -v /srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --ctx-size 131072 --parallel 1 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/runtime/container-gateway.cid --label experiment=EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001 --rm --pull=never --name exp-v100-orn15-9b-llama-target-b512-ub256-1gpu2-c2-perf-20260928-001-gateway --label project=v100-llm-test --network host -v /home/loopwhile/v100-llm-test-wbs5-manual/416817e5f2a8-ornith9-llama-20260928/results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/runtime/litellm-config.yaml:/app/config.yaml:ro ghcr.io/berriai/litellm:v1.101.0 --config /app/config.yaml --host 127.0.0.1 --port 18079
```

### Environment

Host process environment와 Docker 내부 환경을 구분한다. Container defaults/실제 환경은 [resolved receipt](../../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/runtime/effective-environment.json)에 보존했다.

```json
{
  "host": [
    {
      "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
      "LANG": "C.UTF-8",
      "HOME": "/home/loopwhile"
    },
    {
      "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
      "LANG": "C.UTF-8",
      "HOME": "/home/loopwhile"
    },
    {
      "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
      "LANG": "C.UTF-8",
      "HOME": "/home/loopwhile"
    }
  ],
  "container_overrides": [
    {},
    {}
  ]
}
```

### 필수 LiteLLM gateway

Runtime: `1.101.0 / 18243cd7af4c3325165ba68b21379e2719e051c7`; image `ghcr.io/berriai/litellm:v1.101.0`. 단일 endpoint `http://127.0.0.1:18079`, least-busy, backend당 max_parallel_requests=1, num_retries=0. 짧은 routing preflight 후 routing-settled admission을 사용했다. [원본 gateway config](../../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/runtime/litellm-config.yaml).

```json
{
  "model_list": [
    {
      "model_name": "Ornith-1.5-9B",
      "model_info": {
        "id": "backend-0"
      },
      "litellm_params": {
        "model": "openai/Ornith-1.5-9B",
        "api_base": "http://127.0.0.1:18080/v1",
        "api_key": "local-no-key",
        "max_parallel_requests": 1,
        "timeout": 1800,
        "stream_timeout": 1800,
        "max_retries": 0
      }
    },
    {
      "model_name": "Ornith-1.5-9B",
      "model_info": {
        "id": "backend-1"
      },
      "litellm_params": {
        "model": "openai/Ornith-1.5-9B",
        "api_base": "http://127.0.0.1:18081/v1",
        "api_key": "local-no-key",
        "max_parallel_requests": 1,
        "timeout": 1800,
        "stream_timeout": 1800,
        "max_retries": 0
      }
    }
  ],
  "router_settings": {
    "routing_strategy": "least-busy",
    "num_retries": 0
  }
}
```

## Workload / measured performance

`workloads/performance/v1.json` SHA256 `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`. 요청당 output reserve 4,096 / min output 1,024, temperature 0 / top_p 1 / seed 520, thinking OFF / tool parser none. Cold-independent; full-size measured warmup 없음.

| Metric | Observed |
|---|---:|
| TTFT mean | 139.204 s |
| Prefill mean | 912.192 tok/s |
| Mean request decode | 43.987 tok/s |
| Aggregate decode | 80.895 tok/s |
| End-to-end output | 16.199 tok/s |
| Batch wall | 173.343 s |
| Total output tokens | 2808 |
| Peak VRAM GPU0 / GPU1 | 10945 / 10945 MiB |

| Request | Prompt tokens (live tokenizer) | Output tokens | TTFT s | Prefill tok/s | Decode tok/s | Output verdict |
|---|---:|---:|---:|---:|---:|---|
| project-a | 126975 | 1438 | 140.108 | 906.263 | 43.341 | PASS |
| project-b | 126976 | 1370 | 138.300 | 918.121 | 44.634 | PASS |

## Telemetry / integrity

VRAM peak sampled every 0.5s; power/temp/clocks sampled every 2s. TPS definitions unchanged.

| GPU | Power min–max W | Temperature min–max °C | SM clock min–max MHz | Memory clock min–max MHz | Samples |
|---|---:|---:|---:|---:|---:|
| 0 | 26.04–171.23 | 43–71 | 135–1200 | 877–877 | 133 |
| 1 | 26.52–168.75 | 40–65 | 135–1200 | 877–877 | 133 |

Peak VRAM은 sampled 값이며 순간 peak 전체를 보장하지 않는다. Runtime lifecycle telemetry는 startup/idle 구간을 포함할 수 있다.

Output integrity: **PASS (2/2)**. C2 resident/active=true, queue_only=false; post-health healthy. [Overlap evidence](../../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/overlap-evidence.json) · [Output 원문](../../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/requests.json) · [Post-health](../../results/raw/EXP-V100-ORN15-9B-LLAMA-TARGET-B512-UB256-1GPU2-C2-PERF-20260928-001/health-after.json).

## 제약 및 해석

- R0 대비 TTFT -23.52%, prefill +30.73%, wall -19.71%, mean request decode +0.40%.
- 원본 repository는 UNRESOLVED/null이다. 기록된 revision과 local GGUF SHA256에 한정해 검증했으며 다운로드 가능한 upstream provenance의 완결성을 주장하지 않는다.
- LiteLLM 단일 endpoint가 필수다. 별도 backend 직접 분배는 이 recipe의 acceptance 경로가 아니다.
- 이 recipe의 유효 measured run은 1회다. 반복 검증의 신뢰구간이나 전체 workload에 대한 우위를 주장하지 않는다.
- Mean request decode와 aggregate decode는 scheduling/overlap 및 서로 다른 output 길이의 영향을 받는다. Aggregate decode를 순수 kernel 속도나 mean × concurrency로 해석하지 않는다.
- Preflight의 artifact/CLI/runner 검증과 measured startup/output/overlap으로 승격했다. Runtime route/graph/cache 중 직접 증명되지 않은 항목은 UNKNOWN으로 유지한다.

## Publication audit

[Frozen source](<../../docs/WBS-5 - Ornith 1.5 9B - llama.cpp.md>)의 candidate ID/delta/invariant와 일치한다. 전체 7개 track / 25개 candidate 및 28개 plan instance 대조 결과와 evidence SHA256은 [publication receipt](../../state/wbs5-final-recipes.json)에 기록했다.
