#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m pip install -r "$ROOT_DIR/image_worker/requirements.txt"
