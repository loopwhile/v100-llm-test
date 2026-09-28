# WBS 5.3.3.5 — Ornith 1.5 35B-A3B / llama.cpp track result review

Review date: 2026-09-29

## 1. Scope and authoritative evidence

This review performs **no GPU inference**. It closes the frozen WBS5 Ornith 1.5 35B-A3B / llama.cpp track using the already-published `performance/v1.json` raw artifacts.

Authoritative measured runs:

| Candidate | Experiment | Verdict |
|---|---|---|
| R0 `ORN35-LLAMA-WBS5-R0-TARGET` | `EXP-V100-WBS5-ORNITH35-LLAMA-R0-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R1 `ORN35-LLAMA-WBS5-R1-MTP1` | `EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002` | `PASS_C2_ACTIVE` |
| R2 `ORN35-LLAMA-WBS5-R2-UB256` | `EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001` | `PASS_C2_ACTIVE` |
| R3 `ORN35-LLAMA-WBS5-R3-QUEUE4X` | `EXP-V100-WBS5-ORNITH35-LLAMA-R3-PERF-20260928-001` | `PASS_C2_ACTIVE` |

R1의 최초 `EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-001`은 measured request 전에 port conflict로 끝난 `INCONCLUSIVE` infrastructure-invalid attempt다. Raw는 보존하지만 performance comparison에는 사용하지 않는다. 사용자 승인으로 같은 frozen configuration을 fresh ID `-002`에서 재실행했고, retry provenance는 raw/report에 기록되어 있다.

Frozen one-variable deltas:

- R1: R0에서 `--spec-type none -> draft-mtp` 및 model-fixed `--spec-draft-n-max 1`만 변경.
- R2: R0에서 `--ubatch-size 128 -> 256`만 변경. `--batch-size 512` 유지.
- R3: R0에서 container environment `CUDA_SCALE_LAUNCH_QUEUES=4x`만 추가.
- R1+R2 조합, MTP n=2, NGRAM, graph-off, P2P 강제 등 새 candidate는 이 review에서 만들거나 추정하지 않는다.

Evidence roots:

- R0: [raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R0-PERF-20260928-001/) / [report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R0-PERF-20260928-001.md)
- R1: [raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002/) / [report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002.md)
- R2: [raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/) / [report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001.md)
- R3: [raw](../results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R3-PERF-20260928-001/) / [report](../reports/ornith-1.5-35b-a3b/EXP-V100-WBS5-ORNITH35-LLAMA-R3-PERF-20260928-001.md)

## 2. Metric semantics

The result interpretation preserves the harness definitions.

- Per-request prefill TPS uses llama.cpp `timings.prompt_per_second` when present. These four runs have runtime timings, so the reported prefill values are not reconstructed as prompt tokens / TTFT.
- Per-request decode TPS uses llama.cpp `timings.predicted_per_second` when present.
- `mean_request_decode_tps` is the arithmetic mean of the two request-level runtime decode TPS values.
- `aggregate_decode_tps` is total output tokens divided by `latest request end - earliest first content`.
- `end_to_end_output_tps` is total output tokens divided by the full synchronized batch wall time.

Because the shared layer-split server processes the two 128K prompts mostly serially before the common decode tail, the B-request decode timing and aggregate decode window include substantial scheduling/prefill interaction. Therefore aggregate decode and mean request decode are **not pure decode-kernel benchmarks** and output-length differences must not be ignored.

## 3. Common identity and invariant

- Model repository: `ornith-ai/Ornith-1.5-35B-A3B-GGUF`
- Revision: `12393612fd4f730ff5aadc23e9b8f9648aa49ceb`
- Artifact: `/srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf`
- SHA256: `42739874cc2ccfdb8523b23fbe52e29b2a7555c8176737ca9ca0b5d59859d41f`
- Weight: Q4_K_M
- KV: Q8_0 K/V
- Runtime: llama.cpp build 10775 / commit `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`
- OCI: `kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`
- Hardware: 2× Tesla V100-SXM2-16GB
- Repository topology name: `tp2-shared`
- Actual llama.cpp split: `--split-mode layer --tensor-split 1,1`; this is a two-GPU layer/model split, not tensor-parallel all-reduce.
- `-ngl all --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072`
- `--flash-attn on --jinja --reasoning off --metrics --slots --no-warmup`
- Workload: `V100-PERFORMANCE-C2-128K-v1`, SHA256 `e413acced27c1991d76ce2b2df195ff73ce2b4f45853b9676e5b9000ef8503ca`
- Two independent projects, 131072 target context/request, 4096 output reserve, minimum output 1024/request.
- Prefix cache lane: cold-independent.
- Measured repetition: one valid measured execution per frozen candidate; no automatic repetition.

## 4. Measured comparison

| Metric | R0 TARGET | R1 MTP1 | R2 UB256 | R3 QUEUE4X |
|---|---:|---:|---:|---:|
| TTFT mean | 791.438 s | 833.067 s | **670.091 s** | 791.615 s |
| Prefill | 191.416 tok/s | 182.785 | **229.750** | 191.380 |
| Request A decode | 28.130 tok/s | **31.985** | 26.995 | 28.100 |
| Request B decode | 2.681 tok/s | 2.674 | 4.398 | 2.681 |
| Mean request decode | 15.406 tok/s | **17.329** | 15.697 | 15.390 |
| Aggregate decode | 5.400 tok/s | 5.709 | **7.228** | 5.399 |
| End-to-end output | 3.218 tok/s | 3.432 | **4.505** | 3.218 |
| Batch wall | 1176.326 s | 1242.844 s | **1038.990 s** | 1176.659 s |
| Output tokens A/B | 1930 / 1856 | 2313 / 1952 | 1832 / 2849 | 1930 / 1856 |
| Peak VRAM GPU0/GPU1 | 12831 / 12309 MiB | 12897 / 13737 | 13103 / 12581 | 12831 / 12309 |
| Spec acceptance | N/A | **1838 / 2426 = 75.76%** | N/A | N/A |

R0-relative observed deltas:

- R1: TTFT +5.26%, prefill -4.51%, mean request decode +12.49%, request-A decode +13.70%, request-B decode -0.28%, batch wall +5.65%, peak VRAM +66 MiB GPU0 / +1428 MiB GPU1.
- R2: TTFT -15.33%, prefill +20.03%, mean request decode +1.89%, request-A decode -4.03%, request-B decode +64.00%, batch wall -11.68%, peak VRAM +272 MiB on each GPU.
- R3: TTFT +0.022%, prefill -0.019%, mean request decode -0.101%, aggregate decode -0.033%, end-to-end -0.028%, batch wall +0.028%, identical peak VRAM.

The R2 aggregate/E2E gains are not treated as pure decode improvements: R2 generated 4681 total output tokens versus R0's 3786, and the mixed aggregate window is shortened by faster prefill/scheduling. The robust R2 claim is the large runtime-reported prefill/TTFT improvement and shorter batch wall, not a decode-kernel speedup.

## 5. Capacity / stability

All four authoritative candidates:

- completed as `PASS_C2_ACTIVE`;
- recorded resident/active overlap true and queue-only false;
- completed both requests above the 1024-token minimum;
- remained post-health healthy;
- had no OOM, capacity failure, runtime crash or server-health failure.

The R1 `-001` port-conflict attempt is excluded from this statement because no measured request was admitted.

## 6. Output integrity

All authoritative R0/R1/R2/R3 requests have mechanical output verdict `PASS` and `finish_reason=stop`.

R0 and R3 are an especially clean A/B pair:

- prompt token counts are identical;
- output token counts are identical (1930 / 1856);
- both generated response texts are byte-for-byte identical;
- launch configuration differs only by the verified R3 container environment variable.

R1 and R2 generated different output lengths/trajectories. WBS5 `performance/v1` does not have the WBS3 pre-registered semantic oracle, so this review does not claim semantic-quality superiority among candidates. Recipe validation here is bounded to the WBS5 serving/performance/output-integrity contract.

## 7. R1 — native MTP1 interpretation

R1 intended to increase sustained generation throughput using the embedded one-layer native MTP predictor with depth 1.

Observed:

- speculative counters are active: 2426 draft / 1838 accepted, 75.76% acceptance;
- request A runtime decode improves 28.130 -> 31.985 tok/s (+13.70%);
- request B decode is effectively unchanged, 2.681 -> 2.674 tok/s (-0.28%);
- mean request decode improves +12.49%;
- prefill falls -4.51%, TTFT rises +5.26%, and batch wall rises +5.65%;
- GPU1 peak rises by 1428 MiB.

This is evidence of a **real decode-oriented MTP effect**, but not an overall latency win for the 128K×2 workload. Acceptance ratio is supportive diagnostic evidence, not a throughput metric by itself.

Decision: **promote R1 as `VALIDATED_RECIPE — DECODE_ORIENTED`**. It is appropriate when post-prefill generation throughput is the priority and the higher prefill latency/VRAM cost is acceptable. No MTP n=2 candidate is inferred or added.

## 8. R2 — UB256 interpretation

R2 changes only the physical microbatch limit from 128 to 256 while retaining logical batch 512.

Observed:

- prefill rises 191.416 -> 229.750 tok/s (+20.03%);
- TTFT falls 791.438 -> 670.091 s (-15.33%);
- batch wall falls 1176.326 -> 1038.990 s (-11.68%) despite a longer generated output total;
- peak VRAM increases by only 272 MiB/GPU;
- request A decode is -4.03% while request B decode is +64.00%, so the +1.89% mean request decode change must not be presented as a decode-kernel improvement.

Server prompt-progress logs retain the same broad behavior: one 128K prompt consumes almost the full first prefill interval before the second prompt advances materially. R2 improves physical prompt-processing efficiency inside that scheduling structure; it does not demonstrate a new fairness/interleaving policy.

Decision: **promote R2 as `VALIDATED_RECIPE — LONG_PREFILL_LATENCY_ORIENTED`**. Its validated value is the strong long-context prefill/TTFT/wall improvement with modest additional VRAM.

## 9. R3 — launch queue interpretation

R3 intended to improve multi-GPU layer-split prompt processing through `CUDA_SCALE_LAUNCH_QUEUES=4x`.

The variable was actually delivered to the container:

- `runtime/effective-environment.json` records `CUDA_SCALE_LAUNCH_QUEUES=4x` in the effective environment.
- Graph reuse evidence exists for both R0 and R3; both record server-lifetime reuse count 4992 (the evidence scope is not measured-window-only).

R3 and R0 are essentially identical: all core metrics are within about 0.1%, peak VRAM is identical, and generated text is identical.

Decision: **branch closed — no measurable benefit; do not promote R3 as a final recipe**. No queue multiplier sweep is added.

## 10. Topology behavior

The measured topology claim remains bounded to what raw evidence proves:

- two 131072-context slots can be resident and reach active decode overlap;
- queue-only is false;
- R0/R2/R3 server logs show the 128K prefill phases are nevertheless effectively serialized;
- the logical project label `tp2-shared` must not be described as tensor-parallel all-reduce because the actual command is llama.cpp layer split.

Approximate common decode-overlap windows from request timestamps are ~59.3s (R0), ~54.8s (R1), ~67.8s (R2), and ~59.4s (R3). These values describe the measured request lifetimes, not GPU kernel concurrency.

## 11. Power / temperature / clocks

No candidate shows evidence that the primary performance differences came from thermal or obvious clock-state failure.

Observed sampled maxima:

| Candidate | GPU0/GPU1 power max | GPU0/GPU1 temp max | SM clock range | Memory clock |
|---|---:|---:|---:|---:|
| R0 | 141.43 / 137.38 W | 62 / 56 C | 135–1200 MHz | 877 MHz |
| R1 | 129.15 / 129.62 W | 59 / 56 C | 135–1200 MHz | 877 MHz |
| R2 | 138.32 / 138.79 W | 62 / 56 C | 135–1200 MHz | 877 MHz |
| R3 | 137.28 / 135.02 W | 61 / 56 C | 135–1200 MHz | 877 MHz |

Telemetry stores sampled min/max rather than a normalized energy-per-token measurement, so this review does not rank candidates by power efficiency.

## 12. Final recipe records

### R1 — VALIDATED_RECIPE / DECODE_ORIENTED

- Candidate: `ORN35-LLAMA-WBS5-R1-MTP1`
- Experiment: `EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002`
- Weight/KV: Q4_K_M / Q8_0 K/V
- Speculative: embedded native MTP, `--spec-draft-n-max 1`; no companion GGUF
- Topology: 2-GPU shared llama.cpp layer split 1,1
- Context/concurrency: 131072 per slot, 2 slots, ctx-size 262144
- Batch/ubatch: 512 / 128
- Graph: pinned runtime default; graph reuse evidence observed, no graph-off override
- Relevant environment override: none
- Output integrity: PASS
- Capacity/stability: PASS_C2_ACTIVE
- Peak VRAM: 12897 / 13737 MiB
- Limitation: improves active generation but worsens 128K prefill/TTFT/wall; single measured execution; WBS5 has no semantic oracle; no evidence that R1+R2 effects are additive.

Measured exact launch command:

```sh
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5/e2e2e97450cb/results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002/runtime/container-0.cid --label experiment=EXP-V100-WBS5-ORNITH35-LLAMA-R1-PERF-20260928-002 --rm --pull=never --name exp-v100-wbs5-ornith35-llama-r1-perf-20260928-002-backend-0 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 128 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type draft-mtp --spec-draft-n-max 1 --jinja --reasoning off --metrics --slots --no-warmup
```

### R2 — VALIDATED_RECIPE / LONG_PREFILL_LATENCY_ORIENTED

- Candidate: `ORN35-LLAMA-WBS5-R2-UB256`
- Experiment: `EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001`
- Weight/KV: Q4_K_M / Q8_0 K/V
- Speculative: none
- Topology: 2-GPU shared llama.cpp layer split 1,1
- Context/concurrency: 131072 per slot, 2 slots, ctx-size 262144
- Batch/ubatch: 512 / 256
- Graph: pinned runtime default; graph reuse evidence observed, no graph-off override
- Relevant environment override: none
- Output integrity: PASS
- Capacity/stability: PASS_C2_ACTIVE
- Peak VRAM: 13103 / 12581 MiB
- Limitation: validated advantage is long-prefill latency/throughput, not pure decode speed; single measured execution; WBS5 has no semantic oracle; no evidence that R1+R2 effects are additive.

Measured exact launch command:

```sh
docker run --cidfile /home/loopwhile/v100-llm-test-wbs5/e2e2e97450cb/results/raw/EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001/runtime/container-0.cid --label experiment=EXP-V100-WBS5-ORNITH35-LLAMA-R2-PERF-20260928-001 --rm --pull=never --name exp-v100-wbs5-ornith35-llama-r2-perf-20260928-001-backend-0 --label project=v100-llm-test --gpus '"device=0,1"' -p 127.0.0.1:18080:8080 -v /srv/models/ornith-1.5-35b-a3b-gguf/Ornith-1.5-35B-Q4_K_M.gguf:/model/target.gguf:ro --entrypoint llama-server kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149 -m /model/target.gguf --host 0.0.0.0 --port 8080 -ngl all --split-mode layer --tensor-split 1,1 --ctx-size 262144 --parallel 2 --kv-unified --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
```

## 13. Track closeout

Final track decision:

- R0: canonical measured reference baseline; not promoted as an optimization recipe.
- R1: **VALIDATED_RECIPE — DECODE_ORIENTED**.
- R2: **VALIDATED_RECIPE — LONG_PREFILL_LATENCY_ORIENTED**.
- R3: **CLOSED — NO MEASURABLE BENEFIT**.
- No overall winner is declared because WBS 5.5 explicitly allows workload-oriented recipes instead of one universal winner.
- R1+R2 additivity is unverified. This review does not schedule or imply a combined measurement.
- No new candidate is added.
- No additional GPU inference is required by WBS 5.3.3.5.

WBS 5.3.3.5 status: **DONE**.
