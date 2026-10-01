#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
MLX_LOG="$RUNTIME_DIR/mlx.log"
MLX_PID="$RUNTIME_DIR/mlx.pid"
MODEL="${MODEL:-mlx-community/Qwen3-8B-4bit}"
export MODEL

mkdir -p "$RUNTIME_DIR"

if curl -fsS http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
  echo "MLX backend already running on 127.0.0.1:8000"
else
  echo "Starting MLX backend: $MODEL"
  nohup python3 -m mlx_lm server \
    --model "$MODEL" \
    --host 0.0.0.0 \
    --port 8000 \
    >"$MLX_LOG" 2>&1 &
  echo "$!" > "$MLX_PID"

  echo "Waiting for MLX backend..."
  for _ in $(seq 1 120); do
    if curl -fsS http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
      break
    fi
    if ! kill -0 "$(cat "$MLX_PID")" >/dev/null 2>&1; then
      echo "MLX backend exited before it became ready. Last log lines:"
      tail -80 "$MLX_LOG" || true
      exit 1
    fi
    sleep 1
  done
fi

sleep 2

if ! curl -fsS http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
  echo "MLX backend did not start. Last log lines:"
  tail -80 "$MLX_LOG" || true
  exit 1
fi

echo "Starting Docker API/UI..."
cd "$ROOT_DIR"
docker compose up --build -d

echo "Ready: http://127.0.0.1:8080"
echo "Stop everything with: bash scripts/docker_stop.sh"
