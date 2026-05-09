# Contributing

Thanks for improving Image Multi Asset Extractor.

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-cpu.txt
pip install -r requirements-ui.txt
pip install -r requirements-gpu-nvidia.txt
pip install -r requirements-amd-directml.txt
```

CPU mode is intended to work across Windows, Linux, macOS, and Docker.
NVIDIA CUDA is the most reliable GPU path. AMD support is best-effort through DirectML on Windows or ROCm on Linux.

## Pull Request Checklist

- Keep the tool standalone; do not couple it to Open Word Studio.
- Do not commit generated PNGs, local sprite sheets, model files, or `.venv`.
- Run `python extract_assets.py --check-env`.
- Run `python -m py_compile extract_assets.py app.py`.
- Add or update README/docs when behavior changes.
