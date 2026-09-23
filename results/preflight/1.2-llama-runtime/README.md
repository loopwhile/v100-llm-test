# WBS 1.2 — llama.cpp Runtime Verification

## Verdict

PASS

## Pinned runtime

- Family: `kyuz0/nvidia-v100-ai-toolboxes`
- OCI image digest: `sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149`
- llama.cpp build: `10775`
- Pinned commit: `67a17c17caa95742186f8b1ecadd1b5abd6d5ebb`
- Runtime-reported commit prefix: `67a17c17c`

## Identity verification

The locally installed OCI image exactly matches the pinned digest.

`llama-server --version` reports:

- version: `0.3.0-dev`
- build: `10775`
- commit prefix: `67a17c17c`

The runtime binary does not expose the full 40-character Git commit and the OCI image contains no separate llama.cpp revision label or build metadata containing it.

Therefore the runtime identity is verified by:

1. exact pinned OCI image digest,
2. exact build number `10775`,
3. runtime commit prefix `67a17c17c`, matching the pinned full revision.

No unsupported full-commit claim is made beyond the metadata exposed by the pinned image.

## CUDA userspace

Verified inside the pinned image:

- `cuda-cudart-12-6`: `12.6.77-1`
- `libcublas-12-6`: `12.6.4.1-1`

These match `config/runtime-lock.json`.

## Required llama.cpp features

Verified from the pinned `llama-server --help`:

- `--kv-unified`: supported
- `--kv-unified-per-slot`: supported
- `--spec-type none`: supported
- `ngram-simple`: supported
- `draft-mtp`: supported
- `--spec-draft-n-max`: supported

The `--spec-type` help explicitly defines the argument as a comma-separated list of speculative decoding types. Therefore the required composite lane syntax:

`draft-mtp,ngram-simple`

is supported by this runtime.

## Required lanes

The pinned runtime exposes the primitives required for:

- TARGET → `--spec-type none`
- NGRAM → `--spec-type ngram-simple`
- MTP → `--spec-type draft-mtp`
- MTP_NGRAM → `--spec-type draft-mtp,ngram-simple`

Whether a specific model artifact supports MTP remains a model/artifact compatibility question and is not implied solely by this runtime capability check.

## Evidence

- `image-check.txt`
- `llama-version.txt`
- `cuda-packages.txt`
- `llama-help.txt`
- `feature-check.txt`
- `image-labels.txt`
- `build-metadata-files.txt`
