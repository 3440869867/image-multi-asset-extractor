# Installation Guide

Image Multi Asset Extractor is designed to run on most common desktop/server systems.

## Compatibility Matrix

| System | CPU Mode | NVIDIA GPU Mode | AMD GPU Mode | Notes |
| --- | --- | --- | --- | --- |
| Windows 10/11 | Supported | Supported with NVIDIA driver/CUDA runtime | Experimental via DirectML | Use PowerShell or `.bat` scripts. |
| Linux x86_64 | Supported | Supported with NVIDIA driver/CUDA runtime | Experimental via ROCm | Best target for batch GPU extraction. |
| macOS Apple Silicon | Supported | Not supported | Not supported | CPU mode only. |
| macOS Intel | Supported | Rare legacy setups only, not recommended | Not supported | CPU mode recommended. |
| Docker | Supported | Possible with NVIDIA Container Toolkit | Not supported | Included Dockerfile is CPU-first. |

NVIDIA CUDA is the most reliable GPU path. AMD is best-effort through DirectML on Windows or ROCm on Linux. CPU mode is the broad compatibility path.

## Windows CPU Install

```powershell
cd image-multi-asset-extractor
.\scripts\install_cpu.ps1
.\scripts\run_ui.ps1
```

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Alternative:

```bat
scripts\install_cpu.bat
scripts\run_ui.bat
```

## Windows NVIDIA Install

Install a recent NVIDIA driver first, then:

```powershell
cd image-multi-asset-extractor
.\scripts\install_nvidia.ps1
.\scripts\run_ui.ps1
```

Check:

```powershell
.\.venv\Scripts\python.exe extract_assets.py --check-env
```

## Windows AMD DirectML Install

```powershell
cd image-multi-asset-extractor
.\scripts\install_amd_directml.ps1
.\scripts\run_ui.ps1
```

In the UI, choose:

```text
amd-directml
```

Or in `config.json`:

```json
{
  "gpuBackend": "amd-directml",
  "allowCpuFallback": true
}
```

## Linux CPU Install

```bash
cd image-multi-asset-extractor
chmod +x scripts/*.sh
./scripts/install_cpu.sh
./scripts/run_ui.sh
```

## Linux NVIDIA Install

Install NVIDIA driver/CUDA runtime first, confirm:

```bash
nvidia-smi
```

Then:

```bash
cd image-multi-asset-extractor
chmod +x scripts/*.sh
./scripts/install_nvidia.sh
./scripts/run_ui.sh
```

## Linux AMD ROCm Install

ROCm support depends on GPU generation, driver, distribution, Python version, and ONNX Runtime package availability.

```bash
cd image-multi-asset-extractor
chmod +x scripts/*.sh
./scripts/install_amd_rocm.sh
./scripts/run_ui.sh
```

In the UI, choose:

```text
amd-rocm
```

## macOS Install

macOS is CPU mode only:

```bash
cd image-multi-asset-extractor
chmod +x scripts/*.sh
./scripts/install_cpu.sh
./scripts/run_ui.sh
```

## Docker CPU Mode

```bash
docker compose up --build
```

Open:

```text
http://localhost:7860
```

The included Docker setup is CPU-first. NVIDIA Docker can be added later with NVIDIA Container Toolkit.
