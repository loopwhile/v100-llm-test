import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bench_harness as h
import build_128k_workload as builder

class FakeAdapter:
    def receipt(self,payload):
        return {"source":"fake-char-tokenizer","prompt_tokens":max(1,len(payload["messages"][0]["content"])//4)}

class WBS3V2ContractTests(unittest.TestCase):
    def test_manifest_and_oracle(self):
        m=builder.load_manifest(ROOT/"workloads/concurrency/v2.json")
        o=json.loads((ROOT/"workloads/concurrency/v2-ground-truth.json").read_text())
        self.assertEqual(m["workload_id"],"V100-CONCURRENCY-C2-128K-v2")
        self.assertEqual(o["workload_id"],m["workload_id"])
        self.assertEqual(set(o["projects"]),{"A","B"})
        self.assertTrue(m["acceptance_contract"]["concurrency_evidence_independent_of_output_verdict"])

    def test_anchor_once_and_variant_padding(self):
        m=builder.load_manifest(ROOT/"workloads/concurrency/v2.json")
        rendered=builder.render(m["requests"][0],3)
        self.assertEqual(rendered.count("GROUND-TRUTH ANCHOR"),1)
        self.assertEqual(rendered.count("self.pending.clear()"),1)
        self.assertIn("StorageTelemetry_000001",rendered)
        self.assertIn("checksum_probe_000002",rendered)
        self.assertNotIn("{{SECTION}}",rendered)

    def test_build_preserves_oracle_identity(self):
        m=builder.load_manifest(ROOT/"workloads/concurrency/v2.json")
        result=builder.build(m,FakeAdapter(),"mock-model")
        self.assertEqual(result["semantic_oracle"],m["semantic_oracle"])
        self.assertEqual(len({x["raw_prompt_sha256"] for x in result["build_evidence"]}),2)

    def test_queue_evidence_survives_output_failure(self):
        a=h.HTTPAdapter("http://mock","1Cat-vLLM")
        a._probe_samples=[{"monotonic_s":10.0,"processing":1.0,"waiting":1.0,"resident_slots":None},{"monotonic_s":20.0,"processing":1.0,"waiting":0.0,"resident_slots":None}]
        e=a.overlap_evidence([{"verdict":"FAIL_OUTPUT","first_abs":11.0,"end_abs":15.0},{"verdict":"PASS","first_abs":16.0,"end_abs":19.0}])
        self.assertTrue(e["queue_only"]);self.assertFalse(e["active_overlap"]);self.assertFalse(e["resident"])

    def test_active_evidence_survives_output_failure(self):
        a=h.HTTPAdapter("http://mock","1Cat-vLLM")
        a._probe_samples=[{"monotonic_s":12.0,"processing":2.0,"waiting":0.0,"resident_slots":None}]
        e=a.overlap_evidence([{"verdict":"FAIL_OUTPUT","first_abs":10.0,"end_abs":14.0},{"verdict":"FAIL_OUTPUT","first_abs":11.0,"end_abs":15.0}])
        self.assertTrue(e["active_overlap"]);self.assertTrue(e["resident"]);self.assertFalse(e["queue_only"])

if __name__=="__main__":unittest.main()
