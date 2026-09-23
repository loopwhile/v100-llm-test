#!/usr/bin/env python3
"""Execution policy for v100-llm-test. Offline validation only."""
from __future__ import annotations

import argparse
import json

POLICY = "v100-c1-c2-single-execution-v1"
RETRY_REASONS = {
    "harness_bug",
    "instrumentation_bug",
    "infrastructure_failure",
    "configuration_fix",
    "user_authorized",
}


def _int(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _documented(config, name):
    value = config.get(name)
    return isinstance(value, str) and bool(value.strip())


def future_config(config):
    """Apply fresh-project defaults and validate declared exceptions."""
    result = dict(config)
    repetitions = _int(
        config.get("measured_repetitions", config.get("repetition_count", 1)),
        "measured_repetitions",
        minimum=1,
    )
    if "repetition_count" in config and config["repetition_count"] != repetitions:
        raise ValueError("repetition_count conflicts with measured_repetitions")
    if repetitions > 1 and not _documented(config, "repetition_user_request"):
        raise ValueError("repetitions > 1 require a documented explicit user request")

    warmups = _int(config.get("warmup_count", 0), "warmup_count", minimum=0)
    if warmups and not all(
        _documented(config, key)
        for key in ("full_size_warmup_reason", "full_size_warmup_user_approval")
    ):
        raise ValueError(
            "full-size warmup requires a technical reason and prior user approval"
        )

    if "retry_of" in config:
        if not _documented(config, "retry_of") or not _documented(config, "experiment_id"):
            raise ValueError("retry requires predecessor and new experiment IDs")
        if config["retry_of"] == config["experiment_id"]:
            raise ValueError("retry requires a new experiment ID")
        if config.get("retry_reason") not in RETRY_REASONS or not _documented(
            config, "retry_evidence"
        ):
            raise ValueError("retry requires an allowed reason and supporting evidence")
        if config["retry_reason"] == "user_authorized" and not _documented(
            config, "retry_user_approval"
        ):
            raise ValueError("user-authorized retry requires explicit user approval")

    result.update(
        measurement_policy=POLICY,
        measured_repetitions=repetitions,
        repetition_count=repetitions,
        warmup_count=warmups,
    )
    return result


def execution_plan(concurrency, *, turns=1, **overrides):
    """Describe execution units; this function never performs inference."""
    if type(concurrency) is not int or concurrency not in (1, 2):
        raise ValueError("planned concurrency must be C1 or C2")
    _int(turns, "turns", minimum=1)
    config = future_config(overrides)
    return config | {
        "concurrency": concurrency,
        "intended_requests_per_batch": concurrency,
        "turns_per_execution": turns,
        "measured_batches": config["measured_repetitions"] * turns,
        "total_intended_requests": config["measured_repetitions"] * turns * concurrency,
        "release": "synchronized barrier per batch",
        "plan_only": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, choices=(1, 2), default=1)
    parser.add_argument("--turns", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(execution_plan(args.concurrency, turns=args.turns), indent=2))


if __name__ == "__main__":
    main()
