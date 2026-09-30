# R1-GRAPH-AUTO-MBT4096

Publication: 2026-09-30 · **VALIDATED_RECIPE — GRAPH_AUTO**

근거 experiment: `EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001`. [측정 report](../../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001.md) · [track review](../../docs/WBS-5.4.3.4-result-review.md#7-2026-09-30-r1-재측정-addendum) · [기계 판독 레코드](../../state/wbs5-final-recipes.json)

## 검증 범위

P520 2× Tesla V100-SXM2-16GB에서 요청당 131,072-token ceiling, 독립 Project A/B C2 active, 두 요청 mechanical output PASS, post-health healthy. 이 승격은 performance/v1 serving 검증에 한정하며 task-level semantic PASS나 C3+ 지원을 뜻하지 않는다.

Topology: `tp2-shared`. vLLM tensor parallel size 2, max-num-seqs 2.

## Model / runtime provenance

- Repository: `ornith-ai/Ornith-1.5-35B-A3B-NVFP4`
- Revision receipt: `94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa`
- Local artifact: `/srv/models/ornith-1.5-35b-a3b-nvfp4`
- Weight / KV: `NVFP4` / `fp8_e5m2`
- NVFP4 config/index/tokenizer 및 세 weight shard SHA256은 아래 exact artifact receipt에 수록.
- Runtime observed: `1.5.0`
- Runtime pin: `1cat_vllm-1.5.0-cp312-cp312-linux_x86_64.whl`
- Wheel SHA256: `2a4d6bee4e19d315b142f2c563059f3064ddeeca563a6bdc828c33e1073c825b`
- [측정 전 artifact 검증](../../results/raw/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001/runtime/artifact-check.json) · [runtime 사전 검사](../../results/raw/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001/runtime/preflight.json)

```json
{
  "path": "/srv/models/ornith-1.5-35b-a3b-nvfp4",
  "repository": "ornith-ai/Ornith-1.5-35B-A3B-NVFP4",
  "revision": "94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa",
  "files": {
    "config.json": {
      "expected": "319ee1293a279a57990fcfc18fdb533101ffaf264a990a7d0bcb1c3d24fc720d",
      "actual": "319ee1293a279a57990fcfc18fdb533101ffaf264a990a7d0bcb1c3d24fc720d",
      "revision": "94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa"
    },
    "model-00001-of-00003.safetensors": {
      "expected": "648fe83171485f4be03ea58d86089e088c94c2a3dc88922233f9002f30d8bc8b",
      "actual": "648fe83171485f4be03ea58d86089e088c94c2a3dc88922233f9002f30d8bc8b",
      "revision": "94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa"
    },
    "model-00002-of-00003.safetensors": {
      "expected": "cb5c5978721a1e87406ae68f1cd5a855326e40ff8bc13832644c392115336987",
      "actual": "cb5c5978721a1e87406ae68f1cd5a855326e40ff8bc13832644c392115336987",
      "revision": "94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa"
    },
    "model-00003-of-00003.safetensors": {
      "expected": "8303cef7d375021d69dcafc60d3fad5f8186995b18b0db5e2a609aadeb8a4f51",
      "actual": "8303cef7d375021d69dcafc60d3fad5f8186995b18b0db5e2a609aadeb8a4f51",
      "revision": "94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa"
    },
    "model.safetensors.index.json": {
      "expected": "52af7e400d0138ffde60f127fbf3ce494e6ebf682748f7e44545c25b68d28128",
      "actual": "52af7e400d0138ffde60f127fbf3ce494e6ebf682748f7e44545c25b68d28128",
      "revision": "94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa"
    },
    "tokenizer.json": {
      "expected": "5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42",
      "actual": "5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42",
      "revision": "94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa"
    },
    "tokenizer_config.json": {
      "expected": "5186f0defcd7f232382c7f0aebcd2252d073bb921ab240e407b7ae8745d2b29b",
      "actual": "5186f0defcd7f232382c7f0aebcd2252d073bb921ab240e407b7ae8745d2b29b",
      "revision": "94e431d9cc47fa1986a7a1a4e9a80f7f118b03aa"
    }
  }
}
```

## Serving configuration

- Speculative: `target-only`, depth `0`.
- Batch/ubatch: `N/A/N/A`; MBT/max-num-seqs: `4096/2`.
- Graph: auto path (`--enforce-eager` removed); capture/replay evidence is `UNKNOWN`.
- Configuration SHA256: `c55b59d814bd738ecc23a527e1cdd6255f920ef126048f7dbaec513136035429`.

### 실제 측정 launch command

아래 명령은 당시 snapshot 경로와 experiment 식별자를 포함한 원문이다. 재실행 시 해당 경로가 필요하며 기존 raw experiment를 덮어쓰지 않는다. 이 publication에서는 명령을 실행하지 않았다.

```bash
/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python -m vllm.entrypoints.openai.api_server --model /srv/models/ornith-1.5-35b-a3b-nvfp4 --served-model-name Ornith-1.5-35B-A3B --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 --gpu-memory-utilization 0.90 --host 127.0.0.1 --port 18080
```

### Environment

Host process environment와 Docker 내부 환경을 구분한다. Container defaults/실제 환경은 [resolved receipt](../../results/raw/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001/runtime/effective-environment.json)에 보존했다.

```json
{
  "host": [
    {
      "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
      "LANG": "C.UTF-8",
      "HOME": "/home/loopwhile",
      "CUDA_VISIBLE_DEVICES": "0,1",
      "VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL": "0",
      "PYTHONPATH": "/home/loopwhile/v100-llm-test-wbs5/a9c72cc919de/scripts/runtime_hooks"
    }
  ],
  "container_overrides": [
    {}
  ]
}
```

## Workload / measured performance

`workloads/performance/v1.json` SHA256 `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`. 요청당 output reserve 4,096 / min output 1,024, temperature 0 / top_p 1 / seed 520, thinking OFF / tool parser none. Cold-independent; full-size measured warmup 없음.

| Metric | Observed |
|---|---:|
| TTFT mean | 108.012 s |
| Prefill mean | 1484.145 tok/s |
| Mean request decode | 30.511 tok/s |
| Aggregate decode | 30.321 tok/s |
| End-to-end output | 22.164 tok/s |
| Batch wall | 218.774 s |
| Total output tokens | 4849 |
| Peak VRAM GPU0 / GPU1 | 14825 / 14825 MiB |

| Request | Prompt tokens (live tokenizer) | Output tokens | TTFT s | Prefill tok/s | Decode tok/s | Output verdict |
|---|---:|---:|---:|---:|---:|---|
| project-a | 126975 | 2915 | 157.263 | 807.403 | 47.463 | PASS |
| project-b | 126976 | 1934 | 58.761 | 2160.887 | 13.560 | PASS |

## Telemetry / integrity

VRAM peak sampled every 0.5s; power/temp/clocks sampled every 2s. TPS definitions unchanged.

| GPU | Power min–max W | Temperature min–max °C | SM clock min–max MHz | Memory clock min–max MHz | Samples |
|---|---:|---:|---:|---:|---:|
| 0 | 26.04–200.93 | 42–68 | 135–1200 | 877–877 | 218 |
| 1 | 26.52–188.79 | 40–63 | 135–1200 | 877–877 | 218 |

Peak VRAM은 sampled 값이며 순간 peak 전체를 보장하지 않는다. Runtime lifecycle telemetry는 startup/idle 구간을 포함할 수 있다.

Output integrity: **PASS (2/2)**. C2 resident/active=true, queue_only=false; post-health healthy. [Overlap evidence](../../results/raw/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001/overlap-evidence.json) · [Output 원문](../../results/raw/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001/requests.json) · [Post-health](../../results/raw/EXP-V100-WBS5-ORNITH35-ONECAT-R1-PERF-20260930-001/health-after.json).

## 제약 및 해석

- 2026-09-30 동일 R1 설정 재측정이 A/B mechanical output PASS, C2 active, queue=false, post-health healthy를 충족해 current final recipe로 승격했다.
- 2026-09-29 원측정의 Project B `FAIL_OUTPUT`(997 < 최소 1024 tokens)은 historical evidence로 보존한다.
- Graph capture/replay evidence는 두 R1 실행 모두 `UNKNOWN`이다. 따라서 이 recipe는 R1 serving configuration의 검증이며 CUDA Graph 자체의 speedup/capture hit를 증명하지 않는다.
- R0와 두 R1 실행은 output trajectory가 다르므로 aggregate decode 및 wall 차이를 순수 graph 효과로 분리하지 않는다.
- 이 recipe의 authoritative measured run은 2026-09-30 후속 실행 1회다. 반복 검증의 신뢰구간이나 전체 workload 우위를 주장하지 않는다.
- Mean request decode와 aggregate decode는 scheduling/overlap 및 output 길이의 영향을 받는다.
- Wheel SHA는 보존된 wheel receipt와 static review로 연결한다. 설치 package tree 전체가 wheel과 byte-identical하다는 독립 검증은 없다.
## Publication audit

[Frozen source](<../../docs/WBS-5 - Ornith 1.5 35B-A3B - 1Cat-vLLM.md>)의 candidate ID/delta/invariant와 일치한다. 전체 7개 track / 25개 candidate 및 28개 plan instance 대조 결과와 evidence SHA256은 [publication receipt](../../state/wbs5-final-recipes.json)에 기록했다.
