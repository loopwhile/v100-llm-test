# Q38-LLAMA-WBS5-R2-TARGET-UB256

Publication: 2026-09-29 · **VALIDATED_RECIPE — LONG_PREFILL_LATENCY_ORIENTED**

근거 experiment: `EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001`. [측정 report](../../reports/qwen3-8-27b/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001.md) · [track review](../../docs/WBS-5.3.1.7-result-review.md) · [기계 판독 레코드](../../state/wbs5-final-recipes.json)

## 검증 범위

P520 2× Tesla V100-SXM2-16GB에서 요청당 131,072-token ceiling, 독립 Project A/B C2 active, 두 요청 mechanical output PASS, post-health healthy. 이 승격은 performance/v1 serving 검증에 한정하며 task-level semantic PASS나 C3+ 지원을 뜻하지 않는다.

Topology: `tp2-shared`. 실제 llama.cpp 구현은 `--split-mode layer --tensor-split 1,1`이다.

## Model / runtime provenance

- Repository: `unsloth/Qwen3.8-27B-GGUF`
- Revision receipt: `4ca720788d1e01f1bff70c033e0d0028fd02e502`
- Local artifact: `/srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf`
- Weight / KV: `UD-Q4_K_M` / `Q8_0`
- GGUF SHA256: `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`
- Runtime observed: `version: 0.3.0-dev (build 10775, commit 67a17c17c)
built with GNU 11.4.0 for Linux x86_64`
- Runtime pin: `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`
- Runtime commit: `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`
- [측정 전 artifact 검증](../../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/runtime/artifact-check.json) · [runtime 사전 검사](../../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/runtime/preflight.json)

```json
{
  "path": "/srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf",
  "expected": "322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482",
  "actual": "322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482"
}
```

## Serving configuration

- Speculative: `target-only`, depth `0`.
- Batch/ubatch: `512/256`; MBT/max-num-seqs: `N/A/N/A`.
- Graph: default enabled, disable override 없음; lifetime reuse 4339회. Measured-window graph hit 수와 동일시하지 않는다.
- Configuration SHA256: `7bb2031d35687846839c27cd0d6d87649280a97dbaf015cc1bb57ac9fdfd6d9c`.

### 실제 측정 launch command

아래 명령은 당시 snapshot 경로와 experiment 식별자를 포함한 원문이다. 재실행 시 해당 경로가 필요하며 기존 raw experiment를 덮어쓰지 않는다. 이 publication에서는 명령을 실행하지 않았다.

```bash
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5-manual-45ee01cb2d9e/results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/runtime/container-0.cid --label experiment=EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001 --rm --pull=never --name exp-v100-wbs5-qwen-llama-r2-perf-20260928-001-backend-0 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/qwen3.8-unsloth/Qwen3.8-27B-UD-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### Environment

Host process environment와 Docker 내부 환경을 구분한다. Container defaults/실제 환경은 [resolved receipt](../../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/runtime/effective-environment.json)에 보존했다.

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
| TTFT mean | 679.053 s |
| Prefill mean | 264.112 tok/s |
| Mean request decode | 5.593 tok/s |
| Aggregate decode | 4.514 tok/s |
| End-to-end output | 3.457 tok/s |
| Batch wall | 1337.272 s |
| Total output tokens | 4623 |
| Peak VRAM GPU0 / GPU1 | 13447 / 14533 MiB |

| Request | Prompt tokens (live tokenizer) | Output tokens | TTFT s | Prefill tok/s | Decode tok/s | Output verdict |
|---|---:|---:|---:|---:|---:|---|
| project-a | 126975 | 2653 | 1044.977 | 121.525 | 9.076 | PASS |
| project-b | 126976 | 1970 | 313.129 | 406.699 | 2.109 | PASS |

## Telemetry / integrity

VRAM peak sampled every 0.5s; power/temp/clocks sampled every 2s. TPS definitions unchanged.

| GPU | Power min–max W | Temperature min–max °C | SM clock min–max MHz | Memory clock min–max MHz | Samples |
|---|---:|---:|---:|---:|---:|
| 0 | 26.52–216.3 | 44–72 | 135–1200 | 877–877 | 653 |
| 1 | 27.02–202.69 | 41–63 | 135–1200 | 877–877 | 653 |

Peak VRAM은 sampled 값이며 순간 peak 전체를 보장하지 않는다. Runtime lifecycle telemetry는 startup/idle 구간을 포함할 수 있다.

Output integrity: **PASS (2/2)**. C2 resident/active=true, queue_only=false; post-health healthy. [Overlap evidence](../../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/overlap-evidence.json) · [Output 원문](../../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/requests.json) · [Post-health](../../results/raw/EXP-V100-WBS5-QWEN-LLAMA-R2-PERF-20260928-001/health-after.json).

## 제약 및 해석

- R0 두 반복 대비 TTFT 약 24.7~24.9%, wall 약 13.2~15.4% 감소. Decode는 유지 + 약한 개선 신호다.
- llama slot sampler 누락은 보존된 server log의 task overlap으로 보정됐다. log-overlap-evidence.json과 원래 sampler evidence를 함께 참조한다.
- WBS7 native MTP/GQA2 결과는 이 frozen recipe에 포함하지 않는다.
- 이 recipe의 유효 measured run은 1회다. 반복 검증의 신뢰구간이나 전체 workload에 대한 우위를 주장하지 않는다.
- Mean request decode와 aggregate decode는 scheduling/overlap 및 서로 다른 output 길이의 영향을 받는다. Aggregate decode를 순수 kernel 속도나 mean × concurrency로 해석하지 않는다.
- Preflight의 artifact/CLI/runner 검증과 measured startup/output/overlap으로 승격했다. Runtime route/graph/cache 중 직접 증명되지 않은 항목은 UNKNOWN으로 유지한다.

## Publication audit

[Frozen source](<../../docs/WBS-5 - Qwen 3.8 27B - llama.cpp.md>)의 candidate ID/delta/invariant와 일치한다. 전체 7개 track / 25개 candidate 및 28개 plan instance 대조 결과와 evidence SHA256은 [publication receipt](../../state/wbs5-final-recipes.json)에 기록했다.
