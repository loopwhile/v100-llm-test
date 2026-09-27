# P520 optimized CPU-only llama.cpp image for WBS 6.9
#
# Purpose:
# - keep the WBS6 coexistence envelope (4 physical CPU cores, no CUDA)
# - build the experimental OpenVINO CPU backend
# - compile OpenBLAS and LTO into the same image
# - retain native x86 code generation for the fallback/native CPU backend
#
# IMPORTANT: WBS 6.9 must prove OpenVINO is actually active from runtime
# evidence. The runner MUST NOT silently accept native-GGML fallback.

ARG OPENVINO_VERSION_MAJOR=2026.3.1
ARG OPENVINO_VERSION_FULL=2026.3.1.22476.56d9685302d
ARG UBUNTU_VERSION=24.04

FROM ubuntu:${UBUNTU_VERSION} AS builder

ARG OPENVINO_VERSION_MAJOR
ARG OPENVINO_VERSION_FULL
ARG LLAMA_COMMIT=67a17c17caa95742186f8b1ecadd1b5abd6d5ebb

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    git \
    libopenblas-dev \
    libssl-dev \
    libtbb12 \
    ninja-build \
    ocl-icd-opencl-dev \
    opencl-headers \
    opencl-clhpp-headers \
    pkg-config \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/intel && \
    wget -q -O /tmp/openvino.tgz \
      "https://storage.openvinotoolkit.org/repositories/openvino/packages/${OPENVINO_VERSION_MAJOR}/linux/openvino_toolkit_ubuntu24_${OPENVINO_VERSION_FULL}_x86_64.tgz" && \
    tar -xf /tmp/openvino.tgz -C /opt/intel && \
    mv "/opt/intel/openvino_toolkit_ubuntu24_${OPENVINO_VERSION_FULL}_x86_64" \
       "/opt/intel/openvino_${OPENVINO_VERSION_MAJOR}" && \
    ln -s "/opt/intel/openvino_${OPENVINO_VERSION_MAJOR}" /opt/intel/openvino && \
    rm -f /tmp/openvino.tgz

ENV OpenVINO_DIR=/opt/intel/openvino

RUN git clone https://github.com/ggml-org/llama.cpp /src && \
    cd /src && \
    git checkout "${LLAMA_COMMIT}"

RUN bash -c 'source "${OpenVINO_DIR}/setupvars.sh" && \
    cd /src && \
    cmake -B build/opt -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DLLAMA_BUILD_TESTS=OFF \
      -DLLAMA_BUILD_EXAMPLES=OFF \
      -DGGML_NATIVE=OFF \
      -DGGML_LTO=ON \
      -DGGML_CUDA=OFF \
      -DGGML_BACKEND_DL=ON \
      -DGGML_CPU_ALL_VARIANTS=ON \
      -DGGML_BLAS=ON \
      -DGGML_BLAS_VENDOR=OpenBLAS \
      -DGGML_OPENVINO=ON && \
    cmake --build build/opt --parallel 4 --target llama-server'

RUN mkdir -p /dist/bin /dist/lib && \
    cp /src/build/opt/bin/llama-server /dist/bin/ && \
    find /src/build/opt -name '*.so*' -exec cp -P {} /dist/lib/ \; && \
    find "${OpenVINO_DIR}/runtime/lib/intel64" -name '*.so*' -exec cp -P {} /dist/lib/ \;

FROM ubuntu:${UBUNTU_VERSION}

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libgomp1 \
    libopenblas0-pthread \
    libstdc++6 \
    libtbb12 \
    ocl-icd-libopencl1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /dist/bin/ /app/
COPY --from=builder /dist/lib/ /app/

ENV LD_LIBRARY_PATH=/app
ENV GGML_OPENVINO_DEVICE=CPU

WORKDIR /app
# Health is verified by the WBS 6.9 runner on the configured host port.
# Do not bake a fixed-port Docker HEALTHCHECK into this reusable image.
ENTRYPOINT ["/app/llama-server"]
