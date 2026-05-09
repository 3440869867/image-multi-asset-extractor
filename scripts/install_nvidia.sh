#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install -r requirements-gpu-nvidia.txt
./.venv/bin/python -m pip install -r requirements-ui.txt
./.venv/bin/python extract_assets.py --check-env

echo "NVIDIA setup complete. Run: ./.venv/bin/python app.py"
