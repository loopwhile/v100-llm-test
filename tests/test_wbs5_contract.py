"""Offline WBS5 admission/configuration/evidence tests. No live GPU or HTTP calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bench_harness as h
import run_wbs5 as runner
import wbs5_contract as c
import wbs5_evidence as e


def plan(track="qwen-llama", candidate="R0", sequence=1, label=None):
    label = label or ("repetition-1" if track == "qwen-llama" and candidate == "R0" else "screening-1")
    return c.build_plan(track, candidate, c.experiment_id(track, candidate, "20260928", sequence), label)


class FrozenContractTests(unittest.TestCase):
    def test_qwen_known_serving_decode_invariant_is_common_and_not_an_ofat_axis(self):
        raw = ROOT / "results/raw/EXP-V100-Q38-1CAT-FP8E4M3-TARGET-RECIPE-B200-C1-128K-20260925-001"
        old = json.loads((raw / "config.json").read_text())
        planned = json.loads((raw / "runtime/planned-config.json").read_text())
        flag = "VLLM_SM70_GDN_DECODE_FLASHQLA"
        self.assertEqual(old["command_environments"][0][flag], "0")
        self.assertEqual(old["command_environments"], planned["command_environments"])
        for i in range(4):
            p = plan("qwen-onecat", f"R{i}")
            env = p["launch_plan"]["command_environments"][0]
            self.assertEqual(env[flag], "0")
            self.assertEqual(env["VLLM_FLASH_V100_DECODE_PARTITION_SIZE"], "256")
            self.assertEqual(env["VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL"], "1" if i == 2 else "0")
            self.assertFalse(any(flag in row["path"] for row in p["normalized_delta_from_r0"]))
            dry = runner.dispatch(p)
            self.assertEqual(dry["effective_environment"][0][flag], "0")
            self.assertFalse(dry["measured_inference_executed"])
            config = runner.build_config(p, dry["effective_environment"])
            self.assertEqual(config["sampling"], {"temperature": 0, "top_p": 1, "seed": 520})
            self.assertEqual(config["tool_parser"], "none")
            self.assertFalse(config["thinking"])
            self.assertNotIn("--reasoning-parser", p["launch_plan"]["commands"][0])
            self.assertNotIn("--tool-call-parser", p["launch_plan"]["commands"][0])
        for track in set(c.TRACKS) - {"qwen-onecat"}:
            self.assertNotIn(flag, c.launch_plan(track, "R0")["command_environments"][0])

    def test_qwen_decode_invariant_drop_enable_and_ambient_drift_are_rejected(self):
        flag = "VLLM_SM70_GDN_DECODE_FLASHQLA"
        for i in range(4):
            baseline = c.launch_plan("qwen-onecat", f"R{i}")
            for value in (None, "1"):
                changed = copy.deepcopy(baseline)
                if value is None:
                    del changed["command_environments"][0][flag]
                else:
                    changed["command_environments"][0][flag] = value
                with self.assertRaisesRegex(ValueError, "FROZEN_DELTA_MISMATCH"):
                    c.assert_launch("qwen-onecat", f"R{i}", changed)
            with self.assertRaisesRegex(ValueError, "FROZEN_DELTA_MISMATCH"):
                c.effective_environments(baseline, {flag: "1"})
            self.assertEqual(c.effective_environments(baseline, {flag: "0"})[0][flag], "0")

    def test_pinned_decode_default_static_source_and_historical_route_receipt(self):
        import ast
        receipt = json.loads((ROOT / "state/wbs5-qwen-gdn-route-audit.json").read_text())
        self.assertEqual(receipt["decision"], "ADD_BASELINE_INVARIANT")
        self.assertEqual(receipt["pinned_source_default"], "1")
        self.assertEqual(receipt["historical_success"]["environment"][receipt["flag"]], "0")
        # Parse only the saved source expression; do not import vLLM/torch or
        # evaluate the runtime configuration/device checks.
        rows = receipt["source"]["vllm/envs.py"]["lines"]
        expression = "{" + "\n".join(row["text"].strip() for row in rows if 3254 <= row["line"] <= 3256) + "}"
        parsed = ast.parse(expression, mode="eval")
        get = next(node for node in ast.walk(parsed) if isinstance(node, ast.Call)
                   and isinstance(node.func, ast.Attribute) and node.func.attr == "getenv")
        self.assertEqual([node.value for node in get.args], [receipt["flag"], "1"])
        raw = ROOT / "results/raw" / receipt["historical_success"]["experiment_id"]
        log = (raw / "runtime/server-0.log").read_text()
        self.assertIn("SM70 exact mixed-QKV GDN decode route enabled.", log)
        self.assertIn("fused_sigmoid_gating_delta_rule_update_kernel", log)
        self.assertFalse(any(receipt["execution"].values()))

    def test_all_frozen_ids_and_counts(self):
        expected = {"qwen-llama": 3, "ornith9-llama": 3, "ornith35-llama": 4,
                    "gemma-llama": 4, "qwen-onecat": 4, "ornith9-onecat": 4, "ornith35-onecat": 3}
        self.assertEqual({t: len(v[2]) for t, v in c.TRACKS.items()}, expected)
        self.assertEqual(sum(expected.values()), 25)
        docs = "\n".join(p.read_text() for p in (ROOT / "docs").glob("WBS-5 - *.md"))
        for track, (_, _, ids) in c.TRACKS.items():
            for i, cid in enumerate(ids):
                with self.subTest(track=track, candidate=i):
                    self.assertEqual(plan(track, f"R{i}")["candidate_id"], cid)
                    self.assertIn(cid, docs)

    def test_unknown_rejected(self):
        for track, candidate in (("unknown", "R0"), ("qwen-llama", "R3"), ("ornith9-llama", "R3"),
                                 ("qwen-onecat", "R4"), ("qwen-onecat", "R01")):
            with self.assertRaises(ValueError):
                c.candidate_id(track, candidate)

    def test_workload_pins_and_wbs3_separation(self):
        self.assertEqual(h.sha((ROOT / c.WORKLOAD).read_bytes()), c.WORKLOAD_SHA)
        import run_c2_llama
        import run_c2_onecat
        self.assertEqual(run_c2_llama.WORKLOAD_MANIFEST.name, "v2.json")
        self.assertEqual(run_c2_onecat.WORKLOAD_MANIFEST.name, "v2.json")
        for track, (_, _, ids) in c.TRACKS.items():
            for i in range(len(ids)):
                p = plan(track, f"R{i}")
                self.assertEqual(p["workload"], {"path": c.WORKLOAD, "sha256": c.WORKLOAD_SHA,
                    "context_per_request": 131072, "requests": ["project-a", "project-b"],
                    "output_reserve": 4096, "min_output": 1024})
                self.assertTrue(p["expected_artifact_hash"])
                self.assertEqual(p["launch_plan"]["concurrency"], 2)

    def test_exact_delta_paths_all_candidates(self):
        # Expected independent axes; two servers may share the same axis, and a
        # native MTP / graph axis can require two coupled command fields.
        expected = {
            "qwen-llama": [["--spec-type"], ["--ubatch-size"]],
            "ornith9-llama": [["--ubatch-size"] * 2, ["--spec-type"] * 2],
            "ornith35-llama": [["--spec-draft-n-max", "--spec-type"], ["--ubatch-size"], ["CUDA_SCALE_LAUNCH_QUEUES"]],
            "gemma-llama": [["--spec-type"], ["--batch-size"], ["GGML_CUDA_DISABLE_GRAPHS"]],
            "qwen-onecat": [["--compilation-config", "--enforce-eager"], ["VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL"], ["--kv-cache-dtype"]],
            "ornith9-onecat": [["--max-num-batched-tokens"], ["--enforce-eager"], ["--speculative-config"]],
            "ornith35-onecat": [["--enforce-eager"], ["--max-num-batched-tokens"]],
        }
        for track, axes in expected.items():
            self.assertEqual(plan(track)["normalized_delta_from_r0"], [])
            for i, fields in enumerate(axes, 1):
                rows = plan(track, f"R{i}")["normalized_delta_from_r0"]
                self.assertEqual(len(rows), len(fields), track)
                for row, field in zip(rows, fields):
                    self.assertIn("/" + field, row["path"])

    def test_final_command_and_environment_drift_hard_stop(self):
        for track in c.TRACKS:
            base = c.launch_plan(track, "R0")
            for key, value in (("commands", "--unexpected-tuning"), ("command_environments", "NCCL_TEST_OVERRIDE")):
                changed = copy.deepcopy(base)
                if key == "commands":
                    changed[key][0].append(value)
                else:
                    changed[key][0][value] = "1"
                with self.assertRaisesRegex(ValueError, "FROZEN_DELTA_MISMATCH"):
                    c.assert_launch(track, "R0", changed)
        with self.assertRaisesRegex(ValueError, "FROZEN_DELTA_MISMATCH"):
            c.effective_environments(c.launch_plan("qwen-onecat", "R0"), {"CUDA_HOME": "/unexpected"})
        # Even if dispatch generation changes accidentally, the independent
        # normalized allowlist refuses an extra knob or the wrong delta value.
        valid = plan("qwen-onecat", "R2")["normalized_delta_from_r0"]
        for changed in (valid + [{"path": "/servers/0/environment/CUDA_HOME", "r0": None, "candidate": "/cuda"}],
                        [dict(valid[0], candidate="0")]):
            with self.assertRaisesRegex(ValueError, "FROZEN_DELTA_MISMATCH"):
                c.assert_delta("qwen-onecat", "R2", changed)

    def test_worker_rejects_sampling_context_template_and_retry_drift(self):
        p = plan()
        with patch.dict("os.environ", {}, clear=True):
            config = runner.build_config(p, c.effective_environments(p["launch_plan"], {}))
            runner.validate_worker_config(config)
            for key, value in (("context_tokens", 65536), ("sampling", {"temperature": 1}),
                               ("thinking", True), ("chat_template_kwargs", {"enable_thinking": True}),
                               ("retry_of", "EXP-OLD"), ("measured_repetitions", 2)):
                changed = copy.deepcopy(config); changed[key] = value
                with self.assertRaises(ValueError):
                    runner.validate_worker_config(changed)

    def test_all_worker_configs_validate_or_stop_at_frozen_gate(self):
        with patch.dict("os.environ", {}, clear=True):
            for track, (_, _, ids) in c.TRACKS.items():
                for i in range(len(ids)):
                    p = plan(track, f"R{i}")
                    environments = c.effective_environments(p["launch_plan"], {})
                    if p["launch_plan"].get("gateway"):
                        environments.append(dict(environments[0]))
                    config = runner.build_config(p, environments)
                    if p["status"] == "STATIC_READY":
                        runner.validate_worker_config(config)
                    else:
                        with self.assertRaisesRegex(ValueError, "CONDITIONAL_PENDING_GATE|BLOCKED_BY_HOST_TOOLCHAIN"):
                            runner.validate_worker_config(config)

    def test_input_lock_cannot_be_rewritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "config").mkdir()
            (root / "config/wbs5-input-lock.json").write_text('{"sha256":{}}')
            with self.assertRaisesRegex(ValueError, "input lock"):
                c.verify_inputs(root)

    def test_materialized_workload_rejects_contract_drift(self):
        manifest = runner.w.load_manifest(ROOT / c.WORKLOAD)
        workload = {"version": manifest["workload_id"], "mode": "performance", "context_tokens": 131072,
                    "source_manifest_sha256": h.sha(h.canon(manifest)), "sampling": manifest["sampling"],
                    "requests": [{"project_id": x, "max_tokens": 4096, "min_output_tokens": 1024, "check": "nonempty"} for x in ("A", "B")]}
        runner.validate_workload(workload)
        for key, value in (("max_tokens", 2048), ("min_output_tokens", 1), ("tools", []), ("project_id", "A")):
            changed = copy.deepcopy(workload); changed["requests"][1][key] = value
            with self.assertRaisesRegex(ValueError, "WORKLOAD_IDENTITY_MISMATCH"):
                runner.validate_workload(changed)

    def test_qwen_onecat_forced_override_removed(self):
        r2 = c.launch_plan("qwen-onecat", "R2")
        self.assertEqual(r2["command_environments"][0]["VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL"], "1")
        r3 = c.launch_plan("qwen-onecat", "R3")
        self.assertEqual(c.normalized(r3)["servers"][0]["argv"]["--kv-cache-dtype"], ["fp8_e5m2"])
        self.assertEqual(r3["command_environments"][0]["VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL"], "0")
        for r in (r2, r3):
            self.assertNotIn("--reasoning-parser", r["commands"][0])
            self.assertNotIn("--speculative-config", r["commands"][0])

    def test_docker_environment_reaches_container_and_native_mtp_has_no_companion(self):
        for track, key, value in (("ornith35-llama", "CUDA_SCALE_LAUNCH_QUEUES", "4x"),
                                  ("gemma-llama", "GGML_CUDA_DISABLE_GRAPHS", "1")):
            p = plan(track, "R3")
            cmd = c.materialize_commands(p, Path(p["raw_destination"]))[0]
            self.assertEqual(cmd[cmd.index("--env") + 1], key + "=" + value)
            self.assertEqual(c.normalized(p["launch_plan"])["servers"][0]["container_environment"], {key: value})
        cmd = c.launch_plan("ornith35-llama", "R1")["commands"][0]
        self.assertEqual(cmd[cmd.index("--spec-draft-n-max") + 1], "1")
        self.assertNotIn("--model-draft", cmd)

    def test_repetition_and_confirm_same_config_fresh_ids(self):
        pairs = [(plan(sequence=1), plan(sequence=2, label="repetition-2")),
                 (plan(candidate="R1"), plan(candidate="R1", sequence=2, label="confirm-1")),
                 (plan(candidate="R2"), plan(candidate="R2", sequence=2, label="confirm-1"))]
        for a, b in pairs:
            self.assertNotEqual(a["experiment_id"], b["experiment_id"])
            self.assertEqual(a["configuration_sha256"], b["configuration_sha256"])
            self.assertEqual(a["workload"], b["workload"])
            self.assertFalse(b["run_identity"]["automatic_retry"])
        with self.assertRaises(ValueError):
            plan("ornith35-llama", label="confirm-1")
        mismatches = [
            ("ornith35-llama", "R0", 2, "screening-1"),
            ("qwen-llama", "R0", 2, "repetition-1"),
            ("qwen-llama", "R1", 1, "confirm-1"),
        ]
        for track, candidate, sequence, label in mismatches:
            with self.assertRaisesRegex(ValueError, "sequence"):
                plan(track, candidate, sequence=sequence, label=label)

    def test_default_dry_plan_has_no_host_gpu_http_or_raw_side_effect(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for track, (_, _, ids) in c.TRACKS.items():
                for i in range(len(ids)):
                    p = copy.deepcopy(plan(track, f"R{i}"))
                    # Published measured raw may legitimately exist in the repository.
                    # Give this side-effect test its own guaranteed-fresh raw target.
                    raw_destination = root / "raw-destinations" / p["experiment_id"]
                    p["raw_destination"] = str(raw_destination)
                    self.assertFalse(raw_destination.exists())
                    with patch("subprocess.run", side_effect=AssertionError("process called")), \
                         patch("subprocess.Popen", side_effect=AssertionError("startup called")), \
                         patch.object(h.HTTPAdapter, "call", side_effect=AssertionError("HTTP called")):
                        dry = runner.dispatch(p, output_root=root / "plans")
                    self.assertFalse(dry["measured_inference_executed"])
                    self.assertTrue(dry["exact_launch_commands"])
                    self.assertFalse(raw_destination.exists())
                    with self.assertRaises(FileExistsError):
                        runner.dispatch(p, output_root=root / "plans")

    def test_raw_overwrite_refused_before_any_process(self):
        with tempfile.TemporaryDirectory() as td:
            p = plan(); p["raw_destination"] = td
            marker = Path(td) / "old-evidence"; marker.write_text("preserve")
            with patch("subprocess.run", side_effect=AssertionError("process called")):
                with self.assertRaises(FileExistsError):
                    runner.execute_shared(p, None)
            self.assertEqual(marker.read_text(), "preserve")

    def test_gates_and_toolchain_guard_run_before_host_checks(self):
        for track, candidate in (("ornith9-onecat", "R0"), ("ornith9-onecat", "R3"),
                                 ("gemma-llama", "R3"), ("qwen-onecat", "R2")):
            p = plan(track, candidate)
            self.assertNotEqual(p["status"], "STATIC_READY")
            with patch("socket.gethostname", side_effect=AssertionError("host inspected")):
                with self.assertRaises(ValueError):
                    runner.dispatch(p, execute_measured=True)
        c.assert_admission(plan("qwen-onecat", "R0"))

    def test_g0_requires_hashed_separate_evidence(self):
        p = plan("ornith9-onecat", "R0")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); raw = root / "results/raw/EXP-GATE"
            raw.mkdir(parents=True); evidence = raw / "audit.json"
            evidence.write_text('{"verdict":"PASS"}')
            receipt = {"gate": p["admission_gate"], "verdict": "PASS", "track": p["track"],
                "baseline_configuration_sha256": plan(p["track"])["configuration_sha256"],
                "experiment_id": "EXP-GATE", "semantic_audit": "PASS", "project_a": "PASS", "project_b": "PASS",
                "file_sha256": c.verify_inputs()["sha256"],
                "evidence": [{"path": str(evidence), "sha256": h.sha(evidence.read_bytes())}]}
            with patch.object(c, "ROOT", root), patch.object(c, "verify_inputs", return_value=c.verify_inputs()):
                c.assert_admission(p, receipt)
                with self.assertRaises(ValueError):
                    c.assert_admission(p, dict(receipt, baseline_configuration_sha256="wrong"))
                evidence.write_text("changed")
                with self.assertRaises(ValueError):
                    c.assert_admission(p, receipt)

    def test_gate_b_requires_hash_bound_r0_measured_evidence(self):
        p = plan("gemma-llama", "R3")
        r0 = plan("gemma-llama", "R0")
        with patch.dict("os.environ", {}, clear=True):
            config = runner.build_config(r0, c.effective_environments(r0["launch_plan"], {}))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); raw = root / "results/raw" / r0["experiment_id"]
            raw.mkdir(parents=True)
            h.save(raw / "config.json", config)
            h.save(raw / "identity.json", {"config_sha256": h.sha(h.canon(config))})
            h.save(raw / "metrics.json", {"verdict": "PASS_C2_ACTIVE"})
            h.save(raw / "completion.json", {"experiment_id": r0["experiment_id"], "verdict": "PASS_C2_ACTIVE"})
            evidence = [{"path": str(raw / name), "sha256": h.sha((raw / name).read_bytes())}
                        for name in ("config.json", "identity.json", "metrics.json", "completion.json")]
            receipt = {"gate": "GEMMA_GATE_B", "verdict": "PASS", "track": "gemma-llama",
                       "baseline_configuration_sha256": r0["configuration_sha256"],
                       "experiment_id": r0["experiment_id"], "graph_support": "PASS",
                       "trigger": "R0_GRAPH_INSTABILITY", "evidence": evidence}
            with patch.object(c, "ROOT", root):
                c.assert_admission(p, receipt)
                only_audit = raw / "audit.json"; only_audit.write_text('{"verdict":"PASS"}')
                weak = dict(receipt, evidence=[{"path": str(only_audit), "sha256": h.sha(only_audit.read_bytes())}])
                with self.assertRaisesRegex(ValueError, "R0 measured evidence"):
                    c.assert_admission(p, weak)
                changed = copy.deepcopy(config); changed["candidate_key"] = "R1"
                h.save(raw / "config.json", changed)
                h.save(raw / "identity.json", {"config_sha256": h.sha(h.canon(changed))})
                bad = [{"path": str(raw / name), "sha256": h.sha((raw / name).read_bytes())}
                       for name in ("config.json", "identity.json", "metrics.json", "completion.json")]
                with self.assertRaisesRegex(ValueError, "not the frozen R0"):
                    c.assert_admission(p, dict(receipt, evidence=bad))


class EvidenceTests(unittest.TestCase):
    def test_graph_unknown_duplicate_conflict_and_actual_log(self):
        self.assertIsNone(e.graph_evidence({})["reuse_count"])
        line = "slot print_timing: id 0 | task 8 | graphs reused = 1412"
        parsed = e.graph_evidence({"server-0": line + "\n" + line})
        self.assertEqual(parsed["reuse_count"], 1412)
        self.assertEqual(parsed["items"][0]["task_id"], 8)
        for text in (line + "\n" + line.replace("1412", "1413"), "graphs reused = 15"):
            parsed = e.graph_evidence({"server-0": text})
            self.assertEqual(parsed["status"], "UNKNOWN")
            self.assertIsNone(parsed["reuse_count"])
        self.assertEqual(e.graph_evidence({"server-0": line.replace("1412", "0")})["reuse_count"], 0)

    def test_slot_prompt_progress_monotonic_and_missing_fields(self):
        slot = {"id": 1, "id_task": 12, "is_processing": True,
                "next_token": {"n_prompt_tokens_processed": 8192, "n_past": 8190, "n_decoded": 2}}
        row = e.slot_rows([slot], 20.5)[0]
        self.assertEqual((row["slot_id"], row["task_id"], row["n_prompt_tokens_processed"], row["n_past"], row["n_decoded"]),
                         (1, 12, 8192, 8190, 2))
        adapter = Mock(_probe_samples=[{"monotonic_s": 20.5, "slots": [slot]}], spec=["_probe_samples"])
        self.assertEqual(e.slot_progress(adapter)["status"], "OBSERVED")
        self.assertIsNone(e.slot_rows([{"id": 0, "is_processing": True}], 21)[0]["n_prompt_tokens_processed"])
        list_next_token = {"id": 0, "id_task": 74, "is_processing": True, "next_token": []}
        list_row = e.slot_rows([list_next_token], 21.5)[0]
        self.assertEqual((list_row["slot_id"], list_row["task_id"], list_row["is_processing"]), (0, 74, True))
        self.assertIsNone(list_row["n_prompt_tokens_processed"])
        self.assertIsNone(list_row["n_past"])
        self.assertIsNone(list_row["n_decoded"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "progress.jsonl"
            e.persist_slot_sample(path, adapter._probe_samples[0])
            self.assertEqual(json.loads(path.read_text())["rows"][0]["monotonic_s"], 20.5)

    def test_spec_missing_counters_reset_and_known_acceptance(self):
        for runtime, prefix in (("llama.cpp", "llamacpp"), ("1Cat-vLLM", "vllm")):
            def snapshot(draft, accepted=None, count=None):
                values = {"draft_tokens": draft, "accepted_tokens": accepted, "drafts": count}
                text = "\n".join(f"{prefix}:spec_decode_num_{key}_total {value}" for key, value in values.items() if value is not None)
                return {"/metrics": text}
            value = e.metric_delta(snapshot(0, 0, 0), snapshot(100, 25, 10), runtime)
            self.assertEqual(value["aggregate"]["acceptance_ratio"], .25)
            self.assertEqual(value["aggregate"]["draft_count"], 10)
            for before, after in (({}, {}), (snapshot(0), snapshot(100)), (snapshot(100, 25, 10), snapshot(1, 1, 1))):
                value = e.metric_delta(before, after, runtime)
                self.assertEqual(value["status"], "UNKNOWN")
                self.assertIsNone(value["aggregate"]["acceptance_ratio"])

    def test_mock_harness_wbs5_writes_new_metrics_without_http_or_gpu(self):
        # Synthetic adapter: small local strings, mocked receipts/timings/counters.
        # No workload HTTP request, tokenizer, GPU process or live inference.
        class Adapter:
            def health(self): return {"healthy": True}
            def snapshot(self): return {"/metrics": ""}
            def receipt(self, payload): return {"prompt_tokens": 126976}
            def stream_complete(self, payload):
                return {"choices": [{"finish_reason": "stop", "message": {"content": "local synthetic unit output"}}],
                        "usage": {"prompt_tokens": 126976, "completion_tokens": 1024},
                        "timings": {"prompt_per_second": 500, "predicted_per_second": 20}}, \
                       {"first_token_s": 10, "terminal_s": 20, "ttft_ms": 200, "wall_s": 10}
            def overlap_evidence(self, records): return {"resident": True, "active_overlap": True, "queue_only": False}
        manifest = runner.w.load_manifest(ROOT / c.WORKLOAD)
        workload = {"version": manifest["workload_id"], "mode": "performance", "context_tokens": 131072,
                    "source_manifest_sha256": h.sha(h.canon(manifest)), "sampling": manifest["sampling"],
                    "requests": [{"id": f"project-{x.lower()}", "project_id": x, "messages": [{"role": "user", "content": x}],
                                  "max_tokens": 4096, "min_output_tokens": 1024, "check": "nonempty"} for x in ("A", "B")]}
        p = plan(); config = runner.build_config(p, c.effective_environments(p["launch_plan"], {}))
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {}, clear=True), \
             patch.object(h, "GPUPeakProbe") as gpu, \
             patch("subprocess.run", side_effect=AssertionError("process called")), \
             patch.object(h.HTTPAdapter, "call", side_effect=AssertionError("HTTP called")):
            gpu.return_value.summary.return_value = {"peak_memory_mib": {0: 1000, 1: 1100}}
            raw = Path(td)
            self.assertEqual(h.run_batch(raw, config, workload, Adapter()), "PASS_C2_ACTIVE")
            metric = json.loads((raw / "metrics.json").read_text())
            self.assertEqual(metric["total_output_tokens"], 2048)
            self.assertEqual(metric["candidate_id"], p["candidate_id"])
            self.assertEqual(metric["mean_request_decode_tps"], 20)
            self.assertEqual(metric["aggregate_decode_tps"], 204.8)
            self.assertEqual(json.loads((raw / "speculative-evidence.json").read_text())["status"], "UNKNOWN")

    def test_metric_schema_total_tokens_and_unknown(self):
        p = plan(); config = runner.build_config(p, c.effective_environments(p["launch_plan"], {}))
        records = [{"request_id": "A", "actual_output_tokens": 1024, "decode_tps": 3.5},
                   {"request_id": "B", "actual_output_tokens": 2048, "decode_tps": 4.5}]
        result = e.metric_receipt(config, {}, records)
        self.assertEqual(result["total_output_tokens"], 3072)
        self.assertEqual(result["requests"][0]["decode_tps"], 3.5)
        for key in ("ttft_ms", "prefill_tps", "mean_request_decode_tps", "aggregate_decode_tps", "end_to_end_output_tps",
                    "batch_wall_s", "peak_vram_gpu0_mib", "peak_vram_gpu1_mib", "c2_active", "queue_only"):
            self.assertIsNone(result[key]); self.assertEqual(result["metric_status"][key], "UNKNOWN")
        records[1]["actual_output_tokens"] = None
        self.assertIsNone(e.metric_receipt(config, {}, records)["total_output_tokens"])

    def test_pre_run_receipt_and_telemetry_unknown_without_gpu(self):
        p = plan()
        receipt = e.pre_run_receipt(p, execute=lambda _: (_ for _ in ()).throw(FileNotFoundError("mock")))
        self.assertEqual(receipt["gpus"]["status"], "UNKNOWN")
        with self.assertRaises(ValueError):
            e.validate_pre_run(receipt)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "telemetry.jsonl"
            result = e.telemetry_summary(path)
            self.assertIsNone(result["0"]["power.draw"]["max"])
            sample = {"fields": e.GPU_FIELDS, "csv": "0,uuid,Tesla V100-SXM2-16GB,16384,1000,15384,65,200,1200,877,99\n"}
            path.write_text(json.dumps(sample) + "\n")
            result = e.telemetry_summary(path)
            self.assertEqual(result["0"]["power.draw"]["max"], 200)
            self.assertEqual(result["1"]["power.draw"]["status"], "UNKNOWN")

    def test_resolved_docker_environment_receipt_preserves_image_and_candidate_env(self):
        p = plan("ornith35-llama", "R3")
        config = runner.build_config(p, c.effective_environments(p["launch_plan"], {}))
        inspect = [{"Id": "sha256:pinned-test", "Config": {"Env": ["PATH=/image/bin", "BASE_IMAGE_VALUE=constant"]}}]
        receipt = e.environment_receipt(config, execute=lambda _: json.dumps(inspect))
        container = receipt["containers"][0]
        self.assertEqual(container["effective_environment"]["CUDA_SCALE_LAUNCH_QUEUES"], "4x")
        self.assertEqual(container["effective_environment"]["BASE_IMAGE_VALUE"], "constant")
        self.assertEqual(container["overrides"], {"CUDA_SCALE_LAUNCH_QUEUES": "4x"})

    def test_finalize_only_new_wbs5_directory_preserves_raw_server_log(self):
        with tempfile.TemporaryDirectory() as td:
            raw = Path(td); (raw / "runtime").mkdir()
            p = plan(); config = runner.build_config(p, c.effective_environments(p["launch_plan"], {}))
            h.save(raw / "runtime/planned-config.json", config)
            log = raw / "runtime/server-0.log"; log.write_text("raw log remains\n")
            original = log.read_bytes()
            e.finalize(raw)
            self.assertEqual(log.read_bytes(), original)
            result = json.loads((raw / "wbs5-evidence.json").read_text())
            self.assertIsNone(result["total_output_tokens"])
            self.assertEqual(json.loads((raw / "graph-evidence.json").read_text())["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
