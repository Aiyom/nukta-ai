#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-mlx-community/Qwen3-8B-4bit}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

python3 -m mlx_lm server --model "$MODEL" --host "$HOST" --port "$PORT"
