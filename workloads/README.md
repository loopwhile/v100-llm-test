# Workloads

The repository stores **small deterministic workload manifests**, not megabyte-scale materialized prompts.

`scripts/build_128k_workload.py` expands a manifest against the exact running runtime/tokenizer and writes a generated harness-ready JSON file under `workloads/generated/`.

This preserves the useful pattern from `qwen3.8-bench`—deterministic synthetic long-context material—without committing 100K–1MB prompt blobs.

## Primary manifests

- `capacity/v1.json`: Project A only, C1, 128K context budget.
- `concurrency/v1.json`: Project A + Project B, C2, each independently calibrated to the 128K context budget.

Both reserve 512 output tokens and target at least 99% total context utilization. The generated prompts use different project headers, source blocks and padding markers, so C2 acceptance does not rely on a large shared prefix.

Generated workload bytes and the tokenizer receipt are evidence and must be preserved with the experiment that consumes them.
