#!/usr/bin/env python3
"""C1/C2 OpenAI-compatible benchmark harness. It never owns server lifecycle."""
import hashlib,json,os,re,shutil,socket,subprocess,threading,time,urllib.error,urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
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

def detect_repetition(text,finish_reason=None):
 if not text or not text.strip():return False
 words=text.split()
 if len(words)<20:
  return len(set(words))<=2 and len(words)>=6
 lines=[l.strip() for l in text.splitlines() if len(l.strip())>=25]
 if lines:
  from collections import Counter
  most_common_line,count=Counter(lines).most_common(1)[0]
  if count>=3 and (len(most_common_line)*count)/max(1,len(text))>0.35:return True
 if len(words)>=60:
  n=8; ngrams=[tuple(words[i:i+n]) for i in range(len(words)-n+1)]
  if len(set(ngrams))/len(ngrams)<0.40:return True
 if finish_reason=="length" and len(words)>=100:
  tail=words[-60:]; n=6; tail_ngrams=[tuple(tail[i:i+n]) for i in range(len(tail)-n+1)]
  if len(set(tail_ngrams))/len(tail_ngrams)<0.35:return True
 max_k=min(64,len(words)//3)
 for k in range(4,max_k+1):
  for i in range(len(words)-3*k+1):
   if words[i:i+k]==words[i+k:i+2*k]==words[i+2*k:i+3*k]:
    repeat_count=3; pos=i+3*k
    while pos+k<=len(words) and words[pos:pos+k]==words[i:i+k]:
     repeat_count+=1; pos+=k
    if repeat_count*k>=30 or repeat_count>=5:return True
 return False

def output_ok(case,res):
 try:
  if len(res["choices"])!=1:return False
  c=res["choices"][0]; m=c["message"]; text=m.get("content") or ""; check=case.get("check","nonempty")
  if "\ufffd" in text or any(ord(x)<32 and x not in "\n\r\t" for x in text):return False
  finish_reason=c.get("finish_reason")
  if finish_reason not in (("stop","length") if check=="nonempty" else ("stop",)):return False
  if check=="nonempty":
   if not text.strip():return False
   if detect_repetition(text,finish_reason):return False
   return True
  return text.strip()==case["expected"]
 except (KeyError,IndexError,TypeError): return False

def metric_value(text,name):
 vals=[]
 for raw in text.splitlines():
  line=raw.strip()
  if not (line.startswith(name+" ") or line.startswith(name+"{")):continue
  try:vals.append(float(line.rsplit(None,1)[1]))
  except (ValueError,IndexError):pass
 return max(vals) if vals else None

def resident_slots(slots):
 if not isinstance(slots,list):return None
 count=0; witnessed=False
 for slot in slots:
  if not isinstance(slot,dict):continue
  vals=[]
  for key in ("n_past","n_prompt_tokens_processed","n_tokens","n_decoded"):
   value=slot.get(key)
   if isinstance(value,(int,float)):vals.append(value);witnessed=True
  if vals and max(vals)>0:count+=1
 return count if witnessed else None

def runtime_completed(records):
 return [r for r in records if isinstance(r.get("first_abs"),(int,float)) and isinstance(r.get("end_abs"),(int,float)) and r["end_abs"]>=r["first_abs"]]

class HTTPAdapter:
 def __init__(self,base_url,runtime,timeout_s=1800):
  self.base=base_url.rstrip("/");self.runtime=runtime;self.timeout=timeout_s;self._probe_samples=[];self._probe_stop=None;self._probe_thread=None
 def request_adapter(self,index):return self
 def call(self,route,body=None,raw=False):
  req=urllib.request.Request(self.base+route,data=None if body is None else canon(body),headers={"Content-Type":"application/json"})
  with urllib.request.urlopen(req,timeout=self.timeout) as r:data=r.read(8*1024*1024+1)
  if len(data)>8*1024*1024:raise ValueError("response evidence too large")
  return data.decode() if raw else json.loads(data)
 def health(self):
  try:self.call("/health",raw=True);return {"healthy":True,"at_utc":utc()}
  except Exception as e:return {"healthy":False,"error":str(e),"at_utc":utc()}
 def liveness(self):
  try:self.call("/health/liveliness",raw=True);return {"healthy":True,"at_utc":utc(),"route":"/health/liveliness"}
  except Exception as e:return {"healthy":False,"error":str(e),"at_utc":utc(),"route":"/health/liveliness"}
 def snapshot(self):
  out={};routes=["/metrics","/props"]+(["/slots"] if self.runtime=="llama.cpp" else [])
  for route in routes:
   try:out[route]=self.call(route,raw=route!="/slots")
   except Exception as e:out[route]={"unavailable":str(e)}
  return out
 def receipt(self,payload):
  if self.runtime=="llama.cpp":
   applied=self.call("/apply-template",payload);toks=self.call("/tokenize",{"content":applied["prompt"],"add_special":True,"parse_special":True})["tokens"]
   return {"source":"llama tokenizer","prompt_tokens":len(toks),"formatted_prompt_sha256":sha(applied["prompt"].encode())}
  body={k:v for k,v in payload.items() if k in ("model","messages","tools","tool_choice","chat_template_kwargs")}
  return {"source":"vllm tokenizer","prompt_tokens":self.call("/tokenize",body|{"add_generation_prompt":True})["count"]}
 def stream_complete(self,payload):
  body=dict(payload,stream=True);body.setdefault("stream_options",{"include_usage":True});req=urllib.request.Request(self.base+"/v1/chat/completions",data=canon(body),headers={"Content-Type":"application/json","Accept":"text/event-stream"})
  start=time.monotonic();first=None;parts=[];usage=None;timings=None;finish=None;response_headers={}
  with urllib.request.urlopen(req,timeout=self.timeout) as r:
   hdr=getattr(r,"headers",{})
   for key in ("x-litellm-model-id","x-litellm-model-api-base","x-litellm-call-id","x-litellm-version"):
    value=hdr.get(key) if hasattr(hdr,"get") else None
    if value:response_headers[key]=value
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
  return res,{"start":start,"first":first,"end":end,"wall_s":end-start,"ttft_ms":None if first is None else (first-start)*1000,"response_headers":response_headers}
 def _probe_once(self):
  sample={"monotonic_s":time.monotonic(),"processing":None,"waiting":None,"resident_slots":None,"kv_usage":None,"error":None}
  try:
   metrics=self.call("/metrics",raw=True)
   if self.runtime=="llama.cpp":
    sample["processing"]=metric_value(metrics,"llamacpp:requests_processing");sample["waiting"]=metric_value(metrics,"llamacpp:requests_deferred")
    try:
     slots=self.call("/slots")
     if isinstance(slots,list):
      active=sum(1 for slot in slots if isinstance(slot,dict) and slot.get("is_processing"))
      sample["processing"]=max(sample["processing"] or 0,active);sample["resident_slots"]=resident_slots(slots)
    except Exception:pass
   else:
    sample["processing"]=metric_value(metrics,"vllm:num_requests_running");sample["waiting"]=metric_value(metrics,"vllm:num_requests_waiting");sample["kv_usage"]=metric_value(metrics,"vllm:kv_cache_usage_perc")
  except Exception as e:sample["error"]=str(e)
  return sample
 def start_overlap_probe(self,expected_concurrency=2,interval_s=.1):
  self._probe_samples=[];self._probe_stop=threading.Event()
  def loop():
   while not self._probe_stop.is_set():
    self._probe_samples.append(self._probe_once());self._probe_stop.wait(interval_s)
  self._probe_thread=threading.Thread(target=loop,daemon=True);self._probe_thread.start()
 def stop_overlap_probe(self):
  if self._probe_stop is not None:self._probe_stop.set()
  if self._probe_thread is not None:self._probe_thread.join(timeout=2)
 def probe_summary(self,start=None,end=None):
  samples=list(self._probe_samples)
  if start is not None and end is not None:samples=[x for x in samples if start<=x.get("monotonic_s",-1)<=end]
  processing=[x["processing"] for x in samples if isinstance(x.get("processing"),(int,float))]
  waiting=[x["waiting"] for x in samples if isinstance(x.get("waiting"),(int,float))]
  resident=[x["resident_slots"] for x in samples if isinstance(x.get("resident_slots"),(int,float))]
  return {"peak_processing":max(processing) if processing else None,"peak_waiting":max(waiting) if waiting else None,"peak_resident_slots":max(resident) if resident else None,"sample_count":len(samples),"samples":samples}
 def overlap_evidence(self,records):
  samples=list(self._probe_samples);processing=[x["processing"] for x in samples if isinstance(x.get("processing"),(int,float))];waiting=[x["waiting"] for x in samples if isinstance(x.get("waiting"),(int,float))];resident=[x["resident_slots"] for x in samples if isinstance(x.get("resident_slots"),(int,float))]
  peak_processing=max(processing) if processing else None;peak_waiting=max(waiting) if waiting else None;peak_resident=max(resident) if resident else None
  completed=runtime_completed(records);decode_start=decode_end=None
  if len(completed)==2:decode_start=max(r["first_abs"] for r in completed);decode_end=min(r["end_abs"] for r in completed)
  active=None
  if decode_start is not None and decode_end is not None and decode_start<decode_end:
   window=[x for x in samples if decode_start<=x["monotonic_s"]<=decode_end]
   if any((x.get("processing") or 0)>=2 for x in window):active=True
  queued=bool(peak_waiting is not None and peak_waiting>=1 and (peak_processing or 0)<=1)
  if active is None and queued:active=False
  resident_ok=True if (peak_processing or 0)>=2 or (peak_resident or 0)>=2 else (False if queued else None)
  return {"source":f"{self.runtime} server metrics/slots sampler","resident":resident_ok,"active_overlap":active,"queue_only":queued,"peak_processing":peak_processing,"peak_waiting":peak_waiting,"peak_resident_slots":peak_resident,"sample_count":len(samples),"samples":samples}

class MultiEndpointAdapter:
 def __init__(self,adapters):
  if len(adapters)<2:raise ValueError("MultiEndpointAdapter requires at least two endpoints")
  self.adapters=list(adapters)
 def request_adapter(self,index):return self.adapters[index]
 def health(self):
  children=[a.health() for a in self.adapters];return {"healthy":all(x.get("healthy") for x in children),"children":children,"at_utc":utc()}
 def snapshot(self):return {f"endpoint_{i}":a.snapshot() for i,a in enumerate(self.adapters)}
 def start_overlap_probe(self,expected_concurrency=2,interval_s=.1):
  for a in self.adapters:
   if hasattr(a,"start_overlap_probe"):a.start_overlap_probe(1,interval_s)
 def stop_overlap_probe(self):
  for a in self.adapters:
   if hasattr(a,"stop_overlap_probe"):a.stop_overlap_probe()
 def overlap_evidence(self,records):
  children=[]
  for a in self.adapters:
   try:children.append(a.overlap_evidence([]))
   except Exception as e:children.append({"source":"child probe failed","error":str(e)})
  completed=runtime_completed(records);active=None
  if len(completed)==2:active=max(r["first_abs"] for r in completed)<min(r["end_abs"] for r in completed)
  return {"source":"independent endpoints: per-request routing plus overlapping decode lifetimes","resident":True if active else None,"active_overlap":active,"queue_only":False if active else None,"children":children}

class LiteLLMGatewayAdapter:
 def __init__(self,gateway,backends):
  if len(backends)!=2:raise ValueError("LiteLLMGatewayAdapter requires exactly two backends")
  self.gateway=gateway;self.backends=list(backends)
 def request_adapter(self,index):return self
 def health(self):
  gateway=self.gateway.liveness() if hasattr(self.gateway,"liveness") else self.gateway.health();children=[a.health() for a in self.backends]
  return {"healthy":bool(gateway.get("healthy")) and all(x.get("healthy") for x in children),"gateway":gateway,"backends":children,"at_utc":utc()}
 def snapshot(self):
  gateway=self.gateway.liveness() if hasattr(self.gateway,"liveness") else self.gateway.health()
  return {"gateway":{"liveness":gateway},"backends":{f"backend_{i}":a.snapshot() for i,a in enumerate(self.backends)}}
 def receipt(self,payload):
  return self.backends[0].receipt(payload)
 def stream_complete(self,payload):
  clean=dict(payload);template_kwargs=clean.pop("chat_template_kwargs",None)
  if template_kwargs is not None:
   extra=dict(clean.get("extra_body") or {});extra["chat_template_kwargs"]=template_kwargs;clean["extra_body"]=extra
  return self.gateway.stream_complete(clean)
 def start_overlap_probe(self,expected_concurrency=2,interval_s=.1):
  for a in self.backends:a.start_overlap_probe(1,interval_s)
 def stop_overlap_probe(self):
  for a in self.backends:a.stop_overlap_probe()
 def overlap_evidence(self,records):
  completed=runtime_completed(records);decode_start=decode_end=None
  if len(completed)==2:
   decode_start=max(r["first_abs"] for r in completed);decode_end=min(r["end_abs"] for r in completed)
  decode_overlap=bool(decode_start is not None and decode_end is not None and decode_start<decode_end)
  children=[a.probe_summary(decode_start,decode_end) if decode_overlap else a.probe_summary() for a in self.backends]
  backend_active=decode_overlap and all((x.get("peak_processing") or 0)>=1 for x in children)
  ids=[r.get("gateway_deployment_id") for r in completed if r.get("gateway_deployment_id")]
  bases=[r.get("gateway_api_base") for r in completed if r.get("gateway_api_base")]
  distinct_ids=(len(ids)==2 and len(set(ids))==2) if len(completed)==2 else None
  distinct_bases=(len(bases)==2 and len(set(bases))==2) if len(completed)==2 else None
  route_proven=distinct_bases is True or distinct_ids is True
  active=True if decode_overlap and (backend_active or route_proven) else (False if len(completed)==2 and not decode_overlap else None)
  resident=True if active is True else None
  queue_only=True if len(completed)==2 and active is False else (False if active is True else None)
  return {"source":"LiteLLM single gateway endpoint + backend runtime probes + deployment response headers","resident":resident,"active_overlap":active,"queue_only":queue_only,"gateway_distinct_deployment_ids":distinct_ids,"gateway_distinct_api_bases":distinct_bases,"gateway_deployment_ids":ids,"gateway_api_bases":bases,"backend_active_in_common_decode_window":backend_active,"children":children}
 def routing_preflight(self,model_name,timeout_s=60):
  payload={"model":model_name,"messages":[{"role":"user","content":"routing preflight ping"}],"max_tokens":16,"stream":True}
  barrier=RoutingSettledAdmissionBarrier(self.backends,timeout_s=timeout_s)
  def call_worker():
   barrier.wait(timeout=30)
   return self.stream_complete(payload)
  with ThreadPoolExecutor(max_workers=2) as pool:
   f0=pool.submit(call_worker)
   f1=pool.submit(call_worker)
   barrier.verify_dual_active(timeout=timeout_s)
   res0,t0=f0.result(timeout=timeout_s)
   res1,t1=f1.result(timeout=timeout_s)
  b0=t0.get("response_headers",{}).get("x-litellm-model-api-base")
  b1=t1.get("response_headers",{}).get("x-litellm-model-api-base")
  id0=t0.get("response_headers",{}).get("x-litellm-model-id")
  id1=t1.get("response_headers",{}).get("x-litellm-model-id")
  distinct_bases=bool(b0 and b1 and b0!=b1)
  distinct_ids=bool(id0 and id1 and id0!=id1)
  if not (distinct_bases or distinct_ids):
   raise RuntimeError(f"Dual-backend routing preflight failed: distinct bases/ids required (got bases: {b0}, {b1})")
  return {"pass":True,"distinct_bases":distinct_bases,"distinct_ids":distinct_ids,"bases":[b0,b1],"deployment_ids":[id0,id1],"at_utc":utc()}

class RoutingSettledAdmissionBarrier:
 def __init__(self,backends,timeout_s=60):
  self.backends=backends;self.timeout_s=timeout_s;self._lock=threading.Lock();self._idx=0
  self._first_active=threading.Event();self.both_active=threading.Event()
 def wait(self,timeout=30):
  with self._lock:
   idx=self._idx;self._idx+=1
  if idx==0:return
  deadline=time.monotonic()+(timeout or self.timeout_s)
  while time.monotonic()<deadline:
   for b in self.backends:
    sample=b._probe_once() if hasattr(b,"_probe_once") else {"processing":1}
    if (sample.get("processing") or 0)>=1:
     self._first_active.set();break
   if self._first_active.is_set():break
   time.sleep(.05)
  if not self._first_active.is_set():
   raise TimeoutError("Routing-settled admission timed out: first request was not observed processing on any backend")
 def verify_dual_active(self,timeout=60):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   p0=((self.backends[0]._probe_once().get("processing") or 0)>=1) if hasattr(self.backends[0],"_probe_once") else True
   p1=((self.backends[1]._probe_once().get("processing") or 0)>=1) if hasattr(self.backends[1],"_probe_once") else True
   if p0 and p1:
    self.both_active.set();return True
   time.sleep(.1)
  raise RuntimeError("Dual-backend routing admission verification failed: both backends did not reach processing >= 1 concurrently")

def make_adapter(endpoints,runtime,timeout_s=1800,gateway_endpoint=None):
 adapters=[HTTPAdapter(x,runtime,timeout_s) for x in endpoints]
 if gateway_endpoint is not None:return LiteLLMGatewayAdapter(HTTPAdapter(gateway_endpoint,"litellm",timeout_s),adapters)
 return adapters[0] if len(adapters)==1 else MultiEndpointAdapter(adapters)

def make_plan_adapter(plan,timeout_s=1800):
 if plan.get("gateway"):return make_adapter(plan["backend_endpoints"],plan["runtime"],timeout_s,plan["gateway"]["endpoint"])
 return make_adapter(plan["endpoints"],plan["runtime"],timeout_s)

class GPUPeakProbe:
 def __init__(self,interval_s=.5):
  self.interval_s=interval_s;self.stop_event=threading.Event();self.thread=None;self.peaks={};self.samples=0;self.error=None;self.available=shutil.which("nvidia-smi") is not None
 def start(self):
  if not self.available:return
  def loop():
   while not self.stop_event.is_set():
    try:
     r=subprocess.run(["nvidia-smi","--query-gpu=index,memory.used","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=2,check=True)
     for line in r.stdout.splitlines():
      i,u=[x.strip() for x in line.split(",",1)];i=int(i);u=float(u);self.peaks[i]=max(self.peaks.get(i,0),u)
     self.samples+=1
    except Exception as e:self.error=str(e)
    self.stop_event.wait(self.interval_s)
  self.thread=threading.Thread(target=loop,daemon=True);self.thread.start()
 def stop(self):
  self.stop_event.set()
  if self.thread is not None:self.thread.join(timeout=2)
 def summary(self):return {"source":"nvidia-smi sampled during measured request window","interval_s":self.interval_s,"samples":self.samples,"peak_memory_mib":self.peaks,"error":self.error,"limitation":"sampled peaks may miss between-sample transients"}


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
 if c.get("topology")=="1gpu-x2-independent":
  g=c.get("gateway")
  if not isinstance(g,dict) or g.get("runtime")!="LiteLLM":raise ValueError("1gpu-x2-independent requires LiteLLM gateway identity")
  for k in ("runtime_revision","image","endpoint","routing_strategy","backend_max_parallel_requests"):
   if k not in g:raise ValueError("missing gateway identity: "+k)

def cases(workload,n):
 selected=workload.get("requests",[])[:n]
 if len(selected)!=n:raise ValueError("workload lacks requests")
 hashes=[sha(canon(x["messages"])) for x in selected]
 if n==2 and len(set(hashes))!=2:raise ValueError("C2 requires independent prompt hashes")
 return selected,hashes

def body(config,workload,case):
 out={"model":config.get("served_model",config["model"]),"messages":case["messages"],"max_tokens":case["max_tokens"],"stream":True,**workload.get("sampling",{})}
 if config.get("sampling"):
  out.update(config["sampling"])
 kwargs={"enable_thinking":config["thinking"]}
 if "reasoning_effort" in config and config["reasoning_effort"] is not None:
  kwargs["reasoning_effort"]=config["reasoning_effort"]
 if config.get("chat_template_kwargs"):
  kwargs.update(config["chat_template_kwargs"])
 out["chat_template_kwargs"]=kwargs
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
  prompt_ok=rec["post_template_prompt_tokens"]==receipt["prompt_tokens"];minimum=case.get("min_output_tokens",1);tokens_ok=type(rec["actual_output_tokens"]) is int and minimum<=rec["actual_output_tokens"]<=case["max_tokens"]
  if not output_ok(case,res) or not tokens_ok:rec["verdict"]="FAIL_OUTPUT"
  elif not prompt_ok:rec["verdict"]="INCONCLUSIVE"
  else:rec["verdict"]=PASS
  first=t.get("first",t.get("first_token_s"));end=t.get("end",t.get("terminal_s"));rec["ttft_ms"]=t.get("ttft_ms");rec["first_abs"]=first;rec["end_abs"]=end;rec["wall_s"]=t.get("wall_s");tim=res.get("timings") or {};rec["prefill_tps"]=tim.get("prompt_per_second");rec["decode_tps"]=tim.get("predicted_per_second")
  hdr=t.get("response_headers") or {};rec["gateway_deployment_id"]=hdr.get("x-litellm-model-id");rec["gateway_api_base"]=hdr.get("x-litellm-model-api-base");rec["gateway_call_id"]=hdr.get("x-litellm-call-id");rec["gateway_version"]=hdr.get("x-litellm-version")
  if rec["decode_tps"] is None and first and end and end>first and tokens_ok:rec["decode_tps"]=rec["actual_output_tokens"]/(end-first)
 except Exception as e:rec.update(verdict=classify(e),error=str(e),error_body=getattr(e,"evidence",None))
 rec["status"]="results_saved";rec["terminal_s"]=time.monotonic()-origin;return rec


def summarize(config,records,evidence,verdict,gpu_summary):
 completed=runtime_completed(records);ok=[r for r in records if r.get("verdict")==PASS];submitted=[r["submitted_s"] for r in records if "submitted_s" in r];terminal=[r["terminal_s"] for r in records if "terminal_s" in r];first=[r["first_abs"] for r in completed];ends=[r["end_abs"] for r in completed];tokens=sum(r.get("actual_output_tokens") or 0 for r in completed);batch=max(terminal)-min(submitted) if submitted and terminal else None;window=max(ends)-min(first) if first and ends else None;dec=[r["decode_tps"] for r in completed if r.get("decode_tps") is not None];ttft=[r["ttft_ms"] for r in completed if r.get("ttft_ms") is not None];pref=[r["prefill_tps"] for r in completed if r.get("prefill_tps") is not None];peaks=gpu_summary.get("peak_memory_mib",{})
 return {"context_tokens":config["context_tokens"],"concurrency":config["concurrency"],"intended_requests":config["concurrency"],"completed_requests":len(completed),"output_passed_requests":len(ok),"batch_wall_s":batch,"submission_skew_s":max(submitted)-min(submitted) if len(submitted)>1 else 0.0,"ttft_ms":sum(ttft)/len(ttft) if ttft else None,"prefill_tps":sum(pref)/len(pref) if pref else None,"mean_request_decode_tps":sum(dec)/len(dec) if dec else None,"aggregate_decode_tps":tokens/window if window and window>0 else None,"end_to_end_output_tps":tokens/batch if batch and batch>0 else None,"server_overlap":evidence,"c1_128k":verdict=="PASS_C1_128K","c2_resident":evidence.get("resident"),"c2_active":evidence.get("active_overlap"),"queue_only":evidence.get("queue_only"),"peak_vram_gpu0_mib":peaks.get(0),"peak_vram_gpu1_mib":peaks.get(1),"gpu_peak_probe":gpu_summary}


def run_batch(output,config,workload,adapter):
 config=future_config(config);validate(config)
 if config["topology"]=="1gpu-x2-independent" and not isinstance(adapter,LiteLLMGatewayAdapter):raise ValueError("1gpu-x2-independent acceptance requires LiteLLM single-gateway adapter")
 if config["measured_repetitions"]!=1:raise ValueError("one measured batch only")
 selected,hashes=cases(workload,config["concurrency"]);payloads=[body(config,workload,x) for x in selected];output=Path(output);output.mkdir(parents=True,exist_ok=True)
 unexpected=[x for x in output.iterdir() if x.name!="runtime"]
 if unexpected:raise FileExistsError(f"raw experiment directory is not fresh: {unexpected[0]}")
 frozen=dict(config,workload_sha256=sha(canon(workload)));save(output/"config.json",frozen);save(output/"identity.json",{"config_sha256":sha(canon(frozen)),"created_at_utc":utc()});save(output/"workload.json",workload);save(output/"payloads.json",payloads)
 before=adapter.health();save(output/"health-before.json",before);save(output/"server-before.json",adapter.snapshot());receipts=[];errors=[];request_adapters=[adapter.request_adapter(i) if hasattr(adapter,"request_adapter") else adapter for i in range(config["concurrency"])]
 for case,payload,request_adapter in zip(selected,payloads,request_adapters):
  try:
   if not before.get("healthy"):raise RuntimeError("server unhealthy")
   r=request_adapter.receipt(payload);receipt_ok(config,case,r);receipts.append(r);errors.append(None)
  except Exception as e:receipts.append(None);errors.append(str(e))
 save(output/"tokenization.json",{"items":[{"request_id":c["id"],"receipt":r,"error":e} for c,r,e in zip(selected,receipts,errors)]});records=[{"request_id":c["id"],"project_id":c.get("project_id",c["id"]),"status":"prepared","verdict":None,"raw_prompt_sha256":h,"requested_output_tokens":c["max_tokens"],"minimum_output_tokens":c.get("min_output_tokens",1)} for c,h in zip(selected,hashes)];save(output/"requests.json",records)
 gpu=GPUPeakProbe()
 if any(errors):
  for r,e in zip(records,errors):r.update(status="not_submitted",verdict="FAIL_STARTUP" if not before.get("healthy") else "FAIL_CAPACITY",error=e)
 else:
  if config.get("topology")=="1gpu-x2-independent" and config.get("concurrency")==2 and isinstance(adapter,LiteLLMGatewayAdapter):
   barrier=RoutingSettledAdmissionBarrier(adapter.backends,timeout_s=60)
  else:
   barrier=threading.Barrier(config["concurrency"])
  origin=time.monotonic()
  try:
   if config["concurrency"]==2 and hasattr(adapter,"start_overlap_probe"):adapter.start_overlap_probe(2)
   gpu.start()
   with ThreadPoolExecutor(max_workers=config["concurrency"]) as pool:
    # Workers own their copies; only this collector mutates/persists the ordered snapshot.
    pending={pool.submit(worker,ra,barrier,origin,dict(r),p,c,rc):i for i,(ra,r,p,c,rc) in enumerate(zip(request_adapters,records,payloads,selected,receipts))}
    if isinstance(barrier,RoutingSettledAdmissionBarrier):
     barrier.verify_dual_active(timeout=60)
    for finished in as_completed(pending):
     records[pending[finished]]=finished.result()
     save(output/"requests.json",records)
  finally:
   gpu.stop()
   if config["concurrency"]==2 and hasattr(adapter,"stop_overlap_probe"):adapter.stop_overlap_probe()
 gpu_summary=gpu.summary();save(output/"gpu-peak.json",gpu_summary);save(output/"requests.json",records);after=adapter.health();save(output/"health-after.json",after);save(output/"server-after.json",adapter.snapshot())
 try:evidence=adapter.overlap_evidence(records)
 except Exception as e:evidence={"source":"overlap probe failed","resident":None,"active_overlap":None,"queue_only":None,"error":str(e)}
 for k in ("resident","active_overlap","queue_only"):evidence.setdefault(k,None)
 save(output/"overlap-evidence.json",evidence);values={r.get("verdict") for r in records};failure=None if values=={PASS} else next((x for x in FAILS if x in values),"INCONCLUSIVE")
 concurrency_verdict=None
 if config["concurrency"]==2:
  if evidence.get("active_overlap") is True:concurrency_verdict="PASS_C2_ACTIVE"
  elif evidence.get("queue_only") is True:concurrency_verdict="QUEUE_ONLY"
  elif evidence.get("resident") is True:concurrency_verdict="PASS_C2_RESIDENT"
  else:concurrency_verdict="INCONCLUSIVE"
 if not after.get("healthy") and before.get("healthy"):verdict="FAIL_CRASH"
 elif failure:verdict=failure
 elif config["concurrency"]==1:verdict="PASS_C1_128K" if config["context_tokens"]==131072 else "PASS"
 else:verdict=concurrency_verdict
 if verdict not in VALID:raise AssertionError(verdict)
 m=summarize(config,records,evidence,verdict,gpu_summary);m["verdict"]=verdict;m["concurrency_verdict"]=concurrency_verdict;m["mechanical_output_verdict"]="PASS" if values=={PASS} else ("FAIL_OUTPUT" if "FAIL_OUTPUT" in values else "NOT_ALL_PASS");save(output/"metrics.json",m);save(output/"completion.json",{"experiment_id":config["experiment_id"],"verdict":verdict,"completed_at_utc":utc(),"post_health":after});return verdict


def inspect_run(output):
 p=Path(output);c=json.loads((p/"config.json").read_text());i=json.loads((p/"identity.json").read_text())
 if sha(canon(c))!=i["config_sha256"]:raise ValueError("config identity mismatch")
 return {"config_valid":True,"completion":json.loads((p/"completion.json").read_text()) if (p/"completion.json").exists() else None}
