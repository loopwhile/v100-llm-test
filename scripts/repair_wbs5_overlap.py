#!/usr/bin/env python3
"""Reconcile one completed WBS5 raw directory from preserved llama.cpp logs."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import wbs5_evidence as evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    args = parser.parse_args()
    result = evidence.reconcile_overlap_from_logs(args.raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result and result.get("active_overlap") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
