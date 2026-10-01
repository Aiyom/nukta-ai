#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
MLX_LOG="$RUNTIME_DIR/mlx.log"
MLX_PID="$RUNTIME_DIR/mlx.pid"
IMAGE_LOG="$RUNTIME_DIR/image-worker.log"
IMAGE_PID="$RUNTIME_DIR/image-worker.pid"
MODEL="${MODEL:-mlx-community/Qwen3-8B-4bit}"
export MODEL

mkdir -p "$RUNTIME_DIR"

cleanup() {
  echo
  echo "Stopping stack..."
  cd "$ROOT_DIR"
  docker compose down || true
  if [ -f "$MLX_PID" ]; then
    PID="$(cat "$MLX_PID")"
    if kill -0 "$PID" >/dev/null 2>&1; then
      kill "$PID" || true
    fi
    rm -f "$MLX_PID"
  fi
  if [ -f "$IMAGE_PID" ]; then
    PID="$(cat "$IMAGE_PID")"
    if kill -0 "$PID" >/dev/null 2>&1; then
      kill "$PID" || true
    fi
    rm -f "$IMAGE_PID"
  fi
  echo "Stopped."
}

trap cleanup EXIT INT TERM

cd "$ROOT_DIR"
docker compose down >/dev/null 2>&1 || true

echo "Starting MLX backend on Apple GPU: $MODEL"
python3 -m mlx_lm server \
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

if ! curl -fsS http://127.0.0.1:8000/v1/models >/dev/null 2>&1; then
  echo "MLX backend did not start. Last log lines:"
  tail -80 "$MLX_LOG" || true
  exit 1
fi

echo "Starting local image worker..."
cd "$ROOT_DIR/image_worker"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8188 >"$IMAGE_LOG" 2>&1 &
echo "$!" > "$IMAGE_PID"
cd "$ROOT_DIR"

echo "Waiting for image worker..."
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8188/health >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$(cat "$IMAGE_PID")" >/dev/null 2>&1; then
    echo "Image worker exited before it became ready. Last log lines:"
    tail -80 "$IMAGE_LOG" || true
    exit 1
  fi
  sleep 1
done

if ! curl -fsS http://127.0.0.1:8188/health >/dev/null 2>&1; then
  echo "Image worker did not start. Last log lines:"
  tail -80 "$IMAGE_LOG" || true
  exit 1
fi

echo "Starting Docker API/UI..."
docker compose up --build -d

echo
echo "Ready: http://127.0.0.1:8080"
echo "Keep this terminal open. Press Ctrl+C here to stop API/UI and MLX."
echo

while true; do
  sleep 3600
done
