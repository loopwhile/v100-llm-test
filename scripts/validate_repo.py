#!/usr/bin/env python3
"""Offline structural validation for v100-llm-test."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_MODELS={"qwen3.8-27b.json","ornith-1.5-9b.json","ornith-1.5-35b-a3b.json","gemma4-26b-a4b.json"}
LLAMA_LANES=["TARGET","NGRAM","MTP","MTP_NGRAM"]
MODEL_SPEC=["target-only","ngram","native-mtp","mtp+ngram"]

def read(path): return json.loads((ROOT/path).read_text())

def validate():
 errors=[]
 def check(ok,msg):
  if not ok: errors.append(msg)

 lanes=read("config/profiles/runtime-lanes.json")
 accept=read("config/profiles/acceptance-128k.json")
 tops=read("config/profiles/topologies.json")
 lock=read("config/runtime-lock.json")
 cap=read("workloads/capacity/v1.json")
 c2=read("workloads/concurrency/v1.json")

 check([x["id"] for x in lanes["llama_cpp"]["required_lanes"]]==LLAMA_LANES,"llama lane contract mismatch")
 check(accept["runtime_requirements"]["llama_cpp"]["required_lanes"]==LLAMA_LANES,"acceptance lane mismatch")
 check(accept["runtime_requirements"]["llama_cpp"]["target_ngram_pair_required"] is True,"TARGET/NGRAM must be required")
 check(accept["runtime_requirements"]["onecat_vllm"]["v100_skinny_required"] is True,"skinny must be required")
 check(tops["context_tokens_per_agent"]==131072,"topology context target mismatch")
 check(tops["topologies"]["tp2-shared"]["C2"]["shared_kv_pool_context"]==262144,"C2 shared pool must be 256K")
 check(tops["topologies"]["tp2-shared"]["C2"]["per_slot_context"]==131072,"C2 per-slot must be 128K")
 skinny=lock["runtimes"]["1Cat-vLLM+v100-skinny"]
 check(skinny["revision"]=="5b589c0dc81223e0ba65bcb3e755874723f8b515","skinny revision drift")
 check(skinny["base_1cat_version"]=="1.2.2","skinny base 1Cat drift")

 model_dir=ROOT/"config/models"
 check({p.name for p in model_dir.glob("*.json")}==EXPECTED_MODELS,"candidate model set mismatch")
 for path in sorted(model_dir.glob("*.json")):
  model=json.loads(path.read_text())
  check(model["context_target"]==131072,f"{path.name}: context target mismatch")
  check(model["llama_cpp"]["required_spec_lanes"]==MODEL_SPEC,f"{path.name}: llama spec lanes mismatch")
  check(model["onecat_vllm"]["required_backend_lanes"]==["stock","v100-skinny"],f"{path.name}: backend lanes mismatch")

 check(cap["context_tokens"]==131072 and len(cap["requests"])==1,"capacity workload mismatch")
 check(c2["context_tokens"]==131072 and len(c2["requests"])==2,"C2 workload mismatch")
 check(c2.get("independent_projects_required") is True,"C2 independence flag missing")
 ids=[x["project_id"] for x in c2["requests"]]
 check(len(set(ids))==2,"C2 project IDs must differ")
 material=["".join(x["seed_blocks"]) for x in c2["requests"]]
 check(material[0]!=material[1],"C2 seed material must differ")

 for path in ("docs/WBS.md","docs/test-matrix.md","docs/runtime-lanes.md","docs/workload-contract.md"):
  check((ROOT/path).is_file(),f"missing document: {path}")
 return errors

def main():
 errors=validate()
 if errors:
  print("Repository contract: FAIL")
  for item in errors: print("- "+item)
  return 2
 print("Repository contract: PASS")
 return 0

if __name__=="__main__":
 raise SystemExit(main())
