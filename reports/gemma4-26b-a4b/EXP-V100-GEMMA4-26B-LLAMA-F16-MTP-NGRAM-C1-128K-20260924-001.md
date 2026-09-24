# EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C1-128K-20260924-001

## Result

- Verdict: **PASS_C1_128K**
- Model: Gemma4-26B-A4B-IT-QAT
- Weight: UD-Q4_K_XL
- KV: FP16
- Runtime: llama.cpp 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
- Topology: TP2 shared, layer split 1,1
- Speculation: **draft-mtp + ngram-simple**
- Draft artifact: smart Q4_0
- Draft depth: 4
- Draft devices: **CUDA0,CUDA1**

## Capacity receipt

- prompt: **129,024**
- reserved output: **2,048**
- total budget: **131,072 / 131,072**
- actual output: **818**
- finish_reason: `stop`
- truncated: 0
- post-health: healthy
- cleanup: container stopped, server exit 0

## Performance evidence

- TTFT: **249193.381 ms**
- prefill: **518.278 tok/s**
- decode: **45.533 tok/s**
- aggregate decode: **45.574 tok/s**
- batch wall: **267.151 s**
- peak VRAM: GPU0 **8,983 MiB**, GPU1 **9,121 MiB**

## Speculative evidence

- generated draft tokens: **1,088**
- accepted draft tokens: **548**
- acceptance: **50.368%**
- mean draft length: **3.01**

The composite lane is active and the full 128K request completed successfully.

## MTP vs MTP_NGRAM observation

Against corrected MTP-only C1 (`...MTP...-002`):

- prefill: **-1.65%**
- decode: **+0.10%**
- TTFT: **+1.68%**
- wall time: **+1.56%**
- GPU0 peak: unchanged
- GPU1 peak: **+20 MiB**
- MTP counters: exactly the same **548 / 1088**

This C1 workload does not establish an incremental NGRAM speed benefit. Per project policy, C1 only establishes compatibility/capacity/output integrity; NGRAM acceleration effectiveness is deferred to Phase 5.

## Semantic review

The response is coherent and complete. Its assertion that the storage code must provide ACID-style transaction atomicity/isolation is contract-dependent; this does not affect serving acceptance.

## Evidence

- Raw: `results/raw/EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C1-128K-20260924-001`
