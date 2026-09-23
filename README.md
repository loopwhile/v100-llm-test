# v100-llm-test

Final serving acceptance tests for a Lenovo P520 with 2× Tesla V100 16GB.

## Goal

Determine which model/runtime/topology can reliably serve independent single-agent coding projects with:
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

llama.cpp:
- TARGET
- NGRAM
- MTP
- MTP_NGRAM

TARGET versus NGRAM is mandatory. MTP versus MTP_NGRAM remains an explicit support/result pair; unsupported combinations are recorded as UNSUPPORTED.

vLLM family:
- 1Cat-vLLM STOCK
- v100-skinny SKINNY, mandatory

v100-skinny is a separate pinned runtime identity, not a flag on the STOCK 1Cat environment.

## Topologies
- tp2-shared: one model/server across both V100s
- 1gpu-x2-independent: two one-GPU servers; currently a first-class Ornith 1.5 9B candidate

Shared llama.cpp C2 explicitly requests a 256K logical aggregate KV pool with a 128K ceiling per slot.

## Workloads
Compact deterministic manifests:
- workloads/capacity/v1.json
- workloads/concurrency/v1.json

scripts/build_128k_workload.py materializes them with the exact live tokenizer so prompt plus reserved output stays within 131072 tokens while filling at least 99% of the budget.

C2 uses unrelated Project A and Project B material with distinct hashes.

## Evidence
Fresh runs write raw evidence under results/raw/<EXPERIMENT_ID>/, one Markdown report under reports/, and normalized rows in:
- results/summary.csv
- reports/comparison.csv

Historical results are not imported as acceptance evidence.

## Project status
Repository implementation is complete through the runtime-lane/test-plan stage. Remaining work is measured execution according to:
- docs/WBS.md
- docs/test-matrix.md
- docs/runtime-lanes.md
- docs/workload-contract.md

Before execution:

    python3 scripts/validate_repo.py
    python3 -m unittest discover -s tests -v

Exact runtime/model compatibility and local artifact identities still require fresh verification on p520-llm before measured GPU runs.
