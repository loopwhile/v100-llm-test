# Final Test Matrix

C1 is tested first. WBS 3 authoritative C2 uses `workloads/concurrency/v2.json` for every runnable lane. Historical v1 C2 runs remain diagnostic evidence only.

## llama.cpp matrix

| Model | Weight | KV | Topology | TARGET | NGRAM | MTP | MTP_NGRAM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen3.8-27B | UD-Q4_K_M | Q8_0 | TP2 shared | C1→C2 | C1→C2 | N/A | N/A |
| Ornith 1.5 35B-A3B | Q4_K_M | Q8_0 | TP2 shared | C1→C2 | C1→C2 | C1→C2 or UNSUPPORTED | C1→C2 or UNSUPPORTED |
| Ornith 1.5 9B | Q6_K | FP16 | TP2 shared | C1→C2 | C1→C2 | C1→C2 | C1→C2 |
| Ornith 1.5 9B | Q6_K | FP16 | 1GPU×2 + LiteLLM | verify→C1→C2 | verify→C1→C2 | verify→C1→C2 | verify→C1→C2 |
| Gemma4 26B-A4B | UD-Q4_K_XL | FP16 | TP2 shared | C1→C2 | C1→C2 | C1→C2 or UNSUPPORTED | C1→C2 or UNSUPPORTED |

Mandatory ngram pairing:
- TARGET versus NGRAM
- MTP versus MTP_NGRAM

TARGET versus NGRAM remains required for every llama.cpp model. Qwen3.8-27B intentionally has no MTP/MTP_NGRAM benchmark lane; the MTP pair applies to Ornith/Gemma candidates that declare it.

C1/C2 NGRAM rows are compatibility/capacity checks, not acceleration benchmarks. A row can PASS with zero/unavailable draft counters or without a TARGET-relative speedup if NGRAM is configured, the requested capacity succeeds, output is valid, and the server remains healthy. Actual NGRAM speedup is judged in Phase 5 using `workloads/performance/v1.json`.

## 1Cat-vLLM / v100-skinny matrix

| Model | Backend | Weight | KV | Spec | Topology | Required result |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3.8-27B | STOCK 1Cat 1.5.0 B200-aligned revalidation lane | QUASAR NVFP4 | FP8 E4M3 | Target-only | TP2 shared | WBS3 v2 C2 revalidation authorized; v1 queue-only/output-fail retained historically |
| Qwen3.8-27B | STOCK 1Cat 1.5.0 recovery recipe | QUASAR NVFP4 | FP8 E5M2 | Target-only | TP2 shared | one-shot 128K recovery validation using LM-only/util0.92/partition256 + historical E5M2/GDN path |
| Qwen3.8-27B | SKINNY v1.1 / 1Cat 1.2.2 | RadixArk mixed NVFP4/FP8 | FP16 contract | MTP k=3 contract | TP2 experimental | PRECHECK `FAIL_OOM_MODEL_LOAD`; boot gate NOT_REACHED; no C1/C2 scheduling |
| Ornith 1.5 35B-A3B | STOCK | NVFP4 | FP8 E5M2 | Target-only | TP2 shared | C1 PASS; WBS3 v2 C2 TODO |
| Ornith 1.5 35B-A3B | SKINNY | no pinned v1.1 contract | — | — | TP2 | support resolution / UNSUPPORTED |
| Ornith 1.5 9B | STOCK | NVFP4 | FP16 | MTP1 | TP2 shared | C1 PASS; v1 active evidence historical; WBS3 v2 C2 TODO |
| Ornith 1.5 9B | STOCK | NVFP4 artifact verified | FP16 candidate | MTP candidate | 1GPU×2 + LiteLLM | runtime compatibility pending → two TP1 servers + LiteLLM or UNSUPPORTED |
| Ornith 1.5 9B | SKINNY | no pinned v1.1 contract | — | — | TP2 | support resolution / UNSUPPORTED |
| Gemma4 26B-A4B | STOCK | AWQ INT4 compressed-tensors | FP16 | Target-only | TP2 shared | C1 FAIL_TIMEOUT; C2 not eligible |
| Gemma4 26B-A4B | SKINNY | no pinned v1.1 contract | — | — | TP2 | support resolution / UNSUPPORTED |

## Primary capacity target

Every primary request:
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
- authoritative workload: `workloads/concurrency/v2.json`.
- max_model_len: 131072; max_num_seqs: 2; TP: 2.
- Ornith 9B and 35B use their C1-validated exact serving contracts.
- Qwen3.8 receives a user-authorized v2 revalidation with the B200-aligned E4M3 recipe; this does not retroactively change the older C1 semantic verdict.
- Gemma4 remains excluded because C1 128K ended FAIL_TIMEOUT.

SKINNY is excluded from C2 on the current P520 because WBS 1.4 failed during model-load QPN prepack before server boot.

## Sustained C2 performance workload

`workloads/performance/v1.json` keeps the same 128K total sequence ceiling per request, reserves 4096 output tokens, requires at least 1024 actual completion tokens, and diversifies repeated identifiers per section. Use it for throughput comparisons, especially TARGET/NGRAM and MTP/MTP_NGRAM; do not use the repeated capacity filler alone to claim an NGRAM speedup.

## Fail-fast / diagnostics
- Preserve a clear 128K OOM/capacity failure.
- Optional 96K/64K runs are diagnostic only and use new experiment IDs.
- Do not perform broad context sweeps.
- Do not run C2 performance for a lane without a valid C1 configuration.
- Do not silently replace unsupported models with another quant or artifact.

## Final comparison eligibility

Shared-server candidates need:
- C1 128K verdict
- C2 verdict
- correct runtime/artifact identity
- valid output
- latency/throughput/VRAM evidence

Ornith 9B 1GPU×2 additionally needs:
- each one-GPU server independently fits 128K
- both servers and the pinned LiteLLM gateway run simultaneously
- C1 and C2 measured requests use one LiteLLM client endpoint, never direct backend selection
- C2 evidence proves distribution across both backends via backend processing samples and/or distinct LiteLLM deployment headers
- all three services remain healthy
- aggregate and per-agent end-to-end performance recorded with LiteLLM overhead included
