#!/usr/bin/env bash
# Recorded WBS7.0 commands. Run only in a fresh isolated remote directory.
# SOURCE archive URL/hash and patch identity: ../source/provenance.json
set -euo pipefail
cd /home/loopwhile/v100-wbs7-preflight-20260929
docker build -f Dockerfile.builder -t wbs7-gqa2-builder:20260929-nccl .
docker image inspect wbs7-gqa2-builder:20260929-nccl > builder-image-inspect.json
docker run --rm --name wbs7-gqa2-build \
 --mount type=bind,src=/home/loopwhile/v100-wbs7-preflight-20260929,dst=/work \
 wbs7-gqa2-builder:20260929-nccl /work/build-candidate.sh
# After the successful build, package isolated binaries into the unchanged base runtime.
docker build -f Dockerfile.runtime -t wbs7-qwen-gqa2:b10775-20260929 .
docker image inspect wbs7-qwen-gqa2:b10775-20260929 > candidate-image-inspect.json
# Help/version only; --gpus supplies libcuda.so.1, never a model or generation.
docker run --rm --gpus all wbs7-qwen-gqa2:b10775-20260929 --version
docker run --rm --gpus all wbs7-qwen-gqa2:b10775-20260929 --spec-type none --help
