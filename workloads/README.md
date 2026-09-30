# Workloads

The repository stores **small deterministic workload manifests**, not megabyte-scale materialized prompts.

`scripts/build_128k_workload.py` expands a manifest against the exact running runtime/tokenizer and writes generated harness-ready JSON under `workloads/generated/`.

This preserves deterministic synthetic long-context material without committing 100K–1MB prompt blobs.

## Primary manifests

- `capacity/v1.json`: Project A only, C1, 128K context budget.
- `concurrency/v2.json`: Project A + Project B, authoritative WBS 3 C2 workload.
- `concurrency/v2-ground-truth.json`: pre-registered semantic oracle for the authoritative v2 C2 workload.
- `concurrency/v1.json`: historical C2 workload retained only for old evidence; it is not authoritative acceptance input.
- `performance/v1.json`: sustained C2 performance workload used for recipe comparisons after acceptance.

## Token budgets

Capacity and authoritative C2:
- total sequence ceiling per request: 131072 tokens
- reserved output: 2048 tokens
- minimum actual completion: 256 tokens
- target utilization: at least 99% of the total context budget

Sustained performance:
- total sequence ceiling per request: 131072 tokens
- reserved output: 4096 tokens
- minimum actual completion: 1024 tokens
- diversified identifiers/sections to avoid treating repeated capacity filler as a speculative-decoding speed benchmark

The v2 C2 workload uses distinct Project A/B material and hashes, one pre-registered seeded defect per project anchor, and semantically-neutral section-variant padding. Runtime concurrency, mechanical output integrity, and oracle-grounded semantic correctness are recorded as separate dimensions.

Generated workload bytes, tokenizer receipts, source-manifest hashes, and materialized prompt hashes are evidence and must be preserved with the experiment that consumes them.

See `docs/workload-contract.md` for the authoritative measurement contract.
