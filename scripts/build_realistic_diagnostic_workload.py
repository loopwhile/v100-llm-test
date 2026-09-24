#!/usr/bin/env python3
"""Build and calibrate diversified realistic 128K diagnostic workload using live Qwen3.8 tokenizer.

Ensures:
- Exactly genuine files from candidate pool.
- At least 100+ unique logical sections/files across multiple projects and languages.
- No repeated synthetic blocks, no repetitive padding, no repetitive meta-instructions.
- Post-template prompt token count strictly in [128,500, 129,023].
- Output reserve 2048, total tokens <= 131072.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = "/srv/models/qwen3.8-vllm/Qwen3.8-27B-QUASAR-NVFP4"
TARGET_MIN_TOKENS = 128500
TARGET_MAX_TOKENS = 129023
TARGET_OPTIMAL_TOKENS = 128800
RESERVED_OUTPUT = 2048
MAX_MODEL_LEN = 131072

HEADER_INTRO = (
    "# Project Snapshot: Multi-Repository LLM Serving & Benchmark Toolchain\n"
    "# This snapshot contains genuine source files, test suites, runtime configs, and documentation\n"
    "# from the benchmark and serving toolchain across multiple repositories.\n"
    "# Please inspect the codebase across the different components and files.\n\n"
)

TASK_INSTRUCTION = (
    "\n# ==============================================================================\n"
    "# TASK INSTRUCTION\n"
    "# ==============================================================================\n"
    "Review the supplied project snapshot. Identify one concrete correctness risk that involves at least two files or components. Explain why it is a risk and give a minimal verification plan. Be specific and concise.\n"
)


def format_file_section(file_info: dict, content: str | None = None) -> str:
    body = content if content is not None else file_info["content"]
    return (
        f"# ==============================================================================\n"
        f"# File: {file_info['path']}\n"
        f"# Project: {file_info['project']} | Language: {file_info['language']} | Lines: {file_info['lines']}\n"
        f"# ==============================================================================\n"
        f"{body.rstrip()}\n\n"
    )


def apply_template_and_count(tok, user_content: str) -> tuple[int, str]:
    messages = [{"role": "user", "content": user_content}]
    prompt_str = tok.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True,
        reasoning_effort="medium",
    )
    tokens = tok.encode(prompt_str)
    return len(tokens), prompt_str


def build_workload():
    pool_file = ROOT / "workloads/diagnostic/candidate_pool.json"
    if not pool_file.is_file():
        raise FileNotFoundError(f"Missing {pool_file}")

    print(f"Loading candidate pool from {pool_file}...")
    pool_data = json.loads(pool_file.read_text(encoding="utf-8"))
    files = pool_data["files"]
    print(f"Total candidates available: {len(files)}")

    print(f"Loading tokenizer from {MODEL_PATH}...")
    tok = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    print(f"Tokenizer loaded. Vocab size: {len(tok)}")

    # We want high diversity with >= 100 unique files.
    # Group candidates by project to round-robin select and balance composition.
    by_proj = {}
    for f in files:
        by_proj.setdefault(f["project"], []).append(f)

    # Sort each group deterministically (prioritize python files, then yaml/sh/json/md)
    def priority_sort(item):
        lang_score = {"py": 0, "sh": 1, "yaml": 2, "json": 3, "md": 4}.get(item["language"], 5)
        # prefer moderate sized files (1000 - 4000 chars) to get ~150-200 files
        char_score = abs(item["chars"] - 2500)
        return (lang_score, char_score, item["path"])

    for proj in by_proj:
        by_proj[proj].sort(key=priority_sort)

    # Stratified selection to ensure all 4 projects and multiple languages are well represented
    chosen_files = []
    used_hashes = set()
    used_paths = set()

    proj_keys = ["v100-llm-test", "qwen3.8-bench", "p520-inference-lab", "ariadne-cli"]
    indices = {p: 0 for p in proj_keys}

    # Start with base prompt
    current_sections = []
    
    # We will assemble files until we reach close to target
    print("Selecting files with stratified sampling across projects and languages...")
    while True:
        added_any = False
        for p in proj_keys:
            idx = indices[p]
            p_list = by_proj.get(p, [])
            while idx < len(p_list):
                cand = p_list[idx]
                idx += 1
                if cand["sha256"] in used_hashes or cand["path"] in used_paths:
                    continue
                used_hashes.add(cand["sha256"])
                used_paths.add(cand["path"])
                chosen_files.append(cand)
                current_sections.append(format_file_section(cand))
                added_any = True
                break
            indices[p] = idx

        # Check token count every 10 files
        if len(chosen_files) % 10 == 0:
            test_content = HEADER_INTRO + "".join(current_sections) + TASK_INSTRUCTION
            cnt, _ = apply_template_and_count(tok, test_content)
            print(f"  Chosen files: {len(chosen_files)}, post-template tokens: {cnt}")
            if cnt >= TARGET_MIN_TOKENS:
                break

        if not added_any:
            break

    # Now fine-tune to land in [TARGET_MIN_TOKENS, TARGET_MAX_TOKENS] (target ~128,800)
    test_content = HEADER_INTRO + "".join(current_sections) + TASK_INSTRUCTION
    cnt, _ = apply_template_and_count(tok, test_content)

    print(f"Initial pass: {len(chosen_files)} files, tokens = {cnt}")

    # If cnt exceeds TARGET_MAX_TOKENS, pop files until below
    while cnt > TARGET_MAX_TOKENS and len(chosen_files) > 100:
        popped = chosen_files.pop()
        current_sections.pop()
        used_hashes.remove(popped["sha256"])
        used_paths.remove(popped["path"])
        test_content = HEADER_INTRO + "".join(current_sections) + TASK_INSTRUCTION
        cnt, _ = apply_template_and_count(tok, test_content)
        print(f"  Popped {popped['path']}, tokens now: {cnt}")

    # If cnt < TARGET_OPTIMAL_TOKENS, search remaining candidates for a file that gets us closer
    remaining = [
        f for f in files
        if f["sha256"] not in used_hashes and f["path"] not in used_paths
    ]

    # Try to add files that fit within budget
    for cand in remaining:
        sec = format_file_section(cand)
        cand_tokens = len(tok.encode(sec))
        if cnt + cand_tokens <= TARGET_OPTIMAL_TOKENS:
            chosen_files.append(cand)
            current_sections.append(sec)
            used_hashes.add(cand["sha256"])
            used_paths.add(cand["path"])
            cnt += cand_tokens
            print(f"  Added fitting file {cand['path']} (+{cand_tokens} tok) -> total tokens: {cnt}")

    # Now if still below TARGET_MIN_TOKENS (or to hit ~128,800 precisely):
    # Take the next genuine candidate file, and include an exact prefix of its lines (clean truncate)
    if cnt < TARGET_OPTIMAL_TOKENS:
        next_cand = None
        for cand in remaining:
            if cand["sha256"] not in used_hashes and cand["path"] not in used_paths:
                next_cand = cand
                break

        if next_cand is None:
            raise RuntimeError("Ran out of candidate files!")

        needed_tokens = TARGET_OPTIMAL_TOKENS - cnt
        print(f"Fine-tuning with genuine prefix of {next_cand['path']} to add ~{needed_tokens} tokens...")

        cand_lines = next_cand["content"].splitlines(keepends=True)
        # Binary search for exact line count that lands in [TARGET_MIN_TOKENS, TARGET_MAX_TOKENS]
        lo, hi = 1, len(cand_lines)
        best_lines = lo
        best_tokens = cnt

        while lo <= hi:
            mid = (lo + hi) // 2
            partial_content = "".join(cand_lines[:mid])
            partial_sec = format_file_section(next_cand, partial_content)
            test_content = HEADER_INTRO + "".join(current_sections) + partial_sec + TASK_INSTRUCTION
            cur_cnt, _ = apply_template_and_count(tok, test_content)

            if cur_cnt <= TARGET_OPTIMAL_TOKENS:
                best_lines = mid
                best_tokens = cur_cnt
                lo = mid + 1
            else:
                hi = mid - 1

        partial_content = "".join(cand_lines[:best_lines])
        partial_sec = format_file_section(next_cand, partial_content)
        current_sections.append(partial_sec)
        chosen_files.append({
            "path": next_cand["path"] + f" (lines 1-{best_lines})",
            "project": next_cand["project"],
            "filename": next_cand["filename"],
            "language": next_cand["language"],
            "lines": best_lines,
            "chars": len(partial_content),
            "sha256": hashlib.sha256(partial_content.encode("utf-8")).hexdigest(),
        })

    # Final assembly and verification
    final_user_content = HEADER_INTRO + "".join(current_sections) + TASK_INSTRUCTION
    final_post_template_tokens, final_post_template_str = apply_template_and_count(tok, final_user_content)

    print("\n================== WORKLOAD VALIDATION ==================")
    print(f"Total Unique Files: {len(chosen_files)}")
    print(f"Post-template Prompt Tokens: {final_post_template_tokens}")
    print(f"Reserved Output Tokens: {RESERVED_OUTPUT}")
    print(f"Total Context Budget: {final_post_template_tokens + RESERVED_OUTPUT} / {MAX_MODEL_LEN}")

    if not (TARGET_MIN_TOKENS <= final_post_template_tokens <= TARGET_MAX_TOKENS):
        raise ValueError(
            f"Token count {final_post_template_tokens} outside target range [{TARGET_MIN_TOKENS}, {TARGET_MAX_TOKENS}]"
        )
    if final_post_template_tokens + RESERVED_OUTPUT > MAX_MODEL_LEN:
        raise ValueError("Exceeded max_model_len!")
    if len(chosen_files) < 100:
        raise ValueError(f"File count {len(chosen_files)} < 100!")

    # Check for identical duplicate blocks
    seen_blocks = set()
    for sec in current_sections:
        h = hashlib.sha256(sec.encode("utf-8")).hexdigest()
        if h in seen_blocks:
            raise ValueError(f"Duplicate section detected: {h}")
        seen_blocks.add(h)
    print("Duplicate Section Check: PASS (All sections unique)")

    # Check for synthetic repetition phrases
    if "Produce at least 256 tokens" in final_user_content:
        raise ValueError("Forbidden benchmark meta-instruction found in user prompt!")
    print("Meta-instruction Check: PASS (No meta-instructions in context)")

    by_proj_final = {}
    by_lang_final = {}
    for f in chosen_files:
        by_proj_final[f["project"]] = by_proj_final.get(f["project"], 0) + 1
        by_lang_final[f["language"]] = by_lang_final.get(f["language"], 0) + 1

    print("Final Files by Project:", by_proj_final)
    print("Final Files by Language:", by_lang_final)

    # Save workload
    workload = {
        "schema_version": 1,
        "workload_id": "V100-EXP-DIAG-REALISTIC-128K-v1",
        "mode": "diagnostic_realistic",
        "context_tokens": MAX_MODEL_LEN,
        "output_tokens": RESERVED_OUTPUT,
        "min_output_tokens": 256,
        "min_context_utilization": round((final_post_template_tokens + RESERVED_OUTPUT) / MAX_MODEL_LEN, 4),
        "source": "diversified multi-repository genuine codebase snapshot (100+ unique files)",
        "sampling": {
            "temperature": 0.7,
            "top_p": 0.8,
            "seed": 520,
        },
        "thinking": True,
        "reasoning_effort": "medium",
        "requests": [
            {
                "id": "diag-realistic-project",
                "project_id": "REALISTIC-SNAPSHOT",
                "title": "Realistic Codebase Snapshot Multi-File Correctness Review",
                "messages": [{"role": "user", "content": final_user_content}],
                "max_tokens": RESERVED_OUTPUT,
                "min_output_tokens": 256,
                "check": "nonempty",
                "expected_post_template_tokens": final_post_template_tokens,
                "final_instruction": TASK_INSTRUCTION.strip(),
            }
        ],
    }

    out_workload_path = ROOT / "workloads/diagnostic/v100_q38_realistic_128k.json"
    out_workload_path.parent.mkdir(parents=True, exist_ok=True)
    out_workload_path.write_text(json.dumps(workload, indent=2), encoding="utf-8")
    print(f"Saved calibrated workload to {out_workload_path}")

    # Save detailed receipt
    receipt = {
        "workload_id": "V100-EXP-DIAG-REALISTIC-128K-v1",
        "post_template_prompt_tokens": final_post_template_tokens,
        "reserved_output_tokens": RESERVED_OUTPUT,
        "total_budget": final_post_template_tokens + RESERVED_OUTPUT,
        "max_model_len": MAX_MODEL_LEN,
        "total_files": len(chosen_files),
        "by_project": by_proj_final,
        "by_language": by_lang_final,
        "prompt_sha256": hashlib.sha256(final_user_content.encode("utf-8")).hexdigest(),
        "files_manifest": [
            {"path": f["path"], "project": f["project"], "language": f["language"], "lines": f["lines"]}
            for f in chosen_files
        ],
    }
    receipt_path = ROOT / "workloads/diagnostic/workload_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Saved detailed receipt to {receipt_path}")
    print("Calibration SUCCESSFUL!")


if __name__ == "__main__":
    build_workload()
