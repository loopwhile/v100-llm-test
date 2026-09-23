import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_128k_workload as builder


class FakeAdapter:
    def receipt(self, payload):
        content = payload["messages"][0]["content"]
        return {"source": "fake-char-tokenizer", "prompt_tokens": max(1, len(content) // 4)}


class WorkloadBuilderTests(unittest.TestCase):
    def test_manifests_load_and_shape(self):
        capacity = builder.load_manifest(ROOT / "workloads/capacity/v1.json")
        concurrency = builder.load_manifest(ROOT / "workloads/concurrency/v1.json")
        performance = builder.load_manifest(ROOT / "workloads/performance/v1.json")
        self.assertEqual(len(capacity["requests"]), 1)
        self.assertEqual(len(concurrency["requests"]), 2)
        self.assertEqual(len(performance["requests"]), 2)
        self.assertEqual(capacity["min_output_tokens"], 256)
        self.assertEqual(performance["min_output_tokens"], 1024)
        self.assertTrue(performance["diversify_identifiers"])
        self.assertTrue(concurrency["independent_projects_required"])
        self.assertNotEqual(
            concurrency["requests"][0]["project_id"],
            concurrency["requests"][1]["project_id"],
        )

    def test_capacity_materializes_near_128k(self):
        manifest = builder.load_manifest(ROOT / "workloads/capacity/v1.json")
        result = builder.build(manifest, FakeAdapter(), "mock-model")
        self.assertEqual(len(result["requests"]), 1)
        item = result["build_evidence"][0]
        self.assertLessEqual(item["total_budget_used"], 131072)
        self.assertGreaterEqual(item["utilization"], 0.99)

    def test_c2_materializes_independent_near_128k_prompts(self):
        manifest = builder.load_manifest(ROOT / "workloads/concurrency/v1.json")
        result = builder.build(manifest, FakeAdapter(), "mock-model")
        self.assertEqual(len(result["requests"]), 2)
        hashes = [x["raw_prompt_sha256"] for x in result["build_evidence"]]
        self.assertEqual(len(set(hashes)), 2)
        for item in result["build_evidence"]:
            self.assertLessEqual(item["total_budget_used"], 131072)
            self.assertGreaterEqual(item["utilization"], 0.99)

    def test_performance_diversification_changes_repeated_block(self):
        manifest = builder.load_manifest(ROOT / "workloads/performance/v1.json")
        spec = manifest["requests"][0]
        plain = builder.render(spec, 2, diversify_identifiers=False)
        diverse = builder.render(spec, 2, diversify_identifiers=True)
        self.assertNotEqual(plain, diverse)
        self.assertIn("PageIndex_a_000001", diverse)

    def test_duplicate_c2_project_id_rejected(self):
        manifest = json.loads((ROOT / "workloads/concurrency/v1.json").read_text())
        manifest["requests"][1]["project_id"] = manifest["requests"][0]["project_id"]
        path = ROOT / "workloads/generated/test-invalid.json"
        # Exercise validation without writing generated content.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "manifest.json"
            p.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                builder.load_manifest(p)


if __name__ == "__main__":
    unittest.main()
