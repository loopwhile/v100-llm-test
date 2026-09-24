#!/usr/bin/env python3
"""Prepare candidate pool of genuine source/doc/config files for realistic 128K diagnostic."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parent

PROJECTS = ["v100-llm-test", "qwen3.8-bench", "p520-inference-lab", "ariadne-cli"]
EXTS = {".py", ".md", ".json", ".yaml", ".yml", ".sh", ".ts"}

EXCLUDE_PARTS = {
    ".git", "__pycache__", "venv", ".venv", "node_modules",
    "raw", "dist", "build", "results", "reports", "coverage", ".pytest_cache", "workloads"
}

FORBIDDEN_PHRASES = [
    "Produce at least 256 tokens",
    "decode behavior is measurable",
    "Synthetic deterministic benchmark material follows"
]

EXCLUDE_NAMES = {
    "package-lock.json", "yarn.lock", "poetry.lock", "candidate_pool.json",
    "v100_q38_realistic_128k.json", "payloads.json", "workload.json",
    "metrics.json", "requests.json", "completion.json"
}


def collect():
    seen_hashes = set()
    pool = []

    for proj in PROJECTS:
        p_path = WS / proj
        if not p_path.exists():
            continue
        for f in sorted(p_path.rglob("*")):
            if not f.is_file() or f.suffix not in EXTS:
                continue
            if any(part in EXCLUDE_PARTS or part.startswith(".") for part in f.parts):
                continue
            if f.name in EXCLUDE_NAMES:
                continue
            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue

            lines = content.splitlines()
            # Select files with moderate size to get high diversity (at least 100+ files)
            if not (15 <= len(lines) <= 350 and 300 <= len(content) <= 18000):
                continue

            # Skip large auto-generated JSONs or base64 dumps
            if f.suffix == ".json" and len(content) > 5000 and "{" not in content[:50]:
                continue

            # Skip files containing benchmark meta-instructions
            if any(phrase in content for phrase in FORBIDDEN_PHRASES):
                continue

            h = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            rel_path = f"{proj}/{f.relative_to(p_path)}"
            lang = f.suffix.lstrip(".")
            if lang in ("yml", "yaml"):
                lang = "yaml"

            pool.append({
                "path": rel_path,
                "project": proj,
                "filename": f.name,
                "language": lang,
                "lines": len(lines),
                "chars": len(content),
                "sha256": h,
                "content": content,
            })

    # Sort deterministically
    pool.sort(key=lambda x: (x["project"], x["language"], x["path"]))

    out_dir = ROOT / "workloads/diagnostic"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "candidate_pool.json"
    out_file.write_text(json.dumps({"schema_version": 1, "total_files": len(pool), "files": pool}, indent=2), encoding="utf-8")
    print(f"Wrote {len(pool)} unique files to {out_file}")

    by_proj = {}
    by_lang = {}
    for item in pool:
        by_proj[item["project"]] = by_proj.get(item["project"], 0) + 1
        by_lang[item["language"]] = by_lang.get(item["language"], 0) + 1
    print("Files by project:", by_proj)
    print("Files by language:", by_lang)


if __name__ == "__main__":
    collect()
