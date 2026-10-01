#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

OS="$(uname -s)"

if [ "$OS" != "Darwin" ]; then
  echo "This local Apple GPU profile is prepared for macOS."
  echo "On Linux/Windows, use server GPU backends and edit .env.docker endpoints."
fi

if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "Installing Node/Electron dependencies..."
npm install

echo "Installing MLX text backend..."
python3 -m pip install -U mlx-lm

echo "Installing local image worker dependencies..."
bash scripts/install_image_worker.sh

echo "Downloading configured models..."
python3 scripts/download_models.py

echo
echo "Setup complete."
echo "Run the app shell:"
echo "  npm run app"
echo
echo "Or run the local stack in Terminal:"
echo "  bash scripts/run_stack.sh"
