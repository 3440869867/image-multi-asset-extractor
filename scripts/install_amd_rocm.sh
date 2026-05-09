#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pip install -r requirements-amd-rocm.txt
./.venv/bin/python -m pip install -r requirements-ui.txt
./.venv/bin/python extract_assets.py --check-env --allow-cpu

echo "AMD ROCm setup complete. Run: ./.venv/bin/python app.py and choose amd-rocm."
