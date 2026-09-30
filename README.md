# v100-llm-test

Serving acceptance and performance-recipe tests for a Lenovo P520 with 2× Tesla V100 16GB.

## Goal

Validate reproducible serving configurations for independent single-agent coding projects, preserving exact model/runtime/topology evidence and publishing bounded recipes rather than selecting one automatic winner.

Operating target:
- per-agent context ceiling: 128K
- normal concurrency: C1
- required peak concurrency: C2
- C3+ out of scope
- C2 requests are independent projects, not cooperating agents

A server merely configured for 128K is not a 128K PASS. Two accepted HTTP requests are not automatically an active C2 PASS.

## Candidate models
- Qwen3.8-27B
- Ornith 1.5 35B-A3B
- Ornith 1.5 9B
- Gemma4 26B-A4B

## Required runtime lanes

llama.cpp global lane catalog:
- TARGET
- NGRAM
- MTP
- MTP_NGRAM

TARGET versus NGRAM is mandatory for every llama.cpp candidate. MTP versus MTP_NGRAM applies only to model artifacts that explicitly declare the MTP pair. Qwen3.8-27B intentionally uses TARGET + NGRAM only; Ornith/Gemma candidates retain the MTP pair.

vLLM family:
- 1Cat-vLLM STOCK
- v100-skinny SKINNY, mandatory explicit result row

v100-skinny is a separate pinned runtime identity, not a flag on the STOCK 1Cat environment. On the current 2×V100-16GB P520, WBS 1.4 ends at `FAIL_OOM_MODEL_LOAD` during QPN prepack before server boot, so SKINNY is retained as evidence but not scheduled for C1/C2. Non-Qwen SKINNY rows remain `UNSUPPORTED` because the pinned v1.1 standalone contract is Qwen-specific.

## Topologies

- `tp2-shared`: one model/server across both V100s.
- `1gpu-x2-independent`: two one-GPU Ornith 1.5 9B servers behind one mandatory LiteLLM gateway.

The independent topology is **validated for llama.cpp**: WBS 4 completed C1 and C2 128K, and TARGET/NGRAM/MTP/MTP_NGRAM all reached `PASS_C2_ACTIVE`. The corresponding STOCK 1Cat-vLLM TP1×2 profile is **closed as `FAIL_STARTUP`**: one V100 16GB cannot fit the pinned 128K FP16 KV requirement (4.68 GiB required versus 2.61 GiB available; estimated maximum sequence length ~71.2K).

For every runnable `1gpu-x2-independent` acceptance test, requests enter through the same LiteLLM endpoint. Direct client-to-backend routing is diagnostic only. LiteLLM is pinned to v1.101.0 and uses two deployments with `least-busy` routing and `max_parallel_requests=1` per backend.

Shared llama.cpp C2 explicitly requests a 256K logical aggregate KV pool with a 128K ceiling per slot.

## Workloads

Compact deterministic manifests:
- `workloads/capacity/v1.json` — C1 capacity
- `workloads/concurrency/v2.json` — authoritative WBS 3 C2 workload
- `workloads/concurrency/v2-ground-truth.json` — pre-registered semantic oracle
- `workloads/concurrency/v1.json` — historical C2 evidence only
- `workloads/performance/v1.json` — sustained C2 performance/replay workload

`scripts/build_128k_workload.py` materializes manifests with the exact live tokenizer so prompt plus reserved output stays within 131072 tokens while filling at least 99% of the budget.

Authoritative C2 uses unrelated Project A/B material with distinct hashes. Capacity/C2 reserves 2048 output tokens and requires at least 256 actual completion tokens. The performance workload reserves 4096 and requires at least 1024. Runtime concurrency evidence is preserved independently from mechanical and semantic output verdicts.

See [workload contract](docs/workload-contract.md) and [workload README](workloads/README.md).

## Current validated results

WBS 3 authoritative C2 and WBS 4 topology validation are complete. Key STOCK 1Cat outcomes:
- Qwen3.8 TP2: WBS3 v2 `QUEUE_ONLY / FAIL_OUTPUT`; no WBS5 eligible recipe.
- Ornith 1.5 9B TP2: WBS3 v2 `PASS_C2_ACTIVE`; WBS5 G0 semantic admission failed and the track closed with no eligible recipe.
- Ornith 1.5 35B-A3B TP2: WBS3 v2 `PASS_C2_ACTIVE`; WBS5 R1 is a current validated recipe.
- Ornith 1.5 9B TP1×2 + LiteLLM: `FAIL_STARTUP` at 128K on one 16GB V100.
- Gemma4 26B-A4B TP2: C1 ended `FAIL_TIMEOUT`; C2/WBS5 not eligible.

WBS 5 final publication contains **6 validated recipes across 5 tracks**:
- Qwen llama.cpp R2 — TARGET, UB256
- Ornith 9B llama.cpp R1 — 1GPU×2 + LiteLLM, TARGET UB256
- Ornith 35B llama.cpp R1 — native MTP1
- Ornith 35B llama.cpp R2 — TARGET UB256
- Gemma4 llama.cpp R0 — TARGET baseline
- Ornith 35B 1Cat R1 — E5M2, graph-auto serving configuration, MBT4096

Qwen 1Cat and Ornith 9B 1Cat have **NO ELIGIBLE RECIPE**. See [WBS 5 final publication](docs/WBS-5.5-final-recipes.md), [all recipe ledger](docs/WBS-5-all-recipes.md), and [machine-readable final recipes](state/wbs5-final-recipes.json).

WBS 7 post-WBS5 validation is also complete. Native MTP1 ended terminal GPU OOM; the bounded GQA×2 experiment passed C2 but was not promoted to a new recipe. See [WBS 7 result review](docs/WBS-7.3-result-review.md).

## Frozen inputs versus current state

Files under `config/models/` are benchmark planning inputs and some are hash-locked by `config/wbs5-input-lock.json`. Their historical `status` strings must not be rewritten after measurement because doing so would invalidate the frozen-input audit. Current outcomes are recorded separately in:
- [current execution state](state/current.md)
- [current machine-readable model status](state/current-model-status.json)
- [model config notes](config/models/README.md)

Historical raw/config/plan files remain immutable evidence even when they contain pre-measurement status text.

## Evidence

Fresh runs write raw evidence under `results/raw/<EXPERIMENT_ID>/`, one Markdown report under `reports/`, and normalized rows in:
- `results/summary.csv`
- `reports/comparison.csv`

Historical results are not imported as acceptance evidence. C2 evidence is sampled from runtime metrics/slots during the measured window, and sampled peak VRAM is merged into experiment metrics. For Ornith 9B llama.cpp 1GPU×2, evidence additionally records LiteLLM deployment headers and backend activity to prove distribution across GPU0/GPU1.

Validation is bounded to the recorded hardware, exact artifacts and declared workload. Mechanical output PASS does not add semantic coding-quality certification.

Offline repository validation:

    python3 scripts/validate_repo.py
    python3 -m unittest discover -s tests -v

The project publishes validated/bounded recipes per model/runtime/topology. It does not choose or deploy one final production configuration; recipe selection is left to the user.
