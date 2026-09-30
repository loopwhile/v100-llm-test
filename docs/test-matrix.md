# Current Test Matrix and Outcomes

This file is the **current outcome summary** for the completed acceptance/topology matrix. Historical plans and execution chronology remain in `docs/WBS.md`; raw evidence remains immutable.

WBS 3 authoritative C2 uses `workloads/concurrency/v2.json` with `workloads/concurrency/v2-ground-truth.json`. Historical v1 C2 runs are diagnostic evidence only.

## llama.cpp matrix

| Model | Weight | KV | Topology | TARGET | NGRAM | MTP | MTP_NGRAM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3.8-27B | UD-Q4_K_M | Q8_0 | TP2 shared | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | N/A | N/A |
| Ornith 1.5 35B-A3B | Q4_K_M | Q8_0 | TP2 shared | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` |
| Ornith 1.5 9B | Q6_K | FP16 | TP2 shared | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` |
| Ornith 1.5 9B | Q6_K | FP16 | 1GPU×2 + LiteLLM | C1 `PASS_C1_128K`, C2 `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` |
| Gemma4 26B-A4B | UD-Q4_K_XL | FP16 | TP2 shared | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` | `PASS_C2_ACTIVE` |

TARGET versus NGRAM remains the mandatory ngram pairing. MTP versus MTP_NGRAM is preserved for models that declare the pair. Qwen3.8 intentionally has no llama.cpp MTP/MTP_NGRAM lane in the frozen matrix.

C1/C2 NGRAM rows are compatibility/capacity checks, not acceleration claims. Performance effectiveness is evaluated with `workloads/performance/v1.json`.

## 1Cat-vLLM / v100-skinny matrix

| Model | Backend | Weight | KV | Spec | Topology | Current result |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3.8-27B | STOCK 1Cat 1.5.0 | QUASAR NVFP4 | FP8 E4M3 | Target-only | TP2 shared | WBS3 v2: `QUEUE_ONLY / FAIL_OUTPUT`; WBS5: no eligible recipe |
| Qwen3.8-27B | STOCK recovery / WBS5 E5M2 branch | QUASAR NVFP4 | FP8 E5M2 | Target-only | TP2 shared | dedicated 128K recovery closed `FAIL_STARTUP / FAIL_CAPACITY`; WBS5 R3 remained `QUEUE_ONLY`; no eligible recipe |
| Qwen3.8-27B | SKINNY v1.1 / 1Cat 1.2.2 | RadixArk mixed NVFP4/FP8 | FP16 contract | MTP k=3 contract | TP2 experimental | `FAIL_OOM_MODEL_LOAD`; boot gate `NOT_REACHED`; no C1/C2 scheduling |
| Ornith 1.5 35B-A3B | STOCK 1Cat 1.5.0 | NVFP4 | FP8 E5M2 | Target-only | TP2 shared | WBS3 v2 `PASS_C2_ACTIVE`; WBS5 R1 current `VALIDATED_RECIPE` |
| Ornith 1.5 35B-A3B | SKINNY | no pinned v1.1 contract | — | — | TP2 | `UNSUPPORTED` |
| Ornith 1.5 9B | STOCK 1Cat 1.5.0 | NVFP4 | FP16 | MTP1 | TP2 shared | WBS3 v2 `PASS_C2_ACTIVE`; WBS5 G0 semantic admission FAIL; no eligible recipe |
| Ornith 1.5 9B | STOCK 1Cat 1.5.0 | NVFP4 | FP16 | MTP1 | 1GPU×2 + LiteLLM | WBS4.2.1 `FAIL_STARTUP`: one 16GB V100 cannot fit 128K FP16 KV; estimated max sequence ~71.2K |
| Ornith 1.5 9B | SKINNY | no pinned v1.1 contract | — | — | TP2 | `UNSUPPORTED` |
| Gemma4 26B-A4B | STOCK 1Cat 1.5.0 | AWQ INT4 compressed-tensors | FP16 | Target-only | TP2 shared | C1 `FAIL_TIMEOUT`; C2/WBS5 not eligible |
| Gemma4 26B-A4B | SKINNY | no pinned v1.1 contract | — | — | TP2 | `UNSUPPORTED` |

## Primary capacity target

Every primary capacity/C2 request:
- total context budget per agent: 131072
- reserved output: 2048
- minimum actual output: 256
- prompt calibrated by live tokenizer
- minimum total utilization: 99%

Shared llama.cpp C2:
- logical aggregate KV target: 262144
- per-slot ceiling: 131072
- parallel: 2

Shared STOCK C2:
- authoritative workload: `workloads/concurrency/v2.json`
- `max_model_len=131072`, `max_num_seqs=2`, TP=2
- Ornith 9B/35B use their C1-validated exact serving contracts
- Qwen3.8 WBS3 v2 completed as queue-only/output-fail
- Gemma4 is excluded because C1 128K ended `FAIL_TIMEOUT`

SKINNY is excluded from C2 on the current P520 because WBS 1.4 failed during model-load QPN prepack before server boot.

## Sustained C2 performance workload

`workloads/performance/v1.json` keeps the 128K total sequence ceiling per request, reserves 4096 output tokens, requires at least 1024 actual completion tokens, and diversifies repeated identifiers per section.

WBS5 final publication produced six validated recipes across five tracks. See `docs/WBS-5.5-final-recipes.md`.

## Fail-fast / diagnostics

- Preserve a clear 128K OOM/capacity failure.
- Optional 96K/64K runs are diagnostic only and use new experiment IDs.
- Do not perform broad context sweeps.
- Do not run C2 performance for a lane without a valid acceptance path.
- Do not silently replace unsupported models with another quant or artifact.
- Historical raw/config/plan files are immutable and may preserve pre-measurement status strings.

## 1GPU×2 acceptance requirements

For a runnable independent topology:
- each one-GPU server must independently fit 128K
- both servers and the pinned LiteLLM gateway must run simultaneously
- C1/C2 measured requests use one LiteLLM client endpoint
- C2 evidence proves distribution across both backends
- all services remain healthy
- aggregate and per-agent end-to-end performance include LiteLLM overhead

llama.cpp satisfies these requirements. The pinned STOCK 1Cat profile fails before the 128K routing/measurement stage because each TP1 backend cannot allocate the required KV cache.
