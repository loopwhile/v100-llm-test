#!/usr/bin/env bash
set -euo pipefail
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
container_name=${ONECAT_CONTAINER:-onecat-ornith35-r1}
model_path=${ONECAT_MODEL_PATH:-/srv/models/ornith-1.5-35b-a3b-nvfp4}
cache_path=${ONECAT_CACHE_PATH:-"$task_dir/cache"}
host_port=${ONECAT_PORT:-18080}

case "${1:-status}" in
  start)
    if docker container inspect "$container_name" >/dev/null 2>&1; then
      docker start "$container_name"
      exit 0
    fi
    test -f "$model_path/config.json"
    test -f "$task_dir/image-id.txt"
    image_id=$(cat "$task_dir/image-id.txt")
    mkdir -p "$cache_path"
    docker run -d --name "$container_name" \
      --gpus '"device=0,1"' \
      --user "$(id -u):$(id -g)" \
      --read-only --tmpfs /tmp:rw,exec,nosuid,nodev,size=4g,mode=1777 \
      --shm-size 8g --cap-drop ALL --security-opt no-new-privileges \
      --restart "${ONECAT_RESTART_POLICY:-unless-stopped}" --stop-timeout 60 \
      --health-cmd 'python -S -c "import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8080/health\", timeout=3)"' \
      --env FLASHINFER_WORKSPACE_BASE=/cache \
      --env TILELANG_CACHE_DIR=/cache/tilelang \
      --env TILELANG_TMP_DIR=/tmp/tilelang \
      --env XDG_CONFIG_HOME=/cache/config \
      --env VLLM_NO_USAGE_STATS=1 \
      --env CUDA_CACHE_PATH=/cache/nvidia \
      --env TORCH_EXTENSIONS_DIR=/cache/torch-extensions \
      --publish "127.0.0.1:$host_port:8080" \
      --mount "type=bind,src=$model_path,dst=/srv/models/ornith-1.5-35b-a3b-nvfp4,readonly" \
      --mount "type=bind,src=$cache_path,dst=/cache" \
      "$image_id" \
      --model /srv/models/ornith-1.5-35b-a3b-nvfp4 \
      --served-model-name Ornith-1.5-35B-A3B \
      --trust-remote-code --dtype half --attention-backend FLASH_ATTN_V100 \
      --tensor-parallel-size 2 --kv-cache-dtype fp8_e5m2 \
      --max-model-len 131072 --max-num-seqs 2 --max-num-batched-tokens 4096 \
      --gpu-memory-utilization 0.90 \
      --enable-auto-tool-choice --tool-call-parser qwen3_xml --reasoning-parser qwen3 \
      --host 0.0.0.0 --port 8080
    ;;
  stop) docker stop "$container_name" ;;
  restart) docker restart "$container_name" ;;
  logs) docker logs --tail 100 -f "$container_name" ;;
  status) docker ps -a --filter "name=^/${container_name}$" --format '{{.Names}}  {{.Status}}  {{.Ports}}' ;;
  health) curl --fail --silent --show-error "http://127.0.0.1:$host_port/health" ;;
  *) echo "Usage: $0 {start|stop|restart|logs|status|health}" >&2; exit 2 ;;
esac
