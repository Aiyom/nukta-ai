#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

OS="$(uname -s)"

case "$OS" in
  Darwin)
    npm run app:build
    ;;
  Linux)
    echo "Linux packaging is not enabled for this local Apple GPU profile yet."
    echo "Use Docker/API with external GPU endpoints, then add electron-builder linux target."
    exit 1
    ;;
  MINGW*|MSYS*|CYGWIN*)
    echo "Windows packaging is not enabled for this local Apple GPU profile yet."
    echo "Use Docker/API with external GPU endpoints, then add electron-builder win target."
    exit 1
    ;;
  *)
    echo "Unsupported OS: $OS"
    exit 1
    ;;
esac
