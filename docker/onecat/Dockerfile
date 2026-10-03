# P520's validated Python and packages are copied into the image, not mounted.
FROM nvidia/cuda:12.8.1-base-ubuntu24.04@sha256:133c78a0575303be34164d0b90137a042172bdf60696af01a3c424ab402d86e2

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libnuma1 libgomp1 libstdc++6 gcc g++ make ninja-build \
    && rm -rf /var/lib/apt/lists/* \
    && groupmod --new-name loopwhile ubuntu \
    && usermod --login loopwhile --home /home/loopwhile --move-home ubuntu

# Keep the original absolute paths to preserve uv symlinks and console scripts.
COPY python/ /home/loopwhile/.local/share/uv/python/cpython-3.12.14-linux-x86_64-gnu/
RUN ln -s cpython-3.12.14-linux-x86_64-gnu /home/loopwhile/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu
COPY venv/ /home/loopwhile/qwen3.8-bench-runtime/venv/
COPY runtime_hooks/ /opt/onecat/runtime_hooks/
COPY runtime-receipt.json /opt/onecat/runtime-receipt.json

ENV PATH=/home/loopwhile/qwen3.8-bench-runtime/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 \
    PYTHONPATH=/opt/onecat/runtime_hooks \
    PYTHONDONTWRITEBYTECODE=1 \
    CUDA_VISIBLE_DEVICES=0,1 \
    VLLM_SM70_FLASHQLA_ORIGINAL_PREFILL=0 \
    XDG_CACHE_HOME=/cache \
    HF_HOME=/cache/huggingface \
    VLLM_CACHE_ROOT=/cache/vllm \
    TRITON_CACHE_DIR=/cache/triton \
    TORCHINDUCTOR_CACHE_DIR=/cache/torchinductor \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

USER 1000:1000
WORKDIR /home/loopwhile
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15m --retries=3 \
    CMD python -S -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
ENTRYPOINT ["/home/loopwhile/qwen3.8-bench-runtime/venv/bin/python", "-m", "vllm.entrypoints.openai.api_server"]
