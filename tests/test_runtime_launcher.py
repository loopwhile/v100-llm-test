from pathlib import Path
import copy,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import runtime_launcher as r

class RuntimePlanTests(unittest.TestCase):
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
  self.assertEqual(len(p["commands"]),2);self.assertEqual(p["endpoints"],["http://127.0.0.1:18080","http://127.0.0.1:18081"])
  self.assertIn("device=0",p["commands"][0]);self.assertIn("device=1",p["commands"][1])
 def test_ornith9_stock_independent_when_artifact_resolves(self):
  lock,_,_,m=r.state(ROOT,"ornith-1.5-9b");m=copy.deepcopy(m);m["onecat_vllm"].update(path="/srv/models/mock-ornith9",weight_quant="NVFP4",kv_candidates=["FP16"],speculative_candidates=["MTP"])
  p=r.onecat_plan(lock,m,"STOCK",2,"1gpu-x2-independent",18080);self.assertTrue(p["supported_for_planning"]);self.assertEqual(len(p["commands"]),2);self.assertEqual(p["command_environments"],[{"CUDA_VISIBLE_DEVICES":"0"},{"CUDA_VISIBLE_DEVICES":"1"}])
  for c in p["commands"]:self.assertEqual(c[c.index("--tensor-parallel-size")+1],"1");self.assertEqual(c[c.index("--max-num-seqs")+1],"1")
 def test_stock_tp2_c2(self):
  p=r.build_plan(ROOT,"qwen3.8-27b","STOCK",2,"tp2-shared");c=p["commands"][0]
  self.assertEqual(c[c.index("--tensor-parallel-size")+1],"2");self.assertEqual(c[c.index("--max-num-seqs")+1],"2")
 def test_skinny_is_separate_tp2_experiment(self):
  p=r.build_plan(ROOT,"qwen3.8-27b","SKINNY",2,"tp2-shared");c=p["commands"][0]
  self.assertTrue(p["experimental_tp2"]);self.assertEqual(p["upstream_reference_topology"],"TP4")
  self.assertIn("5b589c0",p["runtime_revision"]);self.assertEqual(c[c.index("--tensor-parallel-size")+1],"2")
  self.assertEqual(p["kv_cache"],"FP16")
 def test_non_qwen_skinny_is_explicit_unsupported(self):
  p=r.build_plan(ROOT,"ornith-1.5-9b","SKINNY",1,"tp2-shared")
  self.assertFalse(p["supported_for_planning"]);self.assertEqual(p["verdict_if_executed_without_new_support"],"UNSUPPORTED")
 def test_gemma_unpinned_artifact(self):
  self.assertFalse(r.build_plan(ROOT,"gemma4-26b-a4b","NGRAM",1,"tp2-shared")["supported_for_planning"])
if __name__=="__main__":unittest.main()
