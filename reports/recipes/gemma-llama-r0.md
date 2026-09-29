# G4-LCPP-WBS5-R0-TARGET-B512-UB128

Publication: 2026-09-29 · **VALIDATED_RECIPE — BASELINE**

근거 experiment: `EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001`. [측정 report](../../reports/gemma4-26b-a4b/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001.md) · [track review](../../docs/WBS-5.3.4.6-result-review.md) · [기계 판독 레코드](../../state/wbs5-final-recipes.json)

## 검증 범위

P520 2× Tesla V100-SXM2-16GB에서 요청당 131,072-token ceiling, 독립 Project A/B C2 active, 두 요청 mechanical output PASS, post-health healthy. 이 승격은 performance/v1 serving 검증에 한정하며 task-level semantic PASS나 C3+ 지원을 뜻하지 않는다.

Topology: `tp2-shared`. 실제 llama.cpp 구현은 `--split-mode layer --tensor-split 1,1`이다.

## Model / runtime provenance

- Repository: `unsloth/gemma-4-26B-A4B-it-qat-GGUF`
- Revision receipt: `7b92b5b28818151e8669af2e45e88d6086f490dd`
- Local artifact: `/srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf`
- Weight / KV: `UD-Q4_K_XL` / `FP16`
- GGUF SHA256: `a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891`
- Runtime observed: `version: 0.3.0-dev (build 10775, commit 67a17c17c)
built with GNU 11.4.0 for Linux x86_64`
- Runtime pin: `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`
- Runtime commit: `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`
- [측정 전 artifact 검증](../../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/runtime/artifact-check.json) · [runtime 사전 검사](../../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/runtime/preflight.json)

```json
{
  "path": "/srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf",
  "expected": "a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891",
  "actual": "a7c5bc715f5ff8e99a3e8901ce7d2b42b402c669bf24f7c5250747633d0f5891"
}
```

## Serving configuration

- Speculative: `target-only`, depth `0`.
- Batch/ubatch: `512/128`; MBT/max-num-seqs: `N/A/N/A`.
- Graph: default enabled, disable override 없음; lifetime reuse 4425회. Measured-window graph hit 수와 동일시하지 않는다.
- Configuration SHA256: `e2075376ea251e443dc7e1994f05aaf80478829c89cc79bcdebf26d5c063be9a`.

### 실제 측정 launch command

아래 명령은 당시 snapshot 경로와 experiment 식별자를 포함한 원문이다. 재실행 시 해당 경로가 필요하며 기존 raw experiment를 덮어쓰지 않는다. 이 publication에서는 명령을 실행하지 않았다.

```bash
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5/ceb8cc92b537/results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/runtime/container-0.cid --label experiment=EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001 --rm --pull=never --name exp-v100-wbs5-gemma-llama-r0-perf-20260928-001-backend-0 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/gemma-4-26b-a4b-it-qat-gguf/gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k f16 --cache-type-v f16 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

### Environment

Host process environment와 Docker 내부 환경을 구분한다. Container defaults/실제 환경은 [resolved receipt](../../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/runtime/effective-environment.json)에 보존했다.

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
| TTFT mean | 439.098 s |
| Prefill mean | 359.090 tok/s |
| Mean request decode | 22.539 tok/s |
| Aggregate decode | 7.543 tok/s |
| End-to-end output | 4.785 tok/s |
| Batch wall | 671.540 s |
| Total output tokens | 3213 |
| Peak VRAM GPU0 / GPU1 | 10039 / 10537 MiB |

| Request | Prompt tokens (live tokenizer) | Output tokens | TTFT s | Prefill tok/s | Decode tok/s | Output verdict |
|---|---:|---:|---:|---:|---:|---|
| project-a | 126975 | 1603 | 632.645 | 200.743 | 41.260 | PASS |
| project-b | 126976 | 1610 | 245.551 | 517.436 | 3.818 | PASS |

## Telemetry / integrity

VRAM peak sampled every 0.5s; power/temp/clocks sampled every 2s. TPS definitions unchanged.

| GPU | Power min–max W | Temperature min–max °C | SM clock min–max MHz | Memory clock min–max MHz | Samples |
|---|---:|---:|---:|---:|---:|
| 0 | 26.04–169 | 42–61 | 135–1200 | 877–877 | 336 |
| 1 | 26.52–161.46 | 40–58 | 135–1200 | 877–877 | 336 |

Peak VRAM은 sampled 값이며 순간 peak 전체를 보장하지 않는다. Runtime lifecycle telemetry는 startup/idle 구간을 포함할 수 있다.

Output integrity: **PASS (2/2)**. C2 resident/active=true, queue_only=false; post-health healthy. [Overlap evidence](../../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/overlap-evidence.json) · [Output 원문](../../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/requests.json) · [Post-health](../../results/raw/EXP-V100-WBS5-GEMMA-LLAMA-R0-PERF-20260928-001/health-after.json).

## 제약 및 해석

- R1 NGRAM은 성능 악화, R2 b1024는 intended prefill/TTFT 이득이 없어 제외했다.
- Graph reuse가 관측됐지만 R0의 VRAM upward drift/graph instability는 없어서 Gate B는 NOT_TRIGGERED, R3는 SKIPPED다.
- WBS5 recipe는 TARGET만 사용한다. 별도 MTP companion 및 WBS2/3 MTP 결과를 이 성능 레시피에 합치지 않는다.
- 이 recipe의 유효 measured run은 1회다. 반복 검증의 신뢰구간이나 전체 workload에 대한 우위를 주장하지 않는다.
- Mean request decode와 aggregate decode는 scheduling/overlap 및 서로 다른 output 길이의 영향을 받는다. Aggregate decode를 순수 kernel 속도나 mean × concurrency로 해석하지 않는다.
- Preflight의 artifact/CLI/runner 검증과 measured startup/output/overlap으로 승격했다. Runtime route/graph/cache 중 직접 증명되지 않은 항목은 UNKNOWN으로 유지한다.

## Publication audit

[Frozen source](<../../docs/WBS-5 - Gemma4 26B A4B - llama.cpp.md>)의 candidate ID/delta/invariant와 일치한다. 전체 7개 track / 25개 candidate 및 28개 plan instance 대조 결과와 evidence SHA256은 [publication receipt](../../state/wbs5-final-recipes.json)에 기록했다.
