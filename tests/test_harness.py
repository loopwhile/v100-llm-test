import csv, io, json, sys, tempfile, threading, time, unittest, urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
import bench_harness as h, report_experiment as report

CONFIG={"experiment_id":"EXP-V100-Q38-LLAMA-Q8-NONE-C1-128K-001","model":"Qwen3.8-27B","runtime":"llama.cpp","runtime_revision":"mock","model_identity":"mock-sha","launch_command":"mock","backend_variant":"stock","weight_quant":"UD-Q4_K_M","kv_cache":"Q8_0","speculative":"target-only","ngram":"off","topology":"2xV100-TP2","prefix_cache_lane":"cold-independent","chat_template":"mock","tool_parser":"none","thinking":False,"context_tokens":131072,"concurrency":1,"context_test":True,"notes":"csv, newline\nquote"}
WORKLOAD={"version":"mock-128k-v1","sampling":{"temperature":0},"requests":[
 {"id":"project-a","project_id":"A","messages":[{"role":"user","content":"project A unique material"}],"max_tokens":512,"min_output_tokens":256,"check":"nonempty"},
 {"id":"project-b","project_id":"B","messages":[{"role":"user","content":"project B different material"}],"max_tokens":512,"min_output_tokens":256,"check":"nonempty"}]}
def response(): return {"choices":[{"finish_reason":"stop","message":{"content":"ok"}}],"usage":{"prompt_tokens":130560,"completion_tokens":512,"total_tokens":131072},"timings":{"prompt_per_second":900.0,"predicted_per_second":30.0}}
class Mock:
 def __init__(self, overlap=None, error=None, receipt=130560): self.overlap=overlap or {"source":"mock","resident":None,"active_overlap":None,"queue_only":None}; self.error=error; self.receipt_tokens=receipt; self.lock=threading.Lock(); self.active=0; self.peak=0
 def health(self): return {"healthy":True}
 def snapshot(self): return {"mock":True}
 def receipt(self,payload): return {"source":"mock","prompt_tokens":self.receipt_tokens}
 def stream_complete(self,payload):
  if self.error: raise self.error
  start=time.monotonic()
  with self.lock: self.active+=1; self.peak=max(self.peak,self.active)
  time.sleep(.01); first=time.monotonic(); time.sleep(.01); end=time.monotonic()
  with self.lock: self.active-=1
  return response(),{"submitted_s":start,"first_token_s":first,"terminal_s":end,"wall_s":end-start,"ttft_ms":(first-start)*1000,"itl_ms":1.0,"server_timings":{"prompt_per_second":900.0,"predicted_per_second":30.0}}
 def overlap_evidence(self,records): return dict(self.overlap)

class HarnessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); (self.root/"results").mkdir(); (self.root/"reports").mkdir()
  (self.root/"results/summary.csv").write_text(",".join(report.SUMMARY_FIELDS)+"\n"); (self.root/"reports/comparison.csv").write_text(",".join(report.COMPARISON_FIELDS)+"\n")
 def tearDown(self): self.tmp.cleanup()
 def run_case(self,name="run",adapter=None,config=None,workload=None):
  out=self.root/"results/raw"/name; verdict=h.run_batch(out,config or CONFIG,workload or WORKLOAD,adapter or Mock()); return out,verdict
 def test_c1_pass_identity_and_underfill(self):
  out,v=self.run_case(); self.assertEqual(v,"PASS_C1_128K"); self.assertTrue(h.inspect_run(out)["config_valid"])
  out2,v=self.run_case("under",Mock(receipt=1000)); self.assertEqual(v,"FAIL_CAPACITY"); self.assertFalse(json.loads((out2/"metrics.json").read_text())["c1_128k"])
 def test_minimum_output_is_enforced(self):
  w=json.loads(json.dumps(WORKLOAD)); w["requests"][0]["min_output_tokens"]=600
  self.assertEqual(self.run_case("short",workload=w)[1],"FAIL_OUTPUT")
 def test_c2_verdicts_and_barrier(self):
  cases=[({"source":"m","resident":True,"active_overlap":True,"queue_only":False},"PASS_C2_ACTIVE"),({"source":"m","resident":True,"active_overlap":None,"queue_only":False},"PASS_C2_RESIDENT"),({"source":"m","resident":True,"active_overlap":False,"queue_only":True},"QUEUE_ONLY"),({"source":"m","resident":None,"active_overlap":None,"queue_only":None},"INCONCLUSIVE")]
  for i,(e,want) in enumerate(cases):
   a=Mock(e); cfg=CONFIG|{"experiment_id":f"EXP-V100-Q38-LLAMA-Q8-NONE-C2-128K-00{i+1}","concurrency":2}; out,v=self.run_case(str(i),a,cfg); self.assertEqual(v,want); self.assertEqual(a.peak,2); self.assertEqual(len(json.loads((out/"requests.json").read_text())),2)
 def test_multi_endpoint_routes_independent_servers(self):
  cfg=CONFIG|{"experiment_id":"EXP-V100-ORN9-LLAMA-F16-MTP-C2-128K-001","concurrency":2,"topology":"1gpu-x2-independent"}
  self.assertEqual(self.run_case("independent",h.MultiEndpointAdapter([Mock(),Mock()]),cfg)[1],"PASS_C2_ACTIVE")
 def test_server_metric_overlap_classification(self):
  a=h.HTTPAdapter("http://mock","1Cat-vLLM");a._probe_samples=[{"monotonic_s":11.0,"processing":2.0,"waiting":0.0,"resident_slots":None},{"monotonic_s":12.0,"processing":2.0,"waiting":0.0,"resident_slots":None}]
  e=a.overlap_evidence([{"verdict":h.PASS,"first_abs":10.0,"end_abs":13.0},{"verdict":h.PASS,"first_abs":10.5,"end_abs":14.0}]);self.assertTrue(e["resident"]);self.assertTrue(e["active_overlap"]);self.assertFalse(e["queue_only"])
 def test_runtime_log_directory_may_preexist(self):
  out=self.root/"results/raw"/"precreated";(out/"runtime").mkdir(parents=True);(out/"runtime/server-0.log").write_text("boot")
  self.assertEqual(h.run_batch(out,CONFIG,WORKLOAD,Mock()),"PASS_C1_128K")
 def test_c2_independent_prompt_guard(self):
  w=json.loads(json.dumps(WORKLOAD)); w["requests"][1]["messages"]=w["requests"][0]["messages"]; cfg=CONFIG|{"experiment_id":"EXP-V100-Q38-LLAMA-Q8-NONE-C2-128K-010","concurrency":2}
  with self.assertRaisesRegex(ValueError,"independent"): h.run_batch(self.root/"same",cfg,w,Mock())
 def test_failure_classification(self):
  failures=[(TimeoutError("x"),"FAIL_TIMEOUT"),(urllib.error.HTTPError("m",500,"",{},io.BytesIO(b"CUDA out of memory")),"FAIL_OOM"),(urllib.error.HTTPError("m",400,"",{},io.BytesIO(b"maximum context length")),"FAIL_CAPACITY")]
  for i,(err,want) in enumerate(failures): self.assertEqual(self.run_case(str(20+i),Mock(error=err))[1],want)
 def test_publication_duplicate_and_recovery(self):
  out,_=self.run_case("pub"); path=report.publish(self.root,out); self.assertTrue((self.root/path).exists())
  for p in ("results/summary.csv","reports/comparison.csv"):
   with (self.root/p).open(newline="") as f: self.assertEqual(len(list(csv.DictReader(f))),1)
  with self.assertRaises(ValueError): report.publish(self.root,out)
  journal=self.root/"results/.publication.json"; journal.write_text(json.dumps({"writes":{"reports/recovered.md":"ok"}})); self.assertTrue(report.recover(self.root)); self.assertEqual((self.root/"reports/recovered.md").read_text(),"ok")
 def test_publication_midwrite_recovery(self):
  out,_=self.run_case("mid"); original=report.atomic_text; calls=[]
  def fail(path,text):
   calls.append(str(path))
   if len(calls)==3: raise OSError("simulated")
   return original(path,text)
  with patch.object(report,"atomic_text",side_effect=fail):
   with self.assertRaises(OSError): report.publish(self.root,out)
  report.recover(self.root)
  for p in ("results/summary.csv","reports/comparison.csv"):
   with (self.root/p).open(newline="") as f: self.assertEqual(len(list(csv.DictReader(f))),1)
 def test_sse_parser(self):
  sse=b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: {"usage":{"prompt_tokens":10,"completion_tokens":2},"timings":{"predicted_per_second":40.0}}\n\ndata: [DONE]\n\n'; a=h.HTTPAdapter("http://mock","llama.cpp")
  with patch.object(h.urllib.request,"urlopen",return_value=io.BytesIO(sse)): r,t=a.stream_complete({"messages":[]})
  self.assertEqual(r["choices"][0]["message"]["content"],"Hello"); self.assertEqual(r["usage"]["completion_tokens"],2); self.assertIsNotNone(t["ttft_ms"])
if __name__=="__main__": unittest.main()
