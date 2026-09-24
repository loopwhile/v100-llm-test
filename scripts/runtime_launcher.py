#!/usr/bin/env python3
"""Build/preflight/launch pinned V100 server lanes; never runs benchmark requests."""
from __future__ import annotations
import argparse,json,os,shutil,socket,subprocess,sys,time
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
 table={"Q8_0":"q8_0","FP16":"f16","fp8_e4m3":"fp8_e4m3","fp8_e5m2":"fp8_e5m2"}
 if value not in table: raise ValueError("unsupported KV: "+value)
 return table[value]
def unsupported(m,r,l,t,reason):
 return {"supported_for_planning":False,"verdict_if_executed_without_new_support":"UNSUPPORTED",
         "runtime":r,"model":m["model_id"],"lane":l,"topology":t,"reason":reason}
def spec(lanes,lane):
 for x in lanes["llama_cpp"]["required_lanes"]:
  if x["id"]==lane:return x
 raise ValueError("unknown llama lane")

def litellm_gateway(lock,m,backend_endpoints,port):
 rt=lock["runtimes"]["LiteLLM"];model=m["model_id"]
 deployments=[]
 for endpoint in backend_endpoints:
  deployments.append({"model_name":model,"litellm_params":{"model":"openai/"+model,"api_base":endpoint+"/v1","api_key":"local-no-key","max_parallel_requests":1,"timeout":1800,"stream_timeout":1800,"max_retries":0}})
 cfg={"model_list":deployments,"router_settings":{"routing_strategy":"least-busy","num_retries":0}}
 cmd=["docker","run","--rm","--pull=never","--name","v100-test-litellm","--label","project=v100-llm-test","--network","host","-v","{LITELLM_CONFIG}:/app/config.yaml:ro",rt["image"],"--config","/app/config.yaml","--host","127.0.0.1","--port",str(port)]
 return {"runtime":"LiteLLM","runtime_revision":f"{rt['version']} / {rt['commit']}","image":rt["image"],"endpoint":f"http://127.0.0.1:{port}","routing_strategy":"least-busy","backend_max_parallel_requests":1,"config":cfg,"command":cmd}

def attach_gateway(plan,lock,m,backend_endpoints,gateway_port):
 plan["backend_endpoints"]=list(backend_endpoints);plan["gateway"]=litellm_gateway(lock,m,backend_endpoints,gateway_port);plan["endpoints"]=[plan["gateway"]["endpoint"]]
 return plan

def llama_plan(lock,lanes,tops,m,lane,c,topology,port,gateway_port=18079):
 lane_to_spec={"TARGET":"target-only","NGRAM":"ngram","MTP":"native-mtp","MTP_NGRAM":"mtp+ngram"}
 declared_specs=set(m.get("llama_cpp",{}).get("required_spec_lanes",[]))
 requested_spec=lane_to_spec.get(lane)
 if requested_spec not in declared_specs:return unsupported(m,"llama.cpp",lane,topology,"lane is outside this model artifact contract")
 mc=m["llama_cpp"]; s=spec(lanes,lane)
 if not mc.get("path"): return unsupported(m,"llama.cpp",lane,topology,"exact artifact path is not pinned")
 if topology not in m.get("topology_candidates",[]): return unsupported(m,"llama.cpp",lane,topology,"topology not declared")
 if LLAMA_KEYS[lane] not in mc.get("required_spec_lanes",[]): return unsupported(m,"llama.cpp",lane,topology,"lane not declared")
 rt=lock["runtimes"]["llama.cpp"]; cache=kv(mc["kv_candidates"][0])
 def command(gpus,p,parallel,total,tp2):
  cmd=["docker","run","--rm","--pull=never","--name",f"v100-test-{p}",
       "--label","project=v100-llm-test","--gpus",(f'"device={gpus}"' if "," in gpus else f"device={gpus}"),
       "-p",f"127.0.0.1:{p}:8080","-v",f"{mc['path']}:/model/target.gguf:ro",
       "--entrypoint","llama-server",rt["image"],"-m","/model/target.gguf",
       "--host","0.0.0.0","--port","8080","-ngl","all"]
  if tp2: cmd+=["--split-mode","layer","--tensor-split","1,1"]
  spec_args=list(s["args"])
  if lane in ("MTP","MTP_NGRAM") and mc.get("mtp_draft_n_max") is not None:
   i=spec_args.index("--spec-draft-n-max")
   spec_args[i+1]=str(mc["mtp_draft_n_max"])
  if lane in ("MTP","MTP_NGRAM") and mc.get("mtp_companion_required"):
   companion=mc.get("mtp_companion") or {}
   if not companion.get("path"): raise ValueError("MTP companion path is required but not pinned")
   insert_at=cmd.index("--entrypoint")
   cmd[insert_at:insert_at]=["-v",f"{companion['path']}:/model/draft.gguf:ro"]
   spec_args+=["--model-draft","/model/draft.gguf"]
   if mc.get("mtp_draft_device"): spec_args+=["--spec-draft-device",str(mc["mtp_draft_device"])]
  cmd+=["--ctx-size",str(total),"--parallel",str(parallel),"--kv-unified",
        "--kv-unified-per-slot","131072","--batch-size","512","--ubatch-size","128",
        "--cache-type-k",cache,"--cache-type-v",cache,"--flash-attn","on",*spec_args,
        "--jinja","--reasoning","off","--metrics","--slots","--no-warmup"]
  return cmd
 if topology=="tp2-shared":
  total=tops["topologies"]["tp2-shared"][f"C{c}"]["shared_kv_pool_context"]
  commands=[command("0,1",port,c,total,True)]; endpoints=[f"http://127.0.0.1:{port}"]
 else:
  commands=[command("0",port,1,131072,False),command("1",port+1,1,131072,False)]
  endpoints=[f"http://127.0.0.1:{port}",f"http://127.0.0.1:{port+1}"]
 plan={"supported_for_planning":True,"runtime":"llama.cpp",
  "runtime_revision":f"{rt['build']} / {rt['commit']}","model":m["model_id"],"model_identity":mc,
  "weight_quant":mc["weight_quant"],"kv_cache":mc["kv_candidates"][0],"lane":lane,
  "speculative":s["speculative"],"ngram":s["ngram"],"topology":topology,"concurrency":c,
  "context_tokens_per_agent":131072,"commands":commands,"environment":{},"command_environments":[{} for _ in commands],"endpoints":endpoints}
 return attach_gateway(plan,lock,m,endpoints,gateway_port) if topology=="1gpu-x2-independent" else plan

def onecat_plan(lock,m,lane,c,topology,port,gateway_port=18079):
 if topology not in m.get("topology_candidates",[]):return unsupported(m,"1Cat-vLLM",lane,topology,"topology not declared")
 mc=m["onecat_vllm"]
 if lane=="STOCK":
  if mc.get("planning_ready") is False:return unsupported(m,"1Cat-vLLM",lane,topology,"exact artifact is recorded but V100 runtime compatibility is not yet verified")
  if not mc.get("path"):return unsupported(m,"1Cat-vLLM",lane,topology,"exact 1Cat artifact is pending")
  rt=lock["runtimes"]["1Cat-vLLM"];py=os.environ.get("V100_1CAT_PYTHON","V100_1CAT_PYTHON_NOT_SET");kv_candidates=mc.get("kv_candidates") or [mc.get("desired_kv")];kv_value=kv_candidates[0] if kv_candidates else None;weight=mc.get("weight_quant") or mc.get("desired_weight_quant");specs=mc.get("speculative_candidates") or [mc.get("speculative_candidate","target-only")];spec_mode=specs[0];attention_backend=mc.get("attention_backend","FLASH_ATTN_V100")
  if not kv_value:return unsupported(m,"1Cat-vLLM",lane,topology,"KV candidate unresolved")
  spec_args=[];spec_cfg=None
  if spec_mode!="target-only":
   spec_cfg=mc.get("speculative_config")
   if not isinstance(spec_cfg,dict):return unsupported(m,"1Cat-vLLM",lane,topology,"exact speculative launch config is unresolved")
   spec_args=["--speculative-config",json.dumps(spec_cfg,separators=(",",":"))]
  def command(p,tp,max_seqs):
   return [py,"-m","vllm.entrypoints.openai.api_server","--model",mc["path"],"--served-model-name",m["model_id"],"--trust-remote-code","--dtype","half","--attention-backend",attention_backend,"--tensor-parallel-size",str(tp),"--kv-cache-dtype",kv(kv_value),"--max-model-len","131072","--max-num-seqs",str(max_seqs),"--max-num-batched-tokens","2048","--gpu-memory-utilization","0.90","--enforce-eager",*spec_args,"--host","127.0.0.1","--port",str(p)]
  if topology=="tp2-shared":commands=[command(port,2,c)];envs=[{"CUDA_VISIBLE_DEVICES":"0,1"}];endpoints=[f"http://127.0.0.1:{port}"]
  else:
   commands=[command(port,1,1),command(port+1,1,1)];envs=[{"CUDA_VISIBLE_DEVICES":"0"},{"CUDA_VISIBLE_DEVICES":"1"}];endpoints=[f"http://127.0.0.1:{port}",f"http://127.0.0.1:{port+1}"]
  plan={"supported_for_planning":True,"runtime":"1Cat-vLLM","runtime_revision":f"{rt['version']} wheel sha256:{rt['sha256']}","model":m["model_id"],"model_identity":mc,"weight_quant":weight,"kv_cache":kv_value,"lane":lane,"speculative":spec_mode,"speculative_config":spec_cfg,"attention_backend":attention_backend,"ngram":"N/A","topology":topology,"concurrency":c,"context_tokens_per_agent":131072,"commands":commands,"environment":{},"command_environments":envs,"endpoints":endpoints}
  return attach_gateway(plan,lock,m,endpoints,gateway_port) if topology=="1gpu-x2-independent" else plan
 if lane!="SKINNY":raise ValueError("unknown onecat lane")
 if topology!="tp2-shared":return unsupported(m,"1Cat-vLLM+v100-skinny",lane,topology,"v100-skinny v1.1 is pinned only as an experimental TP2 compatibility lane")
 sm=m.get("skinny_v11")
 if not isinstance(sm,dict):return unsupported(m,"1Cat-vLLM+v100-skinny",lane,topology,"standalone v100-skinny v1.1 has no pinned model contract for this candidate")
 return unsupported(m,"1Cat-vLLM+v100-skinny",lane,topology,"WBS 1.4 current-hardware preflight: FAIL_OOM_MODEL_LOAD during QPN _qpn_prepack on 2x V100-16GB before server boot/skinny gate; C1/C2 scheduling disabled")


def build_plan(root,model,lane,c,topology,port=18080,gateway_port=18079):
 lock,lanes,tops,m=state(root,model)
 if lane in LLAMA_KEYS:return llama_plan(lock,lanes,tops,m,lane,c,topology,port,gateway_port)
 if lane in {"STOCK","SKINNY"}:return onecat_plan(lock,m,lane,c,topology,port,gateway_port)
 raise ValueError("unknown lane")

def preflight(plan):
 checks=[]
 def add(n,ok,d=""): checks.append({"name":n,"ok":bool(ok),"detail":d})
 add("supported",plan.get("supported_for_planning") is True,plan.get("reason",""))
 add("host",socket.gethostname().split(".",1)[0]=="p520-llm",socket.gethostname())
 if not plan.get("supported_for_planning"):return {"pass":False,"checks":checks}
 if plan.get("gateway"):
  docker=shutil.which("docker");add("gateway:docker",docker is not None)
  image=plan["gateway"]["image"]
  if docker:
   r=subprocess.run(["docker","image","inspect",image],capture_output=True,text=True);add("gateway:image",r.returncode==0,image)
   if r.returncode==0:
    code="import importlib.metadata as m; print(m.version('litellm'))"
    v=subprocess.run(["docker","run","--rm","--pull=never","--entrypoint","python",image,"-c",code],capture_output=True,text=True,timeout=60)
    add("gateway:litellm_version",v.returncode==0 and v.stdout.strip()==plan["gateway"]["runtime_revision"].split(" / ",1)[0],v.stdout.strip() or v.stderr.strip())
 if plan["runtime"]=="llama.cpp":
  add("docker",shutil.which("docker") is not None)
  path=plan["model_identity"].get("path");add("model_path",bool(path) and Path(path).is_file(),str(path))
  if shutil.which("docker"):
   image=plan["commands"][0][plan["commands"][0].index("--entrypoint")+2]
   r=subprocess.run(["docker","image","inspect",image],capture_output=True,text=True)
   add("image",r.returncode==0,image)
   if r.returncode==0:
    h=subprocess.run(["docker","run","--rm","--pull=never","--gpus","all","--entrypoint","llama-server",image,"--help"],
                     capture_output=True,text=True,timeout=60);txt=h.stdout+h.stderr
    add("help:exit",h.returncode==0,txt[:2000] if h.returncode else "")
    for token in ("--spec-type","--kv-unified","--kv-unified-per-slot","--slots"):add("help:"+token,token in txt)
    if plan["lane"] in ("NGRAM","MTP_NGRAM"):add("help:ngram-simple","ngram-simple" in txt)
    if plan["lane"] in ("MTP","MTP_NGRAM"):
     add("help:draft-mtp","draft-mtp" in txt)
     companion=plan["model_identity"].get("mtp_companion")
     if plan["model_identity"].get("mtp_companion_required"):
      add("help:spec-draft-model","--spec-draft-model" in txt or "--model-draft" in txt)
      add("help:spec-draft-device","--spec-draft-device" in txt)
      path=(companion or {}).get("path")
      add("mtp_companion_path",bool(path) and Path(path).is_file(),str(path))
 else:
  key="V100_SKINNY_PYTHON" if plan["lane"]=="SKINNY" else "V100_1CAT_PYTHON"
  py=os.environ.get(key);add(key,bool(py) and Path(py).is_file(),str(py))
  if py and Path(py).is_file():
   code="import importlib.metadata as m\nfor n in ('1cat-vllm','1cat_vllm'):\n try:\n  print(m.version(n)); break\n except m.PackageNotFoundError: pass\nelse: raise SystemExit(2)"
   r=subprocess.run([py,"-c",code],capture_output=True,text=True,timeout=30)
   version=r.stdout.strip()
   expected="1.2.2" if plan["lane"]=="SKINNY" else "1.5.0"
   add("1cat_version",r.returncode==0 and version==expected,version or r.stderr.strip())
  if plan["lane"]=="STOCK":
   path=plan["model_identity"].get("path");add("model_path",bool(path) and Path(path).is_dir(),str(path))
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

def launch(plan,log_dir=None):
 check=preflight(plan)
 if not check["pass"]:
  print(json.dumps(check,indent=2),file=sys.stderr);raise RuntimeError("preflight failed")
 ps=[];handles=[];envs=plan.get("command_environments") or [plan.get("environment",{}) for _ in plan["commands"]]
 if len(envs)!=len(plan["commands"]):raise ValueError("command_environments length mismatch")
 if plan.get("gateway") and log_dir is None:raise ValueError("LiteLLM topology requires --log-dir so the generated gateway config and logs are preserved")
 if log_dir is not None:log_dir=Path(log_dir).resolve();log_dir.mkdir(parents=True,exist_ok=True)
 try:
  for i,(cmd,extra) in enumerate(zip(plan["commands"],envs)):
   env=os.environ.copy();env.update({k:str(v) for k,v in extra.items()});stdout=None
   if log_dir is not None:
    handle=(log_dir/f"server-{i}.log").open("xb");handles.append(handle);stdout=handle
   ps.append(subprocess.Popen(cmd,env=env,stdout=stdout,stderr=subprocess.STDOUT if stdout is not None else None))
  if plan.get("gateway"):
   config_path=log_dir/"litellm-config.yaml"
   with config_path.open("x",encoding="utf-8") as stream:json.dump(plan["gateway"]["config"],stream,ensure_ascii=False,indent=2);stream.write("\n")
   cmd=[x.replace("{LITELLM_CONFIG}",str(config_path)) for x in plan["gateway"]["command"]]
   handle=(log_dir/"gateway.log").open("xb");handles.append(handle)
   ps.append(subprocess.Popen(cmd,env=os.environ.copy(),stdout=handle,stderr=subprocess.STDOUT))
  while True:
   for p in ps:
    rc=p.poll()
    if rc is not None:
     for q in ps:
      if q.poll() is None:q.terminate()
     return rc
   time.sleep(1)
 except KeyboardInterrupt:
  for p in ps:
   if p.poll() is None:p.terminate()
  return 130
 finally:
  for h in handles:h.close()

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,default=ROOT)
 ap.add_argument("--model",choices=sorted(MODELS),required=True)
 ap.add_argument("--lane",choices=tuple(LLAMA_KEYS)+("STOCK","SKINNY"),required=True)
 ap.add_argument("--concurrency",type=int,choices=(1,2),required=True)
 ap.add_argument("--topology",choices=("tp2-shared","1gpu-x2-independent"),default="tp2-shared")
 ap.add_argument("--port",type=int,default=18080);ap.add_argument("--gateway-port",type=int,default=18079);ap.add_argument("--log-dir",type=Path);g=ap.add_mutually_exclusive_group()
 g.add_argument("--preflight",action="store_true");g.add_argument("--execute",action="store_true");a=ap.parse_args()
 p=build_plan(a.root.resolve(),a.model,a.lane,a.concurrency,a.topology,a.port,a.gateway_port)
 if a.preflight:print(json.dumps({"plan":p,"preflight":preflight(p)},ensure_ascii=False,indent=2));return 0
 if a.execute:return launch(p,a.log_dir)
 print(json.dumps(p,ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
