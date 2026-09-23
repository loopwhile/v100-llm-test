#!/usr/bin/env python3
"""Build/preflight/launch pinned V100 server lanes; never runs benchmark requests."""
from __future__ import annotations
import argparse,json,os,shutil,socket,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODELS={
 "qwen3.8-27b":"qwen3.8-27b.json",
 "ornith-1.5-9b":"ornith-1.5-9b.json",
 "ornith-1.5-35b-a3b":"ornith-1.5-35b-a3b.json",
 "gemma4-26b-a4b":"gemma4-26b-a4b.json",
}
LLAMA_KEYS={"TARGET":"target-only","NGRAM":"ngram","MTP":"native-mtp","MTP_NGRAM":"mtp+ngram"}

def read(path): return json.loads(Path(path).read_text())
def state(root,model):
 return (read(root/"config/runtime-lock.json"),read(root/"config/profiles/runtime-lanes.json"),
         read(root/"config/profiles/topologies.json"),read(root/"config/models"/MODELS[model]))
def kv(value):
 table={"Q8_0":"q8_0","FP16":"f16","FP8":"fp8_e5m2","fp8_e5m2":"fp8_e5m2"}
 if value not in table: raise ValueError("unsupported KV: "+value)
 return table[value]
def unsupported(m,r,l,t,reason):
 return {"supported_for_planning":False,"verdict_if_executed_without_new_support":"UNSUPPORTED",
         "runtime":r,"model":m["model_id"],"lane":l,"topology":t,"reason":reason}
def spec(lanes,lane):
 for x in lanes["llama_cpp"]["required_lanes"]:
  if x["id"]==lane:return x
 raise ValueError("unknown llama lane")

def llama_plan(lock,lanes,tops,m,lane,c,topology,port):
 mc=m["llama_cpp"]; s=spec(lanes,lane)
 if not mc.get("path"): return unsupported(m,"llama.cpp",lane,topology,"exact artifact path is not pinned")
 if topology not in m.get("topology_candidates",[]): return unsupported(m,"llama.cpp",lane,topology,"topology not declared")
 if LLAMA_KEYS[lane] not in mc.get("required_spec_lanes",[]): return unsupported(m,"llama.cpp",lane,topology,"lane not declared")
 if topology=="1gpu-x2-independent" and c!=2: raise ValueError("independent topology is C2 only")
 rt=lock["runtimes"]["llama.cpp"]; cache=kv(mc["kv_candidates"][0])
 def command(gpus,p,parallel,total,tp2):
  cmd=["docker","run","--rm","--pull=never","--name",f"v100-test-{p}",
       "--label","project=v100-llm-test","--gpus",f"device={gpus}",
       "-p",f"127.0.0.1:{p}:8080","-v",f"{mc['path']}:/model/target.gguf:ro",
       "--entrypoint","llama-server",rt["image"],"-m","/model/target.gguf",
       "--host","0.0.0.0","--port","8080","-ngl","all"]
  if tp2: cmd+=["--split-mode","layer","--tensor-split","1,1"]
  cmd+=["--ctx-size",str(total),"--parallel",str(parallel),"--kv-unified",
        "--kv-unified-per-slot","131072","--batch-size","512","--ubatch-size","128",
        "--cache-type-k",cache,"--cache-type-v",cache,"--flash-attn","on",*s["args"],
        "--jinja","--reasoning","off","--metrics","--no-warmup"]
  return cmd
 if topology=="tp2-shared":
  total=tops["topologies"]["tp2-shared"][f"C{c}"]["shared_kv_pool_context"]
  commands=[command("0,1",port,c,total,True)]; endpoints=[f"http://127.0.0.1:{port}"]
 else:
  commands=[command("0",port,1,131072,False),command("1",port+1,1,131072,False)]
  endpoints=[f"http://127.0.0.1:{port}",f"http://127.0.0.1:{port+1}"]
 return {"supported_for_planning":True,"runtime":"llama.cpp",
  "runtime_revision":f"{rt['build']} / {rt['commit']}","model":m["model_id"],"model_identity":mc,
  "weight_quant":mc["weight_quant"],"kv_cache":mc["kv_candidates"][0],"lane":lane,
  "speculative":s["speculative"],"ngram":s["ngram"],"topology":topology,"concurrency":c,
  "context_tokens_per_agent":131072,"commands":commands,"environment":{},"endpoints":endpoints}

def onecat_plan(lock,m,lane,c,topology,port):
 if topology!="tp2-shared": return unsupported(m,"1Cat-vLLM",lane,topology,"1Cat lanes are TP2 shared")
 mc=m["onecat_vllm"]
 if lane=="STOCK":
  if not mc.get("path"): return unsupported(m,"1Cat-vLLM",lane,topology,"exact 1Cat artifact is pending")
  rt=lock["runtimes"]["1Cat-vLLM"]; py=os.environ.get("V100_1CAT_PYTHON","V100_1CAT_PYTHON_NOT_SET")
  cmd=[py,"-m","vllm.entrypoints.openai.api_server","--model",mc["path"],
       "--served-model-name",m["model_id"],"--trust-remote-code","--dtype","half",
       "--attention-backend","FLASH_ATTN_V100","--tensor-parallel-size","2",
       "--kv-cache-dtype",kv(mc["kv_candidates"][0]),"--max-model-len","131072",
       "--max-num-seqs",str(c),"--max-num-batched-tokens","2048",
       "--gpu-memory-utilization","0.90","--enforce-eager","--host","127.0.0.1","--port",str(port)]
  return {"supported_for_planning":True,"runtime":"1Cat-vLLM",
   "runtime_revision":f"{rt['version']} wheel sha256:{rt['sha256']}","model":m["model_id"],
   "model_identity":mc,"weight_quant":mc.get("weight_quant"),"kv_cache":mc["kv_candidates"][0],
   "lane":lane,"speculative":mc.get("speculative_candidates",["target-only"])[0],"ngram":"N/A",
   "topology":topology,"concurrency":c,"context_tokens_per_agent":131072,
   "commands":[cmd],"environment":{"CUDA_VISIBLE_DEVICES":"0,1"},"endpoints":[f"http://127.0.0.1:{port}"]}
 if lane!="SKINNY": raise ValueError("unknown onecat lane")
 sm=m.get("skinny_v11")
 if not isinstance(sm,dict):
  return unsupported(m,"1Cat-vLLM+v100-skinny",lane,topology,
   "standalone v100-skinny v1.1 has no pinned model contract for this candidate")
 rt=lock["runtimes"]["1Cat-vLLM+v100-skinny"]
 py=os.environ.get("V100_SKINNY_PYTHON","V100_SKINNY_PYTHON_NOT_SET")
 sr=os.environ.get("V100_SKINNY_ROOT","V100_SKINNY_ROOT_NOT_SET")
 mp=os.environ.get("V100_SKINNY_MODEL","V100_SKINNY_MODEL_NOT_SET")
 env={"CUDA_VISIBLE_DEVICES":"0,1","CUDA_HOME":os.environ.get("CUDA_HOME","/usr/local/cuda-12.8"),
  "TORCH_CUDA_ARCH_LIST":"7.0","VLLM_SM70_NVFP4_TURBOMIND":"0","VLLM_SM70_QUANT_BACKEND":"marlin",
  "VLLM_1CAT_ENABLE_SM70_MTP_DEFAULTS":"1","VLLM_SKINNY_NVFP4":"1","VLLM_SKINNY_QPN":"1",
  "VLLM_SKINNY_QPN2":"1","VLLM_SKINNY_LMHEAD":"1","VLLM_SKINNY_LMHEAD_NATIVE":"1",
  "VLLM_SKINNY_DROP_CT":"1","VLLM_SKINNY_NVFP4_SRC":sr+"/kernels/skinny_kernels.cu",
  "VLLM_SM70_MTP_DYNAMIC_DRAFT_VOCAB_DEFAULT":"0","VLLM_SM70_GDN_CHAIN_SPEC_FAST_BUILD":"1",
  "VLLM_SM70_QPN8_MT2":"1","VLLM_FLASH_V100_DECODE_PARTITION_SIZE":"1024"}
 cmd=[py,"-m","vllm.entrypoints.openai.api_server","--model",mp,"--served-model-name",m["model_id"],
  "--trust-remote-code","--dtype","float16","--attention-backend","FLASH_ATTN_V100",
  "--tensor-parallel-size","2","--gpu-memory-utilization","0.88","--max-model-len","131072",
  "--max-num-seqs",str(c),"--max-num-batched-tokens","4096","--limit-mm-per-prompt",'{"image":0,"video":0}',
  "--default-chat-template-kwargs",'{"enable_thinking":false}',"--reasoning-parser","qwen3",
  "--enable-auto-tool-choice","--tool-call-parser","hermes",
  "--compilation-config",'{"cudagraph_capture_sizes":[4,8]}',
  "--speculative-config",'{"method":"mtp","num_speculative_tokens":3,"draft_sample_method":"greedy","use_local_argmax_reduction":true}',
  "--host","127.0.0.1","--port",str(port)]
 return {"supported_for_planning":True,"runtime":"1Cat-vLLM+v100-skinny",
  "runtime_revision":f"skinny {rt['revision']} / 1Cat {rt['base_1cat_version']}",
  "model":m["model_id"],"model_identity":sm,"weight_quant":sm["weight_quant"],"kv_cache":"FP16",
  "lane":"SKINNY","speculative":"MTP-k3-long-context","ngram":"N/A","topology":topology,
  "concurrency":c,"context_tokens_per_agent":131072,"commands":[cmd],"environment":env,
  "endpoints":[f"http://127.0.0.1:{port}"],"experimental_tp2":True,"upstream_reference_topology":"TP4"}

def build_plan(root,model,lane,c,topology,port=18080):
 lock,lanes,tops,m=state(root,model)
 if lane in LLAMA_KEYS:return llama_plan(lock,lanes,tops,m,lane,c,topology,port)
 if lane in {"STOCK","SKINNY"}:return onecat_plan(lock,m,lane,c,topology,port)
 raise ValueError("unknown lane")

def preflight(plan):
 checks=[]
 def add(n,ok,d=""): checks.append({"name":n,"ok":bool(ok),"detail":d})
 add("supported",plan.get("supported_for_planning") is True,plan.get("reason",""))
 add("host",socket.gethostname().split(".",1)[0]=="p520-llm",socket.gethostname())
 if not plan.get("supported_for_planning"):return {"pass":False,"checks":checks}
 if plan["runtime"]=="llama.cpp":
  add("docker",shutil.which("docker") is not None)
  path=plan["model_identity"].get("path");add("model_path",bool(path) and Path(path).is_file(),str(path))
  if shutil.which("docker"):
   image=plan["commands"][0][plan["commands"][0].index("--entrypoint")+2]
   r=subprocess.run(["docker","image","inspect",image],capture_output=True,text=True)
   add("image",r.returncode==0,image)
   if r.returncode==0:
    h=subprocess.run(["docker","run","--rm","--pull=never","--entrypoint","llama-server",image,"--help"],
                     capture_output=True,text=True,timeout=60);txt=h.stdout+h.stderr
    for token in ("--spec-type","--kv-unified","--kv-unified-per-slot"):add("help:"+token,token in txt)
    if plan["lane"] in ("NGRAM","MTP_NGRAM"):add("help:ngram-simple","ngram-simple" in txt)
    if plan["lane"] in ("MTP","MTP_NGRAM"):add("help:draft-mtp","draft-mtp" in txt)
 else:
  key="V100_SKINNY_PYTHON" if plan["lane"]=="SKINNY" else "V100_1CAT_PYTHON"
  py=os.environ.get(key);add(key,bool(py) and Path(py).is_file(),str(py))
  if py and Path(py).is_file():
   code="import importlib.metadata as m\nfor n in ('1cat-vllm','1cat_vllm'):\n try:\n  print(m.version(n)); break\n except m.PackageNotFoundError: pass\nelse: raise SystemExit(2)"
   r=subprocess.run([py,"-c",code],capture_output=True,text=True,timeout=30)
   version=r.stdout.strip()
   expected="1.2.2" if plan["lane"]=="SKINNY" else "1.5.0"
   add("1cat_version",r.returncode==0 and version==expected,version or r.stderr.strip())
  if plan["lane"]=="SKINNY":
   root=os.environ.get("V100_SKINNY_ROOT");model=os.environ.get("V100_SKINNY_MODEL")
   model_rev=os.environ.get("V100_SKINNY_MODEL_REVISION")
   add("V100_SKINNY_ROOT",bool(root) and Path(root).is_dir(),str(root))
   add("V100_SKINNY_MODEL",bool(model) and Path(model).is_dir(),str(model))
   add("V100_SKINNY_MODEL_REVISION",model_rev=="554ebba9b5f1b79dc11246341960360e6ef05ef4",str(model_rev))
   if root and Path(root).is_dir() and shutil.which("git"):
    r=subprocess.run(["git","-C",root,"rev-parse","HEAD"],capture_output=True,text=True,timeout=10)
    add("skinny_revision",r.returncode==0 and r.stdout.strip()=="5b589c0dc81223e0ba65bcb3e755874723f8b515",r.stdout.strip())
 return {"pass":all(x["ok"] for x in checks),"checks":checks}

def launch(plan):
 check=preflight(plan)
 if not check["pass"]:
  print(json.dumps(check,indent=2),file=sys.stderr);raise RuntimeError("preflight failed")
 ps=[]
 try:
  for cmd in plan["commands"]:
   env=os.environ.copy();env.update({k:str(v) for k,v in plan.get("environment",{}).items()})
   ps.append(subprocess.Popen(cmd,env=env))
  return max((p.wait() for p in ps),default=0)
 except KeyboardInterrupt:
  for p in ps:
   if p.poll() is None:p.terminate()
  return 130

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,default=ROOT)
 ap.add_argument("--model",choices=sorted(MODELS),required=True)
 ap.add_argument("--lane",choices=tuple(LLAMA_KEYS)+("STOCK","SKINNY"),required=True)
 ap.add_argument("--concurrency",type=int,choices=(1,2),required=True)
 ap.add_argument("--topology",choices=("tp2-shared","1gpu-x2-independent"),default="tp2-shared")
 ap.add_argument("--port",type=int,default=18080);g=ap.add_mutually_exclusive_group()
 g.add_argument("--preflight",action="store_true");g.add_argument("--execute",action="store_true");a=ap.parse_args()
 p=build_plan(a.root.resolve(),a.model,a.lane,a.concurrency,a.topology,a.port)
 if a.preflight:print(json.dumps({"plan":p,"preflight":preflight(p)},ensure_ascii=False,indent=2));return 0
 if a.execute:return launch(p)
 print(json.dumps(p,ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
