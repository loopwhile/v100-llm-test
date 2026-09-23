# v100-llm-test

Final serving acceptance tests for a Lenovo P520 with **2× Tesla V100 16GB**.

## Goal

Determine which model/runtime/topology can reliably serve independent single-agent coding projects with:

- per-agent context ceiling: **128K**
- normal concurrency: **C1**
- required peak concurrency: **C2**
- C3+ concurrency: out of scope
- C2 requests: independent project contexts, not shared-agent branches

The project measures capacity first, then useful performance. A server starting with a 128K setting is not a 128K PASS, and accepting two HTTP requests is not a C2 concurrency PASS.

## Candidate model scope

- Qwen3.8-27B
- Ornith 1.5 35B-A3B
- Ornith 1.5 9B
- Gemma4 26B-A4B

## Runtime lanes

- llama.cpp on the V100/SM70 lane
- 1Cat-vLLM stock V100 lane
- **1Cat-vLLM + v100-skinny — mandatory test lane**

For llama.cpp, **ngram is a mandatory test axis**. A candidate may not silently skip it. If the pinned model/build cannot execute the declared ngram mode, preserve that fact as `UNSUPPORTED`.

## Evidence

Fresh runs write bounded raw evidence under `results/raw/<EXPERIMENT_ID>/`, one Markdown report under `reports/`, and normalized rows in `results/summary.csv` and `reports/comparison.csv`.

Historical benchmark results are not imported into this repository as acceptance evidence.

## Bootstrap status

Turn 1 imports and adapts the reusable repository foundation from `loopwhile/qwen3.8-bench`: host inventory, GPU telemetry, report/result contracts, and core methodology/runtime/workload documents. The benchmark harness, workloads, runtime launchers, and new WBS are added in later turns.
