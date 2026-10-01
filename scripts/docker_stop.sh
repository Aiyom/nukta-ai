#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
MLX_PID="$RUNTIME_DIR/mlx.pid"
IMAGE_PID="$RUNTIME_DIR/image-worker.pid"

cd "$ROOT_DIR"
docker compose down

if [ -f "$MLX_PID" ]; then
  PID="$(cat "$MLX_PID")"
  if kill -0 "$PID" >/dev/null 2>&1; then
    echo "Stopping MLX backend pid $PID"
    kill "$PID"
  fi
  rm -f "$MLX_PID"
fi

if [ -f "$IMAGE_PID" ]; then
  PID="$(cat "$IMAGE_PID")"
  if kill -0 "$PID" >/dev/null 2>&1; then
    echo "Stopping image worker pid $PID"
    kill "$PID"
  fi
  rm -f "$IMAGE_PID"
fi

echo "Stopped Docker API/UI, managed MLX backend, and image worker."
