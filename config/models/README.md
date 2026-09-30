# Model configuration records

The JSON files in this directory are **benchmark planning inputs**, not a live status dashboard.

Some model files are hash-locked by `config/wbs5-input-lock.json` and their exact SHA256 values are referenced by the WBS5 final publication audit. Historical raw plans and receipts also embed copies of these records.

Therefore:
- do not rewrite a frozen model JSON merely because a later measured run changed the operational verdict;
- historical values such as `static_runtime_contract_ready_host_startup_pending` describe the planning state captured by the frozen input;
- changing a hash-locked input after publication would invalidate the frozen-input comparison unless the benchmark is deliberately reopened under a new contract.

Current measured outcomes are tracked separately:
- `state/current.md` — human-readable execution state
- `state/current-model-status.json` — machine-readable current outcome overlay
- `docs/test-matrix.md` — current matrix summary
- `docs/WBS-5.5-final-recipes.md` — final WBS5 recipe publication

Raw experiment `config.json`, `plan.json`, and receipt files remain immutable evidence and may legitimately contain older planning-state strings.
