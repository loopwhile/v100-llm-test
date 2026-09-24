# Gemma4 26B-A4B MTP_NGRAM — previous disposition superseded

The earlier `UNSUPPORTED` disposition was based on the CUDA0-only MTP startup failure and is no longer the active conclusion.

A same-build, same-artifact, same-TP2, same-128K diagnostic changed only:

`--spec-draft-device CUDA0 -> CUDA0,CUDA1`

and produced **PASS_STARTUP**. Therefore MTP_NGRAM is reopened and must be tested after the corrected MTP C1 lane completes successfully.

No measured MTP_NGRAM result exists yet. Do not treat this file as a PASS row.
