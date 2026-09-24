# Gemma4 26B-A4B MTP_NGRAM — historical unsupported disposition superseded

The earlier `UNSUPPORTED` disposition was based on the CUDA0-only MTP startup failure.

Subsequent isolation showed that changing only:

`--spec-draft-device CUDA0 -> CUDA0,CUDA1`

produced startup PASS on the same b10775 / TP2 / 128K / artifact configuration.

The corrected composite lane was then measured:

- experiment: `EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-NGRAM-C1-128K-20260924-001`
- verdict: **PASS_C1_128K**
- draft accepted/generated: **548 / 1088 (50.368%)**
- decode: **45.53 tok/s**
- peak VRAM: **8983 / 9121 MiB**

Therefore `MTP_NGRAM` is supported under the validated dual-draft-device contract. This file is retained only to document that the previous unsupported conclusion was superseded.
