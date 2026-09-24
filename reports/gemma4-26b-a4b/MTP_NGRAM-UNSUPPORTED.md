# Gemma4 26B-A4B MTP_NGRAM — UNSUPPORTED on pinned llama.cpp runtime

The required composite row remains explicit, but no measured experiment is fabricated.

- Model: Gemma4-26B-A4B-IT-QAT
- Runtime: llama.cpp 10775 / 67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
- Required composite: `draft-mtp,ngram-simple`
- MTP dependency: explicit `gemma4-assistant` companion GGUF
- Disposition: **UNSUPPORTED**
- Reason: the exact MTP dependency fails during server startup before a request can be measured.

Parent evidence:
`EXP-V100-GEMMA4-26B-LLAMA-F16-MTP-C1-128K-20260924-001` → `FAIL_STARTUP`, server exit 139.

NGRAM alone is supported and separately passed C1 128K. Adding NGRAM cannot bypass the failed assistant-model initialization that is required by the composite lane. Therefore a redundant MTP_NGRAM crash replay is not scheduled.

This is an explicit support disposition, not a measured C1 PASS/FAIL row and not evidence about a future llama.cpp build.
