#!/usr/bin/env bash
set -euo pipefail

MODEL_ID="${1:-}"
if [ -z "$MODEL_ID" ]; then
  echo "Usage: bash scripts/download_model.sh <huggingface-model-id>"
  echo "Example: bash scripts/download_model.sh mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CACHE_DIR="${HF_HOME:-$ROOT_DIR/.runtime/huggingface}"

mkdir -p "$CACHE_DIR"

echo "Downloading model metadata/files for: $MODEL_ID"
echo "Cache: $CACHE_DIR"
echo

python3 -m pip install --quiet --upgrade huggingface_hub
HF_HOME="$CACHE_DIR" python3 -m huggingface_hub download "$MODEL_ID"

echo
echo "Done. To run MLX with this model:"
echo "MODEL=\"$MODEL_ID\" bash scripts/run_stack.sh"
