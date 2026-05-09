# GPU Backends

Image Multi Asset Extractor tries to support as many systems as possible:

- NVIDIA: CUDA through `CUDAExecutionProvider`
- AMD on Windows: DirectML through `DmlExecutionProvider`
- AMD on Linux: ROCm through `ROCMExecutionProvider` when available
- Universal fallback: CPU through `CPUExecutionProvider`

## Backend Selection

Set `gpuBackend` in `config.json`:

```json
{
  "gpuBackend": "auto"
}
```

Supported values:

- `auto`
- `nvidia-cuda`
- `amd-directml`
- `amd-rocm`
- `cpu`

`auto` tries providers in this order:

1. `CUDAExecutionProvider`
2. `DmlExecutionProvider`
3. `ROCMExecutionProvider`
4. `CPUExecutionProvider`

## AMD Windows: DirectML

Install:

```powershell
.\scripts\install_amd_directml.ps1
```

Then choose `amd-directml` in the UI, or set:

```json
{
  "gpuBackend": "amd-directml",
  "allowCpuFallback": true
}
```

DirectML support depends on your Windows version, GPU driver, Python version, and ONNX Runtime package compatibility.

## AMD Linux: ROCm

Install:

```bash
chmod +x scripts/*.sh
./scripts/install_amd_rocm.sh
```

Then choose `amd-rocm` in the UI, or set:

```json
{
  "gpuBackend": "amd-rocm",
  "allowCpuFallback": true
}
```

ROCm support is more restrictive than CPU mode. It depends on Linux distribution, AMD GPU generation, ROCm version, and Python/ONNX Runtime compatibility.

## CPU Fallback

If AMD acceleration is unavailable, keep:

```json
{
  "allowCpuFallback": true
}
```

The tool will still run, just slower.
