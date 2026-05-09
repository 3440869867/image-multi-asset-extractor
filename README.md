# Image Multi Asset Extractor

Image Multi Asset Extractor is a standalone Python tool for splitting 2.5D/isometric sprite-sheet images into individual transparent PNG assets.

It is useful for map asset libraries, worldbuilding tools, tabletop map editors, visual novel tools, and game prototypes.

> GPU acceleration is NVIDIA CUDA only. AMD GPU acceleration is not supported.

## What It Does

- Reads PNG, JPG, JPEG, and WEBP sprite sheets.
- Detects multiple independent visual elements in one sheet.
- Ignores likely headers, labels, numbering, text notes, and large borders.
- Crops each detected element with 24-48px padding.
- Removes background with `rembg`.
- Exports transparent PNG files.
- Generates a map-asset manifest JSON.
- Sends uncertain sheets to `review_needed/` without deleting originals.
- Supports named extraction presets.
- Supports dry-run detection previews before exporting PNG files.
- Generates a human-readable HTML report.
- Provides both CLI and optional Gradio Web UI.

## Repository Layout

```text
image-multi-asset-extractor/
├── input_sheets/
├── cropped/
├── output_png/
├── review_needed/
├── manifest/
├── reports/
├── docs/
├── examples/
├── app.py
├── config.json
├── extract_assets.py
├── requirements.txt
├── requirements-gpu-nvidia.txt
├── requirements-ui.txt
├── pyproject.toml
└── README.md
```

## Hardware Requirement

The tool supports most common systems through CPU mode, supports faster background removal on NVIDIA CUDA systems, and provides best-effort AMD acceleration through DirectML or ROCm.

Recommended production GPU mode:

- NVIDIA GPU
- Recent NVIDIA driver
- CUDA-compatible runtime through `onnxruntime-gpu`

Best-effort AMD modes:

- Windows AMD: DirectML through `DmlExecutionProvider`
- Linux AMD: ROCm through `ROCMExecutionProvider`

Not supported:

- Intel GPU acceleration
- macOS GPU acceleration

CPU-only testing can be allowed with `--allow-cpu`, but it is slower and intended for small inputs or debugging.

See:

- [docs/INSTALL.md](docs/INSTALL.md)
- [docs/NVIDIA_CUDA.md](docs/NVIDIA_CUDA.md)
- [docs/GPU_BACKENDS.md](docs/GPU_BACKENDS.md)

## System Support

| System | CPU Mode | NVIDIA GPU Mode | AMD GPU Mode |
| --- | --- | --- | --- |
| Windows 10/11 | Yes | Yes | Best effort via DirectML |
| Linux x86_64 | Yes | Yes | Best effort via ROCm |
| macOS Apple Silicon | Yes | No | No |
| macOS Intel | Yes | Not recommended | No |
| Docker | Yes | Advanced setup | Not included |

## Installation

```bash
git clone https://github.com/your-name/image-multi-asset-extractor.git
cd image-multi-asset-extractor

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-cpu.txt
```

NVIDIA install:

```bash
pip install -r requirements.txt
pip install -r requirements-gpu-nvidia.txt
```

AMD Windows DirectML install:

```bash
pip install -r requirements.txt
pip install -r requirements-amd-directml.txt
```

AMD Linux ROCm install:

```bash
pip install -r requirements.txt
pip install -r requirements-amd-rocm.txt
```

Optional Web UI:

```bash
pip install -r requirements-ui.txt
```

Or use helper scripts:

```powershell
.\scripts\install_cpu.ps1
.\scripts\install_nvidia.ps1
.\scripts\install_amd_directml.ps1
.\scripts\run_ui.ps1
```

Linux/macOS:

```bash
chmod +x scripts/*.sh
./scripts/install_cpu.sh
./scripts/install_amd_rocm.sh
./scripts/run_ui.sh
```

Docker CPU mode:

```bash
docker compose up --build
```

Check environment:

```bash
python extract_assets.py --check-env
```

## Quick Start

1. Put sprite-sheet images into:

```text
input_sheets/
```

2. Edit `config.json`:

```json
{
  "category": "roads-waterways",
  "prefix": "river",
  "padding": 36,
  "minArea": 8000,
  "maxArea": 1200000,
  "removeBackground": true,
  "outputSize": 512,
  "ignoreTextRegions": true,
  "gpuBackend": "auto",
  "requireNvidiaGpu": false,
  "allowCpuFallback": true,
  "commercialSafe": true,
  "tags": ["2.5d", "isometric", "map", "river"]
}
```

3. Run:

```bash
python extract_assets.py
```

CPU-only testing:

```bash
python extract_assets.py --allow-cpu
```

Preview detection boxes without exporting PNGs:

```bash
python extract_assets.py --dry-run --allow-cpu
```

This writes annotated preview images and an HTML report to:

```text
reports/extraction_report.html
```

Override category and filename prefix:

```bash
python extract_assets.py --category roads-waterways --prefix river
```

List built-in presets:

```bash
python extract_assets.py --list-presets
```

Use a preset:

```bash
python extract_assets.py --preset xianxia-buildings
```

## Web UI

Start the UI:

```bash
python app.py
```

The UI supports:

- Multiple sheet uploads.
- Category and prefix editing.
- Preset selection.
- Padding and area threshold tuning.
- Preview-only dry run mode.
- NVIDIA environment check.
- CPU fallback toggle for testing.
- Output PNG preview.
- Manifest preview.
- HTML report path.

## Output

Transparent PNG assets are written to:

```text
output_png/
```

Intermediate crops are written to:

```text
cropped/
```

Sheets that need manual inspection are copied to:

```text
review_needed/
```

The manifest is written to:

```text
manifest/map_assets.generated.json
```

The HTML report is written to:

```text
reports/extraction_report.html
```

## Filename Format

```text
river_001.png
river_002.png
river_003.png
```

The prefix comes from `config.json`.

## Manifest Format

Each generated item looks like:

```json
{
  "id": "river_001",
  "name": "River 001",
  "category": "roads-waterways",
  "subCategory": "river",
  "spriteUrl": "/assets/map/isometric/roads-waterways/river_001.png",
  "thumbnail": "/assets/map/isometric/roads-waterways/river_001.png",
  "defaultWidth": 512,
  "defaultHeight": 512,
  "anchorX": 0.5,
  "anchorY": 0.8,
  "tags": ["2.5d", "isometric", "map", "river"],
  "licenseStatus": "ai-generated",
  "commercialSafe": true
}
```

## Suggested Categories

- `river`
- `ocean`
- `road`
- `bridge`
- `building`
- `war`
- `xianxia`
- `sci-fi`

## Presets

Presets live in:

```text
presets.json
```

Current presets:

- `roads-waterways`
- `xianxia-buildings`
- `sci-fi-structures`
- `war-markers`

Presets are simple JSON fragments. They can tune:

- `category`
- `prefix`
- `padding`
- `minArea`
- `maxArea`
- `outputSize`
- `tags`

You can also use broader categories such as:

- `roads-waterways`
- `terrain`
- `settlements`
- `landmarks`
- `fantasy`
- `modern`
- `sci-fi`

## Importing Into a Map Asset Library

Example target:

```text
public/assets/map/isometric/roads-waterways/
```

Copy:

```text
output_png/*.png
```

Then merge:

```text
manifest/map_assets.generated.json
```

into your application's map asset manifest.

## Review Workflow

Automatic extraction is not perfect. Review `review_needed/` when:

- Elements are touching each other.
- Text overlaps the artwork.
- Background is complex.
- Shadows are faint.
- Borders are mistaken for assets.

Tune:

- `minArea`
- `maxArea`
- `backgroundTolerance`
- `padding`
- `ignoreTextRegions`

## Safety and Licensing

This tool does not determine whether a source image is legally safe to use. Only process assets you own, generated assets you are allowed to use, or assets with a license compatible with your project.

`commercialSafe` is metadata you control. It is not legal advice.

## Publishing to GitHub

Before publishing:

1. Remove private images from `input_sheets/`.
2. Remove generated assets from `output_png/`, `cropped/`, `review_needed/`, and `manifest/`.
3. Remove generated reports from `reports/`.
4. Keep only `.gitkeep` files in generated folders.
5. Do not commit `.venv/`.
6. Run:

```bash
python -m py_compile extract_assets.py app.py
python extract_assets.py --check-env
```

Then:

```bash
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/your-name/image-multi-asset-extractor.git
git push -u origin main
```

## Roadmap

- Manual crop correction UI.
- Side-by-side before/after review mode.
- Batch category presets.
- Better detection for touching objects.
- Optional SAM-based segmentation.
- Export profiles for map editors and asset managers.
