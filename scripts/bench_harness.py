#!/usr/bin/env python3
"""C1/C2 OpenAI-compatible benchmark harness. It never owns server lifecycle."""
import hashlib,json,os,re,socket,threading,time,urllib.error,urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from measurement_policy import future_config

PASS="PASS"; FAILS=("FAIL_OOM","FAIL_CAPACITY","FAIL_CRASH","FAIL_TIMEOUT","FAIL_OUTPUT","FAIL_STARTUP","UNSUPPORTED","INCONCLUSIVE")
VALID={"PASS","PASS_C1_128K","PASS_C2_RESIDENT","PASS_C2_ACTIVE","QUEUE_ONLY",*FAILS}
def utc(): return datetime.now(timezone.utc).isoformat()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def sha(v): return hashlib.sha256(v).hexdigest()
def save(path,v):
 p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name("."+p.name+".tmp")
 with t.open("wb") as f: f.write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False).encode()+b"\n"); f.flush(); os.fsync(f.fileno())
 os.replace(t,p)

def output_ok(case,res):
 try:
  if len(res["choices"])!=1:return False
  c=res["choices"][0]; m=c["message"]; text=m.get("content") or ""; check=case.get("check","nonempty")
  if "\ufffd" in text or any(ord(x)<32 and x not in "\n\r\t" for x in text):return False
  if c.get("finish_reason") not in (("stop","length") if check=="nonempty" else ("stop",)):return False
  return bool(text.strip()) if check=="nonempty" else text.strip()==case["expected"]
 except (KeyError,IndexError,TypeError): return False

class HTTPAdapter:
 def __init__(self,base_url,runtime,timeout_s=1800): self.base=base_url.rstrip("/"); self.runtime=runtime; self.timeout=timeout_s
 def call(self,route,body=None,raw=False):
  req=urllib.request.Request(self.base+route,data=None if body is None else canon(body),headers={"Content-Type":"application/json"})
  with urllib.request.urlopen(req,timeout=self.timeout) as r:data=r.read(8*1024*1024+1)
  if len(data)>8*1024*1024:raise ValueError("response evidence too large")
  return data.decode() if raw else json.loads(data)
 def health(self):
  try:self.call("/health",raw=True);return {"healthy":True,"at_utc":utc()}
  except Exception as e:return {"healthy":False,"error":str(e),"at_utc":utc()}
 def snapshot(self):
  out={}
  for route in ("/metrics","/props"):
   try:out[route]=self.call(route,raw=True)
   except Exception as e:out[route]={"unavailable":str(e)}
  return out
 def receipt(self,payload):
  if self.runtime=="llama.cpp":
   applied=self.call("/apply-template",payload); toks=self.call("/tokenize",{"content":applied["prompt"],"add_special":True,"parse_special":True})["tokens"]
   return {"source":"llama tokenizer","prompt_tokens":len(toks),"formatted_prompt_sha256":sha(applied["prompt"].encode())}
  body={k:v for k,v in payload.items() if k in ("model","messages","tools","tool_choice","chat_template_kwargs")}
  return {"source":"vllm tokenizer","prompt_tokens":self.call("/tokenize",body|{"add_generation_prompt":True})["count"]}
 def stream_complete(self,payload):
  body=dict(payload,stream=True);body.setdefault("stream_options",{"include_usage":True});req=urllib.request.Request(self.base+"/v1/chat/completions",data=canon(body),headers={"Content-Type":"application/json","Accept":"text/event-stream"})
  start=time.monotonic();first=None;parts=[];usage=None;timings=None;finish=None
  with urllib.request.urlopen(req,timeout=self.timeout) as r:
   for raw in r:
    line=raw.decode("utf-8",errors="replace").strip()
    if not line.startswith("data:"):continue
    text=line[5:].strip()
    if text=="[DONE]":break
    try:chunk=json.loads(text)
    except json.JSONDecodeError:continue
    usage=chunk.get("usage") or usage;timings=chunk.get("timings") or timings
    if chunk.get("choices"):
     choice=chunk["choices"][0];finish=choice.get("finish_reason") or finish;piece=choice.get("delta",{}).get("content")
     if piece:first=first or time.monotonic();parts.append(piece)
  end=time.monotonic();res={"choices":[{"finish_reason":finish or "stop","message":{"content":"".join(parts)}}]}
  if usage:res["usage"]=usage
  if timings:res["timings"]=timings
  return res,{"start":start,"first":first,"end":end,"wall_s":end-start,"ttft_ms":None if first is None else (first-start)*1000}
 def overlap_evidence(self,records): return {"source":"generic adapter: no scheduler proof","resident":None,"active_overlap":None,"queue_only":None}

def classify(e):
 if isinstance(e,(TimeoutError,socket.timeout)):return "FAIL_TIMEOUT"
 if isinstance(e,urllib.error.URLError) and isinstance(e.reason,(TimeoutError,socket.timeout)):return "FAIL_TIMEOUT"
 if isinstance(e,urllib.error.HTTPError):
  body=e.read(8192).decode(errors="replace");e.evidence=body;low=body.lower()
  if "out of memory" in low or "cuda oom" in low:return "FAIL_OOM"
  if any(x in low for x in ("context length","context size","maximum context","kv cache")):return "FAIL_CAPACITY"
 return "INCONCLUSIVE"

def validate(c):
 if not re.fullmatch(r"EXP-V100-[A-Z0-9][A-Z0-9-]*",c["experiment_id"]):raise ValueError("bad experiment_id")
 if c.get("concurrency") not in (1,2):raise ValueError("concurrency must be C1/C2")
 if type(c.get("context_tokens")) is not int or c["context_tokens"]<1:raise ValueError("bad context_tokens")
 for k in ("model","runtime","runtime_revision","model_identity","launch_command","weight_quant","kv_cache","speculative","ngram","topology","prefix_cache_lane","chat_template","tool_parser","thinking"):
  if k not in c:raise ValueError("missing identity: "+k)

def cases(workload,n):
 selected=workload.get("requests",[])[:n]
 if len(selected)!=n:raise ValueError("workload lacks requests")
 hashes=[sha(canon(x["messages"])) for x in selected]
 if n==2 and len(set(hashes))!=2:raise ValueError("C2 requires independent prompt hashes")
 return selected,hashes

def body(config,workload,case):
 out={"model":config.get("served_model",config["model"]),"messages":case["messages"],"max_tokens":case["max_tokens"],"stream":True,**workload.get("sampling",{})}
 out["chat_template_kwargs"]={"enable_thinking":config["thinking"]}
 for k in ("tools","tool_choice"):
  if k in case:out[k]=case[k]
 return out

def receipt_ok(config,case,r):
 n=r.get("prompt_tokens");used=(n if type(n) is int else -1)+case["max_tokens"]
 if type(n) is not int or n<1 or used>config["context_tokens"]:raise ValueError("invalid/excess context receipt")
 if config.get("context_test",True) and used<int(config["context_tokens"]*config.get("min_context_utilization",.95)):raise ValueError("underfilled context")

def worker(adapter,barrier,origin,rec,payload,case,receipt):
 try:
  barrier.wait(timeout=30);rec.update(status="running",submitted_s=time.monotonic()-origin)
  res,t=adapter.stream_complete(payload);rec["response"]=res;u=res.get("usage") or {};rec["actual_output_tokens"]=u.get("completion_tokens");rec["post_template_prompt_tokens"]=u.get("prompt_tokens")
  prompt_ok=rec["post_template_prompt_tokens"]==receipt["prompt_tokens"];tokens_ok=type(rec["actual_output_tokens"]) is int and 0<rec["actual_output_tokens"]<=case["max_tokens"]
  rec["verdict"]="FAIL_OUTPUT" if not output_ok(case,res) else PASS if prompt_ok and tokens_ok else "INCONCLUSIVE"
  first=t.get("first",t.get("first_token_s"));end=t.get("end",t.get("terminal_s"));rec["ttft_ms"]=t.get("ttft_ms");rec["first_abs"]=first;rec["end_abs"]=end;rec["wall_s"]=t.get("wall_s");tim=res.get("timings") or {};rec["prefill_tps"]=tim.get("prompt_per_second");rec["decode_tps"]=tim.get("predicted_per_second")
  if rec["decode_tps"] is None and first and end and end>first and tokens_ok:rec["decode_tps"]=rec["actual_output_tokens"]/(end-first)
 except Exception as e:rec.update(verdict=classify(e),error=str(e),error_body=getattr(e,"evidence",None))
 rec["status"]="results_saved";rec["terminal_s"]=time.monotonic()-origin;return rec

def summarize(config,records,evidence):
 ok=[r for r in records if r.get("verdict")==PASS];submitted=[r["submitted_s"] for r in records if "submitted_s" in r];terminal=[r["terminal_s"] for r in records if "terminal_s" in r];first=[r["first_abs"] for r in ok if r.get("first_abs")];ends=[r["end_abs"] for r in ok if r.get("end_abs")];tokens=sum(r.get("actual_output_tokens") or 0 for r in ok);batch=max(terminal)-min(submitted) if submitted and terminal else None;window=max(ends)-min(first) if first and ends else None;dec=[r["decode_tps"] for r in ok if r.get("decode_tps") is not None];ttft=[r["ttft_ms"] for r in ok if r.get("ttft_ms") is not None];pref=[r["prefill_tps"] for r in ok if r.get("prefill_tps") is not None]
 return {"context_tokens":config["context_tokens"],"concurrency":config["concurrency"],"intended_requests":config["concurrency"],"completed_requests":len(ok),"batch_wall_s":batch,"submission_skew_s":max(submitted)-min(submitted) if len(submitted)>1 else 0.0,"ttft_ms":sum(ttft)/len(ttft) if ttft else None,"prefill_tps":sum(pref)/len(pref) if pref else None,"mean_request_decode_tps":sum(dec)/len(dec) if dec else None,"aggregate_decode_tps":tokens/window if window and window>0 else None,"end_to_end_output_tps":tokens/batch if batch and batch>0 else None,"server_overlap":evidence,"c1_128k":config["concurrency"]==1 and config["context_tokens"]==131072,"c2_resident":evidence.get("resident"),"c2_active":evidence.get("active_overlap"),"queue_only":evidence.get("queue_only")}

def run_batch(output,config,workload,adapter):
 config=future_config(config);validate(config)
 if config["measured_repetitions"]!=1:raise ValueError("one measured batch only")
 selected,hashes=cases(workload,config["concurrency"]);payloads=[body(config,workload,x) for x in selected];output=Path(output);output.mkdir(parents=True,exist_ok=False);frozen=dict(config,workload_sha256=sha(canon(workload)))
 save(output/"config.json",frozen);save(output/"identity.json",{"config_sha256":sha(canon(frozen)),"created_at_utc":utc()});save(output/"workload.json",workload);save(output/"payloads.json",payloads)
 before=adapter.health();save(output/"health-before.json",before);save(output/"server-before.json",adapter.snapshot());receipts=[];errors=[]
 for case,payload in zip(selected,payloads):
  try:
   if not before.get("healthy"):raise RuntimeError("server unhealthy")
   r=adapter.receipt(payload);receipt_ok(config,case,r);receipts.append(r);errors.append(None)
  except Exception as e:receipts.append(None);errors.append(str(e))
 save(output/"tokenization.json",{"items":[{"request_id":c["id"],"receipt":r,"error":e} for c,r,e in zip(selected,receipts,errors)]});records=[{"request_id":c["id"],"project_id":c.get("project_id",c["id"]),"status":"prepared","verdict":None,"raw_prompt_sha256":h,"requested_output_tokens":c["max_tokens"]} for c,h in zip(selected,hashes)];save(output/"requests.json",records)
 if any(errors):
  for r,e in zip(records,errors):r.update(status="not_submitted",verdict="FAIL_STARTUP" if not before.get("healthy") else "FAIL_CAPACITY",error=e)
 else:
  barrier=threading.Barrier(config["concurrency"]);origin=time.monotonic()
  with ThreadPoolExecutor(max_workers=config["concurrency"]) as pool:records=[f.result() for f in [pool.submit(worker,adapter,barrier,origin,r,p,c,rc) for r,p,c,rc in zip(records,payloads,selected,receipts)]]
 save(output/"requests.json",records);after=adapter.health();save(output/"health-after.json",after);save(output/"server-after.json",adapter.snapshot())
 try:evidence=adapter.overlap_evidence(records)
 except Exception as e:evidence={"source":"overlap probe failed","resident":None,"active_overlap":None,"queue_only":None,"error":str(e)}
 for k in ("resident","active_overlap","queue_only"):evidence.setdefault(k,None)
 save(output/"overlap-evidence.json",evidence);values={r.get("verdict") for r in records};failure=None if values=={PASS} else next((x for x in FAILS if x in values),"INCONCLUSIVE")
 if not after.get("healthy") and before.get("healthy"):verdict="FAIL_CRASH"
 elif failure:verdict=failure
 elif config["concurrency"]==1:verdict="PASS_C1_128K" if config["context_tokens"]==131072 else "PASS"
 elif evidence.get("active_overlap") is True:verdict="PASS_C2_ACTIVE"
 elif evidence.get("queue_only") is True:verdict="QUEUE_ONLY"
 elif evidence.get("resident") is True:verdict="PASS_C2_RESIDENT"
 else:verdict="INCONCLUSIVE"
 if verdict not in VALID:raise AssertionError(verdict)
 m=summarize(config,records,evidence);m["verdict"]=verdict;save(output/"metrics.json",m);save(output/"completion.json",{"experiment_id":config["experiment_id"],"verdict":verdict,"completed_at_utc":utc(),"post_health":after});return verdict

def inspect_run(output):
 p=Path(output);c=json.loads((p/"config.json").read_text());i=json.loads((p/"identity.json").read_text())
 if sha(canon(c))!=i["config_sha256"]:raise ValueError("config identity mismatch")
 return {"config_valid":True,"completion":json.loads((p/"completion.json").read_text()) if (p/"completion.json").exists() else None}
