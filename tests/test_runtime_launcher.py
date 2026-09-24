from pathlib import Path
import copy,csv,sys,unittest
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import runtime_launcher as r

class RuntimePlanTests(unittest.TestCase):
 def test_docker_gpu_list_is_one_csv_field(self):
  cmd=r.build_plan(ROOT,"qwen3.8-27b","TARGET",1,"tp2-shared")["commands"][0]
  self.assertEqual(next(csv.reader([cmd[cmd.index("--gpus")+1]])),["device=0,1"])
 def test_llama_help_probe_has_cuda_driver_access(self):
  plan=r.build_plan(ROOT,"qwen3.8-27b","TARGET",1,"tp2-shared")
  calls=[]
  def execute(cmd,**kwargs):
   calls.append(cmd)
   return SimpleNamespace(returncode=0,stdout="--spec-type --kv-unified --kv-unified-per-slot --slots",stderr="")
  with patch.object(r.socket,"gethostname",return_value="p520-llm"),patch.object(r.shutil,"which",return_value="docker"),patch.object(Path,"is_file",return_value=True),patch.object(r.subprocess,"run",side_effect=execute):
   self.assertTrue(r.preflight(plan)["pass"])
  help_cmd=next(cmd for cmd in calls if "--help" in cmd)
  self.assertEqual(help_cmd[help_cmd.index("--gpus")+1],"all")
 def test_four_llama_lanes(self):
  _,lanes,_,_=r.state(ROOT,"qwen3.8-27b")
  self.assertEqual([x["id"] for x in lanes["llama_cpp"]["required_lanes"]],["TARGET","NGRAM","MTP","MTP_NGRAM"])
 def test_c2_shared_is_256k_pool_with_128k_slot(self):
  p=r.build_plan(ROOT,"qwen3.8-27b","TARGET",2,"tp2-shared");c=p["commands"][0]
  self.assertEqual(c[c.index("--ctx-size")+1],"262144");self.assertEqual(c[c.index("--parallel")+1],"2")
  self.assertEqual(c[c.index("--kv-unified-per-slot")+1],"131072");self.assertIn("--slots",c)
 def test_target_vs_ngram(self):
  a=r.build_plan(ROOT,"qwen3.8-27b","TARGET",1,"tp2-shared")["commands"][0]
  b=r.build_plan(ROOT,"qwen3.8-27b","NGRAM",1,"tp2-shared")["commands"][0]
  self.assertEqual(a[a.index("--spec-type")+1],"none");self.assertEqual(b[b.index("--spec-type")+1],"ngram-simple")
 def test_ornith9_independent_servers(self):
  p=r.build_plan(ROOT,"ornith-1.5-9b","MTP_NGRAM",2,"1gpu-x2-independent")
  self.assertEqual(len(p["commands"]),2);self.assertEqual(p["backend_endpoints"],["http://127.0.0.1:18080","http://127.0.0.1:18081"]);self.assertEqual(p["endpoints"],["http://127.0.0.1:18079"])
  self.assertIn("device=0",p["commands"][0]);self.assertIn("device=1",p["commands"][1])
  self.assertEqual(p["gateway"]["runtime"],"LiteLLM");self.assertEqual(p["gateway"]["routing_strategy"],"least-busy");self.assertEqual(len(p["gateway"]["config"]["model_list"]),2)
  self.assertTrue(all(x["litellm_params"]["max_parallel_requests"]==1 for x in p["gateway"]["config"]["model_list"]))
  self.assertTrue(all(x["litellm_params"]["max_retries"]==0 and x["litellm_params"]["timeout"]==1800 and x["litellm_params"]["stream_timeout"]==1800 for x in p["gateway"]["config"]["model_list"]))
 def test_ornith9_independent_c1_still_uses_full_gateway_topology(self):
  p=r.build_plan(ROOT,"ornith-1.5-9b","TARGET",1,"1gpu-x2-independent")
  self.assertEqual(len(p["commands"]),2);self.assertEqual(p["endpoints"],["http://127.0.0.1:18079"]);self.assertEqual(p["concurrency"],1)
 def test_ornith9_stock_independent_when_artifact_resolves(self):
  lock,_,_,m=r.state(ROOT,"ornith-1.5-9b");m=copy.deepcopy(m);m["onecat_vllm"].update(planning_ready=True,path="/srv/models/mock-ornith9",weight_quant="NVFP4",kv_candidates=["FP16"],speculative_candidates=["MTP"],speculative_config={"method":"mtp","num_speculative_tokens":3})
  p=r.onecat_plan(lock,m,"STOCK",2,"1gpu-x2-independent",18080);self.assertTrue(p["supported_for_planning"]);self.assertEqual(len(p["commands"]),2);self.assertEqual(p["command_environments"],[{"CUDA_VISIBLE_DEVICES":"0","VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL":"0"},{"CUDA_VISIBLE_DEVICES":"1","VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL":"0"}]);self.assertEqual(p["endpoints"],["http://127.0.0.1:18079"])
  for c in p["commands"]:self.assertEqual(c[c.index("--tensor-parallel-size")+1],"1");self.assertEqual(c[c.index("--max-num-seqs")+1],"1");self.assertIn("--speculative-config",c)
 def test_ornith9_stock_fails_closed_without_spec_config(self):
  lock,_,_,m=r.state(ROOT,"ornith-1.5-9b");m=copy.deepcopy(m);m["onecat_vllm"].update(planning_ready=True,path="/srv/models/mock-ornith9",weight_quant="NVFP4",kv_candidates=["FP16"],speculative_candidates=["MTP"])
  m["onecat_vllm"].pop("speculative_config",None)
  p=r.onecat_plan(lock,m,"STOCK",2,"1gpu-x2-independent",18080);self.assertFalse(p["supported_for_planning"]);self.assertIn("speculative",p["reason"])
 def test_stock_tp2_c2(self):
  p=r.build_plan(ROOT,"qwen3.8-27b","STOCK",2,"tp2-shared");c=p["commands"][0]
  self.assertEqual(c[c.index("--tensor-parallel-size")+1],"2");self.assertEqual(c[c.index("--max-num-seqs")+1],"2")
  self.assertEqual(c[c.index("--kv-cache-dtype")+1],"fp8_e4m3")
  self.assertEqual(c[c.index("--max-num-batched-tokens")+1],"4096")
 def test_ornith9_stock_contract_is_pinned_for_host_gate(self):
  p=r.build_plan(ROOT,"ornith-1.5-9b","STOCK",1,"tp2-shared");c=p["commands"][0]
  self.assertTrue(p["supported_for_planning"])
  self.assertEqual(c[c.index("--attention-backend")+1],"FLASH_ATTN_V100")
  self.assertEqual(c[c.index("--kv-cache-dtype")+1],"float16")
  self.assertEqual(c[c.index("--max-num-batched-tokens")+1],"4096")
  self.assertIn("--speculative-config",c)
  spec=__import__("json").loads(c[c.index("--speculative-config")+1])
  self.assertEqual(spec["method"],"mtp");self.assertEqual(spec["num_speculative_tokens"],1)
  self.assertEqual(spec["attention_backend"],"TRITON_ATTN")
 def test_ornith35_stock_contract_uses_explicit_e5m2(self):
  p=r.build_plan(ROOT,"ornith-1.5-35b-a3b","STOCK",1,"tp2-shared");c=p["commands"][0]
  self.assertTrue(p["supported_for_planning"])
  self.assertEqual(c[c.index("--attention-backend")+1],"FLASH_ATTN_V100")
  self.assertEqual(c[c.index("--kv-cache-dtype")+1],"fp8_e5m2")
  self.assertEqual(c[c.index("--max-num-batched-tokens")+1],"4096")
  self.assertNotIn("--speculative-config",c)
 def test_gemma_stock_contract_is_pinned_for_download_and_host_gate(self):
  p=r.build_plan(ROOT,"gemma4-26b-a4b","STOCK",1,"tp2-shared");c=p["commands"][0]
  self.assertTrue(p["supported_for_planning"])
  self.assertEqual(p["model_identity"]["repository"],"nvidia/Gemma-4-26B-A4B-NVFP4")
  self.assertEqual(p["model_identity"]["revision"],"a19cfe00be84568a6867111c9a68c9c44fdcffe6")
  self.assertEqual(c[c.index("--attention-backend")+1],"TRITON_ATTN")
  self.assertEqual(c[c.index("--kv-cache-dtype")+1],"float16")
  self.assertEqual(c[c.index("--max-num-batched-tokens")+1],"4096")
  self.assertNotIn("--speculative-config",c)
 def test_fp8_kv_subtypes_must_be_explicit(self):
  self.assertEqual(r.kv("fp8_e4m3"),"fp8_e4m3")
  self.assertEqual(r.kv("fp8_e5m2"),"fp8_e5m2")
  self.assertEqual(r.kv("FP16","1Cat-vLLM"),"float16")
  self.assertEqual(r.kv("FP16","llama.cpp"),"f16")
  with self.assertRaises(ValueError):r.kv("FP8")
  with self.assertRaises(ValueError):r.kv("fp8")
  with self.assertRaises(ValueError):r.kv("FP8","1Cat-vLLM")
 def test_skinny_closed_after_model_load_oom(self):
  p=r.build_plan(ROOT,"qwen3.8-27b","SKINNY",2,"tp2-shared")
  self.assertFalse(p["supported_for_planning"]);self.assertNotIn("commands",p)
  self.assertIn("FAIL_OOM_MODEL_LOAD",p["reason"])
 def test_non_qwen_skinny_is_explicit_unsupported(self):
  p=r.build_plan(ROOT,"ornith-1.5-9b","SKINNY",1,"tp2-shared")
  self.assertFalse(p["supported_for_planning"]);self.assertEqual(p["verdict_if_executed_without_new_support"],"UNSUPPORTED")
 def test_ornith35_native_mtp_uses_one_draft_token(self):
  for lane in ("MTP","MTP_NGRAM"):
   p=r.build_plan(ROOT,"ornith-1.5-35b-a3b",lane,1,"tp2-shared")
   cmd=p["commands"][0]
   self.assertEqual(cmd[cmd.index("--spec-draft-n-max")+1],"1")
 def test_ornith9_native_mtp_keeps_default_three(self):
  p=r.build_plan(ROOT,"ornith-1.5-9b","MTP",1,"tp2-shared")
  cmd=p["commands"][0]
  self.assertEqual(cmd[cmd.index("--spec-draft-n-max")+1],"3")
 def test_gemma_mtp_uses_explicit_companion(self):
  for lane in ("MTP","MTP_NGRAM"):
   p=r.build_plan(ROOT,"gemma4-26b-a4b",lane,1,"tp2-shared")
   c=p["commands"][0]
   self.assertEqual(c[c.index("--spec-draft-n-max")+1],"4")
   self.assertEqual(c[c.index("--model-draft")+1],"/model/draft.gguf")
   self.assertEqual(c[c.index("--spec-draft-device")+1],"CUDA0,CUDA1")
   self.assertTrue(any("mtp-gemma-4-26B-A4B-it.gguf:/model/draft.gguf:ro" in x for x in c))
 def test_gemma_target_does_not_mount_companion(self):
  c=r.build_plan(ROOT,"gemma4-26b-a4b","TARGET",1,"tp2-shared")["commands"][0]
  self.assertNotIn("--model-draft",c)
  self.assertFalse(any("/model/draft.gguf" in x for x in c))
 def test_gemma_verified_llama_and_pinned_stock_plan(self):
  self.assertTrue(r.build_plan(ROOT,"gemma4-26b-a4b","NGRAM",1,"tp2-shared")["supported_for_planning"])
  self.assertTrue(r.build_plan(ROOT,"gemma4-26b-a4b","STOCK",1,"tp2-shared")["supported_for_planning"])
if __name__=="__main__":unittest.main()
