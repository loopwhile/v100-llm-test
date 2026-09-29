#!/usr/bin/env bash
set -euo pipefail
cd /work
mkdir -p source build evidence
if [ ! -f source/CMakeLists.txt ]; then tar -xzf b10775.tar.gz -C source --strip-components=1; fi
patch --fuzz=0 -d source -p1 < b10775-sm70-gqa2.patch
{ nvcc --version; gcc --version; cmake --version; ninja --version; dpkg-query -W; } > evidence/toolchain.txt
cmake -S source -B build -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=70 \
 -DGGML_CUDA_GRAPHS=ON -DGGML_CUDA_FA_ALL_QUANTS=OFF -DGGML_NATIVE=ON \
 -DCMAKE_CUDA_FLAGS=-DGGML_CUDA_FATTN_VEC_GQA_HEADS=2 \
 -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DLLAMA_BUILD_TESTS=OFF \
 -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON \
 -DLLAMA_BUILD_NUMBER=10775 -DLLAMA_BUILD_COMMIT=67a17c17caa95742186f8b1ecadd1b5abd6d5ebb \
 2>&1 | tee evidence/configure.log
cmake --build build --parallel 4 --target llama-server 2>&1 | tee evidence/compile.log
sha256sum build/bin/* > evidence/binary-sha256.txt
cp build/CMakeCache.txt build/compile_commands.json evidence/
nm -C build/bin/libggml-cuda.so > evidence/candidate-cuda-symbols.txt
