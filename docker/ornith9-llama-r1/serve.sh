#!/usr/bin/env bash
set -euo pipefail
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
model_path=/srv/models/ornith-1.5-9b-mtp-gguf/Ornith-1.5-9B-MTP-Q6_K.gguf
backend_image=kyuz0/nvidia-v100-ai-toolboxes@sha256:e8bf2d9a1b9e2915c5848470fc85ce1cfd4503776f13c56a12b98d2bf30ac149
gateway_image=ghcr.io/berriai/litellm@sha256:d295634e09c648dcdb72c4cc2dd226f5fb87823a73e88cbbed6f205e4deb044b
prefix=ornith9-llama-r1

case "${1:-status}" in
  start)
    test -f "$model_path"
    test -f "$task_dir/litellm-config.yaml"
    for gpu in 0 1; do
      name="$prefix-backend-$gpu"
      if docker container inspect "$name" >/dev/null 2>&1; then
        docker start "$name"
      else
        docker run -d --pull=never --name "$name" \
          --label project=v100-llm-test --label operation=ornith9-llama-r1 \
          --restart unless-stopped --stop-timeout 60 \
          --gpus "device=$gpu" -p "127.0.0.1:$((19080 + gpu)):8080" \
          -v "$model_path:/model/target.gguf:ro" \
          --entrypoint llama-server "$backend_image" \
          -m /model/target.gguf --alias Ornith-1.5-9B --host 0.0.0.0 --port 8080 \
          -ngl all --ctx-size 131072 --parallel 1 --kv-unified \
          --kv-unified-per-slot 131072 --batch-size 512 --ubatch-size 256 \
          --cache-type-k f16 --cache-type-v f16 --flash-attn on \
          --spec-type none --jinja --reasoning off --metrics --slots --no-warmup
      fi
    done
    name="$prefix-gateway"
    if docker container inspect "$name" >/dev/null 2>&1; then
      docker start "$name"
    else
      docker run -d --pull=never --name "$name" \
        --label project=v100-llm-test --label operation=ornith9-llama-r1 \
        --restart unless-stopped --stop-timeout 60 --network host \
        -v "$task_dir/litellm-config.yaml:/app/config.yaml:ro" "$gateway_image" \
        --config /app/config.yaml --host 127.0.0.1 --port 18079
    fi
    ;;
  stop)
    docker stop "$prefix-gateway" "$prefix-backend-0" "$prefix-backend-1"
    ;;
  status)
    docker ps -a --filter "label=operation=ornith9-llama-r1" \
      --format '{{.Names}}  {{.Status}}  {{.Ports}}'
    ;;
  health)
    for port in 19080 19081; do
      curl --fail --silent --show-error "http://127.0.0.1:$port/health"
      echo
    done
    curl --fail --silent --show-error http://127.0.0.1:18079/v1/models
    echo
    ;;
  logs) docker logs --tail 100 -f "$prefix-${2:-gateway}" ;;
  *) echo "Usage: $0 {start|stop|status|health|logs [gateway|backend-0|backend-1]}" >&2; exit 2 ;;
esac
