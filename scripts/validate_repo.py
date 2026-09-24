#!/usr/bin/env python3
"""Offline structural validation for v100-llm-test."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED_MODELS={"qwen3.8-27b.json","ornith-1.5-9b.json","ornith-1.5-35b-a3b.json","gemma4-26b-a4b.json"}
LLAMA_LANES=["TARGET","NGRAM","MTP","MTP_NGRAM"]
MODEL_SPEC_BY_FILE={
 "qwen3.8-27b.json":["target-only","ngram"],
 "ornith-1.5-9b.json":["target-only","ngram","native-mtp","mtp+ngram"],
 "ornith-1.5-35b-a3b.json":["target-only","ngram","native-mtp","mtp+ngram"],
 "gemma4-26b-a4b.json":["target-only","ngram","native-mtp","mtp+ngram"],
}

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
 perf=read("workloads/performance/v1.json")

 check([x["id"] for x in lanes["llama_cpp"]["required_lanes"]]==LLAMA_LANES,"llama lane contract mismatch")
 check(accept["runtime_requirements"]["llama_cpp"]["required_lanes"]==LLAMA_LANES,"acceptance lane mismatch")
 check(accept["runtime_requirements"]["llama_cpp"]["target_ngram_pair_required"] is True,"TARGET/NGRAM must be required")
 check(accept["runtime_requirements"]["onecat_vllm"]["v100_skinny_required"] is True,"skinny must be required")
 check(tops["context_tokens_per_agent"]==131072,"topology context target mismatch")
 check(tops["topologies"]["tp2-shared"]["C2"]["shared_kv_pool_context"]==262144,"C2 shared pool must be 256K")
 check(tops["topologies"]["tp2-shared"]["C2"]["per_slot_context"]==131072,"C2 per-slot must be 128K")
 independent=tops["topologies"]["1gpu-x2-independent"]
 check(independent["gateway"]["required"] is True and independent["gateway"]["runtime"]=="LiteLLM","1GPUx2 must require LiteLLM")
 check(independent["gateway"]["direct_backend_routing_is_acceptance"] is False,"direct backend routing must not be acceptance")
 check(independent["C1"]["client_path"]=="single LiteLLM endpoint" and independent["C2"]["client_path"]=="single LiteLLM endpoint","C1/C2 must use LiteLLM client path")
 check(accept["topology_requirements"]["1gpu-x2-independent"]["c1_and_c2_must_include_gateway"] is True,"acceptance must include LiteLLM for 1GPUx2")
 litellm=lock["runtimes"]["LiteLLM"]
 check(litellm["version"]=="1.101.0","LiteLLM version drift")
 check(litellm["commit"]=="18243cd7af4c3325165ba68b21379e2719e051c7","LiteLLM commit drift")
 skinny=lock["runtimes"]["1Cat-vLLM+v100-skinny"]
 check(skinny["revision"]=="5b589c0dc81223e0ba65bcb3e755874723f8b515","skinny revision drift")
 check(skinny["base_1cat_version"]=="1.2.2","skinny base 1Cat drift")

 model_dir=ROOT/"config/models"
 check({p.name for p in model_dir.glob("*.json")}==EXPECTED_MODELS,"candidate model set mismatch")
 for path in sorted(model_dir.glob("*.json")):
  model=json.loads(path.read_text())
  check(model["context_target"]==131072,f"{path.name}: context target mismatch")
  check(model["llama_cpp"]["required_spec_lanes"]==MODEL_SPEC_BY_FILE[path.name],f"{path.name}: llama spec lanes mismatch")
  check(model["onecat_vllm"]["required_backend_lanes"]==["stock","v100-skinny"],f"{path.name}: backend lanes mismatch")

 q38=read("config/models/qwen3.8-27b.json")["onecat_vllm"]
 o9=read("config/models/ornith-1.5-9b.json")["onecat_vllm"]
 o35=read("config/models/ornith-1.5-35b-a3b.json")["onecat_vllm"]
 g4=read("config/models/gemma4-26b-a4b.json")["onecat_vllm"]
 check(q38.get("planning_ready") is True and q38.get("kv_candidates")==["fp8_e4m3"] and q38.get("speculative_candidates")==["target-only"] and q38.get("attention_backend")=="FLASH_ATTN_V100","WBS 2.2.1 Qwen STOCK contract drift")
 check(o9.get("planning_ready") is True and o9.get("kv_candidates")==["FP16"] and o9.get("speculative_candidates")==["MTP"],"WBS 2.2.2 Ornith9 STOCK identity drift")
 check(o9.get("attention_backend")=="FLASH_ATTN_V100","WBS 2.2.2 target attention backend drift")
 o9spec=o9.get("speculative_config") or {}
 check(o9spec.get("method")=="mtp" and o9spec.get("num_speculative_tokens")==1 and o9spec.get("attention_backend")=="TRITON_ATTN","WBS 2.2.2 MTP1 contract drift")
 check(o35.get("planning_ready") is True and o35.get("kv_candidates")==["fp8_e5m2"] and o35.get("speculative_candidates")==["target-only"],"WBS 2.2.3 Ornith35 STOCK contract drift")
 check(o35.get("attention_backend")=="FLASH_ATTN_V100","WBS 2.2.3 attention backend drift")
 check(g4.get("planning_ready") is True and g4.get("repository")=="nvidia/Gemma-4-26B-A4B-NVFP4","WBS 2.2.4 Gemma artifact drift")
 check(g4.get("revision")=="a19cfe00be84568a6867111c9a68c9c44fdcffe6","WBS 2.2.4 Gemma revision drift")
 check(g4.get("path")=="/srv/models/gemma-4-26b-a4b-nvfp4" and g4.get("kv_candidates")==["FP16"],"WBS 2.2.4 Gemma local/KV contract drift")
 check(g4.get("attention_backend")=="TRITON_ATTN" and g4.get("speculative_candidates")==["target-only"],"WBS 2.2.4 Gemma runtime contract drift")
 check((ROOT/"docs/WBS-2.2-execution-manifest.md").is_file(),"missing WBS 2.2 execution manifest")
 check((ROOT/"scripts/run_c1_onecat.py").is_file(),"missing 1Cat C1 runner")

 check(cap["context_tokens"]==131072 and len(cap["requests"])==1,"capacity workload mismatch")
 check(cap.get("output_tokens")==2048 and cap.get("min_output_tokens")==256,"capacity output objective mismatch")
 check(c2["context_tokens"]==131072 and len(c2["requests"])==2,"C2 workload mismatch")
 check(c2.get("output_tokens")==2048 and c2.get("min_output_tokens")==256,"C2 output objective mismatch")
 check(c2.get("independent_projects_required") is True,"C2 independence flag missing")
 ids=[x["project_id"] for x in c2["requests"]]
 check(len(set(ids))==2,"C2 project IDs must differ")
 material=["".join(x["seed_blocks"]) for x in c2["requests"]]
 check(material[0]!=material[1],"C2 seed material must differ")
 check(perf["context_tokens"]==131072 and len(perf["requests"])==2,"performance workload mismatch")
 check(perf.get("output_tokens")==4096 and perf.get("min_output_tokens")==1024,"performance output objective mismatch")
 check(perf.get("diversify_identifiers") is True,"performance workload must diversify repeated identifiers")
 check(perf.get("independent_projects_required") is True,"performance workload independence flag missing")

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
