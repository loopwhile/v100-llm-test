#!/usr/bin/env python3
"""Offline 8C: write all frozen plans, without subprocesses, HTTP or raw writes."""
import argparse
from collections import Counter
from pathlib import Path

import bench_harness as h
import run_wbs5 as runner
import wbs5_contract as c


def generate(output, date):
    output.mkdir(parents=True, exist_ok=False)
    plans = []
    for track, (_, _, ids) in c.TRACKS.items():
        for i in range(len(ids)):
            candidate = f"R{i}"
            labels = ["repetition-1", "repetition-2"] if track == "qwen-llama" and i == 0 else ["screening-1"]
            if track == "qwen-llama" and i > 0:
                labels.append("confirm-1")
            for sequence, label in enumerate(labels, 1):
                plan = c.build_plan(track, candidate, c.experiment_id(track, candidate, date, sequence), label)
                dry = runner.dispatch(plan, output_root=output)
                plans.append({key: dry[key] for key in ("track", "candidate_key", "candidate_id", "experiment_id",
                                                       "run_identity", "status", "configuration_sha256")})
                plans[-1]["plan_path"] = dry["experiment_id"] + "/candidate-plan.json"
    summary = {"phase": "WBS5-8C", "frozen_tracks": 7, "frozen_candidates": 25, "dry_plans": len(plans),
               "measured_inference_executed": False, "raw_directories_created": False,
               "candidate_status_counts": dict(Counter(row["status"] for row in plans
                   if row["run_identity"]["label"] not in ("repetition-2", "confirm-1"))),
               "workload_path": c.WORKLOAD, "workload_sha256": c.WORKLOAD_SHA,
               "input_lock_sha256": c.INPUT_LOCK_SHA, "plans": plans}
    h.save(output / "manifest.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    summary = generate(args.output, args.date)
    print(f"8C PASS: {summary['frozen_tracks']} tracks, {summary['frozen_candidates']} candidates, {summary['dry_plans']} dry plans; inference NO")


if __name__ == "__main__":
    main()
