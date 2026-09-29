#!/usr/bin/env python3
"""Run exactly one WBS5 measured experiment on P520 and retrieve its raw result.

This is the ThinkPad-side orchestration entry point for measured WBS5 child items.
It does only three things:
1. sync the committed HEAD source to an isolated P520 snapshot,
2. execute exactly one remote measured runner,
3. copy exactly that experiment's raw directory back to the ThinkPad.

It does not publish reports, edit WBS/state, commit, push, retry, tune, or advance
to another WBS item.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

from wbs5_contract import PYTHON as ONECAT_PYTHON

ROOT = Path(__file__).resolve().parents[1]
SSH_HOST = "p520"
REMOTE_BASE = "/home/loopwhile/v100-llm-test-wbs5"


def run(cmd, *, cwd=ROOT, check=True, stdin=None):
    return subprocess.run(cmd, cwd=cwd, check=check, stdin=stdin)


def capture(cmd, *, cwd=ROOT):
    return subprocess.run(
        cmd, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def ssh(command: str, *, check=True):
    return run(["ssh", SSH_HOST, command], check=check)


def tracked_tree_guard():
    branch = capture(["git", "branch", "--show-current"])
    if branch != "main":
        raise RuntimeError(f"requires main branch, got {branch!r}")
    if subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode != 0:
        raise RuntimeError("tracked working tree has unstaged changes")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0:
        raise RuntimeError("index has staged changes")
    return capture(["git", "rev-parse", "HEAD"])


def sync_committed_head(remote_root: str):
    # git archive transfers only committed tracked bytes. No .git, no untracked
    # results, no --delete, and no stale source from another commit.
    archive = subprocess.Popen(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
    )
    assert archive.stdout is not None
    remote_cmd = (
        'test "$(hostname)" = "p520-llm" && '
        f"mkdir -p {shlex.quote(remote_root)} && "
        f"tar -xf - -C {shlex.quote(remote_root)}"
    )
    remote = subprocess.run(
        ["ssh", SSH_HOST, remote_cmd],
        cwd=ROOT,
        stdin=archive.stdout,
    )
    archive.stdout.close()
    archive_rc = archive.wait()
    if archive_rc != 0:
        raise RuntimeError(f"git archive failed: rc={archive_rc}")
    if remote.returncode != 0:
        raise RuntimeError(f"P520 source sync failed: rc={remote.returncode}")


def copy_gate_receipt(local_path: Path, remote_root: str, experiment_id: str) -> str:
    local_path = local_path.resolve()
    if not local_path.is_file():
        raise FileNotFoundError(local_path)
    receipt = json.loads(local_path.read_text())
    gate_id = receipt.get("experiment_id", "")
    if not re.fullmatch(r"EXP-[A-Za-z0-9-]+", gate_id):
        raise ValueError("gate experiment ID invalid")
    local_raw = ROOT / "results/raw" / gate_id
    remote_raw = f"{remote_root}/results/raw/{gate_id}"
    for row in receipt.get("evidence", []):
        source = Path(row["path"])
        source = (source if source.is_absolute() else ROOT / source).resolve()
        try:
            relative = source.relative_to(local_raw.resolve())
        except ValueError as exc:
            raise ValueError("gate evidence outside raw directory") from exc
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("gate evidence hash mismatch")
        destination = f"{remote_raw}/{relative.as_posix()}"
        ssh(f"mkdir -p {shlex.quote(str(Path(destination).parent))}")
        run(["rsync", "-a", "--ignore-existing", str(source), f"{SSH_HOST}:{destination}"])
    remote_dir = f"{remote_root}/.wbs5-gates"
    remote_path = f"{remote_dir}/{experiment_id}-{local_path.name}"
    ssh(f"mkdir -p {shlex.quote(remote_dir)}")
    run(["rsync", "-a", str(local_path), f"{SSH_HOST}:{remote_path}"])
    return remote_path


def remote_raw_exists(remote_raw: str) -> bool:
    return ssh(f"test -e {shlex.quote(remote_raw)}", check=False).returncode == 0


def retrieve_raw(remote_raw: str, local_raw: Path):
    if local_raw.exists():
        raise FileExistsError(
            f"local raw already exists; refusing overwrite: {local_raw}"
        )
    local_raw.parent.mkdir(parents=True, exist_ok=True)
    run(["rsync", "-a", f"{SSH_HOST}:{remote_raw}/", f"{local_raw}/"])


def summarize(local_raw: Path, *, benchmark_rc, recovered_existing: bool):
    completion_path = local_raw / "completion.json"
    metrics_path = local_raw / "metrics.json"
    completion = json.loads(completion_path.read_text()) if completion_path.exists() else {}
    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    summary = {
        "experiment_id": local_raw.name,
        "raw_retrieved": True,
        "recovered_existing_remote_raw": recovered_existing,
        "benchmark_process_exit_code": benchmark_rc,
        "verdict": completion.get("verdict") or metrics.get("verdict") or "UNKNOWN",
        "error": completion.get("error") or metrics.get("error"),
        "local_raw": str(local_raw.relative_to(ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def ornith9_g0_argv(experiment_id: str) -> list[str]:
    # SSH does not forward the caller's environment. Pin the same interpreter
    # used by measured WBS5 1Cat candidates in the remote G0 process itself.
    return [
        "env",
        f"V100_1CAT_PYTHON={ONECAT_PYTHON}",
        "python3",
        "scripts/run_c2_onecat.py",
        "--experiment-id",
        experiment_id,
        "--model",
        "ornith-1.5-9b",
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track")
    parser.add_argument("--candidate")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-label")
    parser.add_argument("--gate-receipt", type=Path)
    parser.add_argument("--performance-diagnostic", action="store_true")
    parser.add_argument("--retry-evidence", type=Path)
    parser.add_argument("--execute-measured", action="store_true")
    parser.add_argument(
        "--ornith9-g0",
        action="store_true",
        help="Run the separate Ornith9 1Cat G0 C2 semantic prerequisite.",
    )
    args = parser.parse_args()

    if not args.ornith9_g0:
        if not all((args.track, args.candidate, args.run_label, args.execute_measured)):
            parser.error(
                "normal WBS5 run requires --track, --candidate, --run-label, "
                "and --execute-measured"
            )
    if args.performance_diagnostic and (args.ornith9_g0 or args.track != "ornith9-onecat"
                                        or args.candidate != "R0" or args.gate_receipt is None):
        parser.error("--performance-diagnostic requires Ornith9 1Cat R0 and --gate-receipt")
    if args.run_label == "retry-1":
        predecessor = args.experiment_id[:-3] + "001"
        expected = ROOT / "results/raw" / predecessor / "completion.json"
        if args.retry_evidence != expected.relative_to(ROOT):
            parser.error(f"retry-1 requires --retry-evidence {expected.relative_to(ROOT)}")
        completion = json.loads(expected.read_text())
        if (completion.get("experiment_id") != predecessor
                or completion.get("verdict") != "INCONCLUSIVE"
                or completion.get("error") != "[Errno 98] Address already in use"):
            parser.error("retry evidence does not match the R1 port-conflict failure")
    elif args.retry_evidence:
        parser.error("--retry-evidence requires --run-label retry-1")

    head = tracked_tree_guard()
    remote_root = f"{REMOTE_BASE}/{head[:12]}"
    remote_raw = f"{remote_root}/results/raw/{args.experiment_id}"
    local_raw = ROOT / "results/raw" / args.experiment_id

    if local_raw.exists():
        raise FileExistsError(
            f"local raw already exists; refusing rerun/overwrite: {local_raw}"
        )

    sync_committed_head(remote_root)

    if remote_raw_exists(remote_raw):
        # Same committed source + same experiment ID means this invocation was
        # already started previously. Never launch it twice; just recover it.
        retrieve_raw(remote_raw, local_raw)
        summarize(local_raw, benchmark_rc=None, recovered_existing=True)
        return 0

    remote_gate = None
    if args.gate_receipt:
        remote_gate = copy_gate_receipt(
            args.gate_receipt, remote_root, args.experiment_id
        )
    remote_retry_evidence = None
    if args.retry_evidence:
        remote_retry_evidence = copy_gate_receipt(
            args.retry_evidence, remote_root, args.experiment_id
        )

    if args.ornith9_g0:
        remote_argv = ornith9_g0_argv(args.experiment_id)
    else:
        remote_argv = [
            "python3",
            "scripts/run_wbs5.py",
            "--track",
            args.track,
            "--candidate",
            args.candidate,
            "--experiment-id",
            args.experiment_id,
            "--run-label",
            args.run_label,
            "--execute-measured",
        ]
        if remote_gate:
            remote_argv += ["--gate-receipt", remote_gate]
        if args.performance_diagnostic:
            remote_argv += ["--performance-diagnostic"]
        if remote_retry_evidence:
            remote_argv += ["--retry-evidence", remote_retry_evidence]

    command = (
        f"cd {shlex.quote(remote_root)} && "
        + shlex.join(remote_argv)
    )
    proc = ssh(command, check=False)
    benchmark_rc = proc.returncode

    if not remote_raw_exists(remote_raw):
        raise RuntimeError(
            f"remote runner exited rc={benchmark_rc} without raw directory: "
            f"{remote_raw}"
        )

    retrieve_raw(remote_raw, local_raw)
    summarize(
        local_raw,
        benchmark_rc=benchmark_rc,
        recovered_existing=False,
    )

    # A benchmark verdict may legitimately be FAIL_*/INCONCLUSIVE while the
    # orchestration itself succeeded. Raw retrieval is the completion criterion.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
