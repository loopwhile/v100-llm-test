# ORN35-LLAMA-WBS5-R2-UB256

Publication: 2026-09-29 · **VALIDATED_RECIPE — LONG_PREFILL_LATENCY_ORIENTED**

근거 experiment: `EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001`. [측정 report](../../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001.md) · [track review](../../docs/WBS-5.3.3.5-result-review.md) · [기계 판독 레코드](../../state/wbs5-final-recipes.json)

## 검증 범위

P520 2× Tesla V100-SXM2-16GB에서 요청당 131,072-token ceiling, 독립 Project A/B C2 active, 두 요청 mechanical output PASS, post-health healthy. 이 승격은 performance/v1 serving 검증에 한정하며 task-level semantic PASS나 C3+ 지원을 뜻하지 않는다.

Topology: `tp2-shared`. 실제 llama.cpp 구현은 `--split-mode layer --tensor-split 1,1`이다.

## Model / runtime provenance

- Repository: `ornith-ai/Ornith-1.5-35B-A3B-GGUF`
- Revision receipt: `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`
- Local artifact: `/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf`
- Weight / KV: `Q4_K_M` / `Q8_0`
- GGUF SHA256: `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`
- Runtime observed: `version: 0.3.0-dev (build 10775, commit 67a17c17c)
built with GNU 11.4.0 for Linux x86_64`
- Runtime pin: `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`
- Runtime commit: `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`
- [측정 전 artifact 검증](../../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/runtime/artifact-check.json) · [runtime 사전 검사](../../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/runtime/preflight.json)

```json
{
  "path": "/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf",
  "expected": "42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f",
  "actual": "42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f"
}
```

## Serving configuration

- Speculative: `target-only`, depth `0`.
- Batch/ubatch: `512/256`; MBT/max-num-seqs: `N/A/N/A`.
- Graph: default enabled, disable override 없음; lifetime reuse 4396회. Measured-window graph hit 수와 동일시하지 않는다.
- Configuration SHA256: `4252ccbe93e014a972be06ebe6d046af998493fecb7472c9ec665d0df3a2aad1`.

### 실제 측정 launch command

아래 명령은 당시 snapshot 경로와 experiment 식별자를 포함한 원문이다. 재실행 시 해당 경로가 필요하며 기존 raw experiment를 덮어쓰지 않는다. 이 publication에서는 명령을 실행하지 않았다.

```bash
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5/e2e2e97450cb/results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/runtime/container-0.cid --label experiment=EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001 --rm --pull=never --name exp-v100-wbs5-ornith35-llama-r2-perf-20260928-001-backend-0 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### Environment

Host process environment와 Docker 내부 환경을 구분한다. Container defaults/실제 환경은 [resolved receipt](../../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/runtime/effective-environment.json)에 보존했다.

```json
{
  "host": [
    {
      "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
      "LANG": "C.UTF-8",
      "HOME": "/home/loopwhile"
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
| TTFT mean | 670.091 s |
| Prefill mean | 229.750 tok/s |
| Mean request decode | 15.697 tok/s |
| Aggregate decode | 7.228 tok/s |
| End-to-end output | 4.505 tok/s |
| Batch wall | 1038.990 s |
| Total output tokens | 4681 |
| Peak VRAM GPU0 / GPU1 | 13103 / 12581 MiB |

| Request | Prompt tokens (live tokenizer) | Output tokens | TTFT s | Prefill tok/s | Decode tok/s | Output verdict |
|---|---:|---:|---:|---:|---:|---|
| project-a | 126975 | 1832 | 948.907 | 133.830 | 26.995 | PASS |
| project-b | 126976 | 2849 | 391.274 | 325.671 | 4.398 | PASS |

## Telemetry / integrity

VRAM peak sampled every 0.5s; power/temp/clocks sampled every 2s. TPS definitions unchanged.

| GPU | Power min–max W | Temperature min–max °C | SM clock min–max MHz | Memory clock min–max MHz | Samples |
|---|---:|---:|---:|---:|---:|
| 0 | 26.52–138.32 | 44–62 | 135–1200 | 877–877 | 517 |
| 1 | 27–138.79 | 41–56 | 135–1200 | 877–877 | 517 |

Peak VRAM은 sampled 값이며 순간 peak 전체를 보장하지 않는다. Runtime lifecycle telemetry는 startup/idle 구간을 포함할 수 있다.

Output integrity: **PASS (2/2)**. C2 resident/active=true, queue_only=false; post-health healthy. [Overlap evidence](../../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/overlap-evidence.json) · [Output 원문](../../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/requests.json) · [Post-health](../../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/health-after.json).

## 제약 및 해석

- R0 대비 prefill +20.03%, TTFT -15.33%, wall -11.68%; GPU당 peak +272 MiB. Decode 가속을 주장하지 않는다.
- R1 native MTP1과 결합한 설정 및 효과의 가산성은 검증하지 않았다.
- 이 recipe의 유효 measured run은 1회다. 반복 검증의 신뢰구간이나 전체 workload에 대한 우위를 주장하지 않는다.
- Mean request decode와 aggregate decode는 scheduling/overlap 및 서로 다른 output 길이의 영향을 받는다. Aggregate decode를 순수 kernel 속도나 mean × concurrency로 해석하지 않는다.
- Preflight의 artifact/CLI/runner 검증과 measured startup/output/overlap으로 승격했다. Runtime route/graph/cache 중 직접 증명되지 않은 항목은 UNKNOWN으로 유지한다.

## Publication audit

[Frozen source](<../../docs/WBS-5 - Ornith 1.5 35B-A3B - llama.cpp.md>)의 candidate ID/delta/invariant와 일치한다. 전체 7개 track / 25개 candidate 및 28개 plan instance 대조 결과와 evidence SHA256은 [publication receipt](../../state/wbs5-final-recipes.json)에 기록했다.
