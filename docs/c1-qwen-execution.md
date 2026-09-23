# WBS 2.1.1 execution and recovery

`scripts/run_c1_qwen.py` executes exactly one Qwen3.8-27B C1 128K lane (`TARGET` or `NGRAM`) on `p520-llm`. It uses the existing runtime plan, capacity manifest, live tokenizer, and benchmark harness. It does not retry, queue another lane, or change hardware policy.

The runner verifies the model SHA256, checks for existing GPU compute processes and an occupied port, and takes an exclusive project lock. Use one remote project directory for both lanes. Each experiment ID creates a new raw directory; reusing an ID fails even if the preceding attempt failed before inference.

Launch from the remote checkout with `nohup`, redirecting stdin/stdout/stderr. Read `results/raw/<ID>/runtime/progress.json` before any subsequent action. It records the host boot ID, runner PID/start ticks, container ID, source/config hashes, phase, and verdict. The readiness deadline is 300 seconds; the workload/measurement subprocess deadline is 2400 seconds, with a 1800-second HTTP timeout.

The raw directory preserves GPU telemetry, runtime logs, tokenizer receipts, request results, final health, and completion evidence. Cleanup addresses only the container from this experiment's cidfile after checking its experiment label. `runtime/exit.json` is written after cleanup. Inspect `runtime/cleanup.json` and the current GPU/process state before launching the next lane.

After a disconnect, inspect the existing process identity and artifacts. Do not run the command again to check whether it completed. The runner survives SSH loss, but does not automatically resume an interrupted inference; a killed worker may leave only prepared request records and runtime progress, without a partial generated response. Preserve such evidence and classify it accordingly.

Copy completed raw directories locally without overwriting different evidence, inspect config identity and output correctness, then publish with `scripts/report_experiment.py`. The automated harness's nonempty check alone does not establish semantic correctness or absence of truncation: WBS acceptance also requires review of the response, finish reason, server logs, and post-request health. Record that review alongside the raw evidence and in the report.
