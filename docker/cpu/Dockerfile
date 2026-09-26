# P520 Intel Xeon W-2135 Native CPU-only llama.cpp Dockerfile
# Contract: WBS 6.1 (GGML_NATIVE=ON, GGML_CUDA=OFF, native single CPU backend)

FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

ARG LLAMA_COMMIT=67a17c17caa95742186f8b1ecadd1b5abd6d5ebb
ARG USE_OPENBLAS=0

RUN git clone https://github.com/ggerganov/llama.cpp /src && \
    cd /src && \
    git checkout ${LLAMA_COMMIT} && \
    if [ "${USE_OPENBLAS}" = "1" ]; then \
        BLAS_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"; \
    else \
        BLAS_ARGS="-DGGML_BLAS=OFF"; \
    fi && \
    cmake -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DGGML_NATIVE=ON \
        -DGGML_CUDA=OFF \
        -DGGML_BACKEND_DL=OFF \
        -DGGML_CPU_ALL_VARIANTS=OFF \
        ${BLAS_ARGS} && \
    cmake --build build --config Release -j 4 --target llama-server && \
    mkdir -p /dist/bin /dist/lib && \
    cp build/bin/llama-server /dist/bin/ && \
    cp -a build/bin/lib*.so* /dist/lib/

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libstdc++6 \
    libopenblas0-pthread \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /dist/bin/ /usr/local/bin/
COPY --from=builder /dist/lib/ /usr/local/lib/
RUN echo "/usr/local/lib" > /etc/ld.so.conf.d/local.conf && ldconfig

ENTRYPOINT ["/usr/local/bin/llama-server"]
