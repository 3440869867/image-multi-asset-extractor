# NVIDIA CUDA Notes

Image Multi Asset Extractor is designed for NVIDIA CUDA GPU acceleration when background removal is enabled.

## Supported GPU Mode

- NVIDIA GPU with a recent driver.
- CUDA-compatible runtime through `onnxruntime-gpu`.
- `rembg[gpu]` installed.

## Other GPU Backends

AMD support is best-effort outside this NVIDIA guide:

- Windows AMD: DirectML, see `docs/GPU_BACKENDS.md`.
- Linux AMD: ROCm, see `docs/GPU_BACKENDS.md`.

NVIDIA CUDA remains the most reliable high-performance path.

CPU-only testing is possible with:

```bash
python extract_assets.py --allow-cpu
```

CPU mode is slower and is intended for review, debugging, or small sprite sheets.

## Check Your Environment

```bash
python extract_assets.py --check-env
```

The output includes:

- Python version.
- Dependency status.
- NVIDIA detection status.
- Whether CPU fallback is allowed.
