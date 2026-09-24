# EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C1-128K-20260924-001

## Result

- Verdict: **PASS_C1_128K**
- Model: Gemma4-26B-A4B-IT-QAT
- Weight: UD-Q4_K_XL
- KV: FP16
- Runtime: llama.cpp 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
- Topology: TP2 shared
- Speculation: target-only

## Capacity receipt

- prompt: **129,024**
- reserved output: **2,048**
- total budget: **131,072 / 131,072**
- actual output: **736**
- finish_reason: `stop`
- truncated: 0
- post-health: healthy
- cleanup: container stopped, server exit 0

## Performance evidence

- TTFT: **246184.042 ms**
- prefill: **524.637 tok/s**
- decode: **68.101 tok/s**
- aggregate decode: **68.117 tok/s**
- batch wall: **256.998 s**
- peak VRAM: GPU0 **8,775 MiB**, GPU1 **8,785 MiB**

## Semantic review

The response is coherent and complete. It assumes that Transaction.commit must provide ACID-style atomicity/isolation; that contract is not established by the capacity workload, so the severity conclusion is contract-dependent. This is recorded as model-quality evidence only and does not affect serving/output-integrity acceptance.

## Evidence

- Raw: `results/raw/EXP-V100-GEMMA4-26B-LLAMA-F16-TARGET-C1-128K-20260924-001`
