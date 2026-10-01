#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Docker services:"
cd "$ROOT_DIR"
docker compose ps

echo
echo "API health:"
curl -fsS http://127.0.0.1:8080/health || true

echo
echo
echo "MLX models:"
curl -fsS http://127.0.0.1:8000/v1/models || true

echo
echo
echo "Image worker:"
curl -fsS http://127.0.0.1:8188/health || true
