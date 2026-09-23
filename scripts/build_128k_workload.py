#!/usr/bin/env python3
"""Materialize deterministic 128K C1/C2 workloads using the live server tokenizer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from bench_harness import HTTPAdapter, canon, sha


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported workload schema")
    if manifest.get("context_tokens") != 131072:
        raise ValueError("primary manifests must target 131072 tokens")
    if type(manifest.get("output_tokens")) is not int or manifest["output_tokens"] < 1:
        raise ValueError("invalid output_tokens")
    requests = manifest.get("requests")
    if not isinstance(requests, list) or len(requests) not in (1, 2):
        raise ValueError("manifest must contain one or two requests")
    ids = [item.get("project_id") for item in requests]
    if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("project_id values must be non-empty and unique")
    if len(requests) == 2 and not manifest.get("independent_projects_required"):
        raise ValueError("C2 manifest must require independent projects")
    return manifest


def render(spec: dict, units: int, pad_units: int = 0) -> str:
    if units < 1 or pad_units < 0:
        raise ValueError("invalid render size")
    blocks = spec["seed_blocks"]
    parts = [
        f"# {spec['title']}\n",
        f"# project_id={spec['project_id']}\n",
        "# Synthetic deterministic capacity material follows.\n",
    ]
    for i in range(units):
        block = blocks[i % len(blocks)]
        parts.append(
            f"\n# --- {spec['project_id']} SECTION {i + 1:06d} ---\n{block.rstrip()}\n"
        )
    if pad_units:
        marker = f" {spec['project_id']}_PAD"
        parts.append("\n# deterministic calibration padding\n" + marker * pad_units + "\n")
    parts.append("\n# FINAL REQUEST\n" + spec["final_instruction"].strip() + "\n")
    return "".join(parts)


def payload_for(model: str, thinking: bool, content: str, output_tokens: int, sampling: dict) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": output_tokens,
        "stream": True,
        **sampling,
        "chat_template_kwargs": {"enable_thinking": thinking},
    }


def count(adapter, model, thinking, content, output_tokens, sampling):
    receipt = adapter.receipt(payload_for(model, thinking, content, output_tokens, sampling))
    tokens = receipt.get("prompt_tokens")
    if type(tokens) is not int or tokens < 1:
        raise ValueError("runtime returned invalid prompt token count")
    return tokens, receipt


def calibrate(adapter, manifest: dict, spec: dict, model: str, thinking: bool) -> tuple[dict, dict]:
    context = manifest["context_tokens"]
    output_tokens = manifest["output_tokens"]
    target = context - output_tokens
    minimum_total = int(context * manifest.get("min_context_utilization", 0.99))
    sampling = manifest.get("sampling", {})

    low, high = 1, 1
    while True:
        text = render(spec, high)
        tokens, _ = count(adapter, model, thinking, text, output_tokens, sampling)
        if tokens > target:
            break
        low = high
        high *= 2
        if high > 131072:
            raise ValueError("unable to bracket target prompt length")

    best_units = low
    lo, hi = low, high - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        text = render(spec, mid)
        tokens, _ = count(adapter, model, thinking, text, output_tokens, sampling)
        if tokens <= target:
            best_units = mid
            lo = mid + 1
        else:
            hi = mid - 1

    base = render(spec, best_units)
    base_tokens, _ = count(adapter, model, thinking, base, output_tokens, sampling)

    best_pad = 0
    lo, hi = 0, max(256, (target - base_tokens) * 4 + 256)
    while lo <= hi:
        mid = (lo + hi) // 2
        text = render(spec, best_units, mid)
        tokens, _ = count(adapter, model, thinking, text, output_tokens, sampling)
        if tokens <= target:
            best_pad = mid
            lo = mid + 1
        else:
            hi = mid - 1

    content = render(spec, best_units, best_pad)
    prompt_tokens, receipt = count(
        adapter, model, thinking, content, output_tokens, sampling
    )
    total = prompt_tokens + output_tokens
    if total > context:
        raise ValueError("calibration exceeded context budget")
    if total < minimum_total:
        raise ValueError(
            f"calibration underfilled context: total={total}, minimum={minimum_total}"
        )

    request = {
        "id": spec["id"],
        "project_id": spec["project_id"],
        "messages": [{"role": "user", "content": content}],
        "max_tokens": output_tokens,
        "check": "nonempty",
    }
    evidence = {
        "request_id": spec["id"],
        "project_id": spec["project_id"],
        "section_units": best_units,
        "padding_units": best_pad,
        "prompt_tokens": prompt_tokens,
        "reserved_output_tokens": output_tokens,
        "total_budget_used": total,
        "utilization": total / context,
        "raw_prompt_sha256": sha(canon(request["messages"])),
        "tokenizer_receipt": receipt,
    }
    return request, evidence


def build(manifest: dict, adapter, model: str, thinking: bool = False) -> dict:
    requests, evidence = [], []
    for spec in manifest["requests"]:
        request, item = calibrate(adapter, manifest, spec, model, thinking)
        requests.append(request)
        evidence.append(item)

    hashes = [item["raw_prompt_sha256"] for item in evidence]
    if len(hashes) == 2 and len(set(hashes)) != 2:
        raise ValueError("C2 materialized prompts are not independent")

    return {
        "version": manifest["workload_id"],
        "source_manifest_sha256": sha(canon(manifest)),
        "context_tokens": manifest["context_tokens"],
        "sampling": manifest.get("sampling", {}),
        "requests": requests,
        "build_evidence": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--runtime", required=True, choices=("llama.cpp", "1Cat-vLLM", "1Cat-vLLM+v100-skinny"))
    parser.add_argument("--model", required=True)
    parser.add_argument("--thinking", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    adapter_runtime = "llama.cpp" if args.runtime == "llama.cpp" else "1Cat-vLLM"
    generated = build(
        manifest,
        HTTPAdapter(args.base_url, adapter_runtime),
        args.model,
        args.thinking,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "version": generated["version"],
        "requests": [
            {
                "id": item["request_id"],
                "prompt_tokens": item["prompt_tokens"],
                "total_budget_used": item["total_budget_used"],
                "utilization": item["utilization"],
                "raw_prompt_sha256": item["raw_prompt_sha256"],
            }
            for item in generated["build_evidence"]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
