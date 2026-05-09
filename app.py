from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import gradio as gr
except Exception as exc:  # pragma: no cover - friendly startup error
    raise SystemExit("Gradio is not installed. Run: pip install -r requirements-ui.txt") from exc


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input_sheets"
OUTPUT_DIR = BASE_DIR / "output_png"
MANIFEST_PATH = BASE_DIR / "manifest" / "map_assets.generated.json"
REPORT_PATH = BASE_DIR / "reports" / "extraction_report.html"
PRESETS_PATH = BASE_DIR / "presets.json"
LOG_PATH = BASE_DIR / "processing.log"


DEFAULT_CONFIG = {
    "category": "roads-waterways",
    "prefix": "river",
    "padding": 36,
    "minArea": 8000,
    "maxArea": 1200000,
    "removeBackground": True,
    "outputSize": 512,
    "ignoreTextRegions": True,
    "gpuBackend": "auto",
    "requireNvidiaGpu": False,
    "allowCpuFallback": True,
    "commercialSafe": True,
    "licenseStatus": "ai-generated",
    "manifestSpriteBase": "/assets/map/isometric",
    "tags": ["2.5d", "isometric", "map", "river"],
}


def load_presets() -> dict[str, dict]:
    if not PRESETS_PATH.exists():
        return {}
    try:
        raw = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
        presets = raw.get("presets", raw)
        return presets if isinstance(presets, dict) else {}
    except Exception:
        return {}


PRESETS = load_presets()


def tail_log(lines: int = 80) -> str:
    if not LOG_PATH.exists():
        return "No log written yet."
    content = LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(content[-lines:])


def read_manifest() -> str:
    if not MANIFEST_PATH.exists():
        return "{}"
    return MANIFEST_PATH.read_text(encoding="utf-8", errors="ignore")


def output_gallery() -> list[str]:
    if not OUTPUT_DIR.exists():
        return []
    return [str(path) for path in sorted(OUTPUT_DIR.glob("*.png"))[-80:]]


def report_link() -> str:
    if not REPORT_PATH.exists():
        return "Report has not been generated yet."
    return f"Report: {REPORT_PATH}"


def build_config(
    preset_name: str,
    category: str,
    prefix: str,
    padding: int,
    output_size: int,
    min_area: int,
    max_area: int,
    remove_background: bool,
    gpu_backend: str,
    require_nvidia: bool,
    allow_cpu: bool,
    tags: str,
) -> dict:
    preset = PRESETS.get(preset_name, {}) if preset_name else {}
    base = {**DEFAULT_CONFIG, **preset}
    parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return {
        **base,
        "category": category.strip() or base["category"],
        "prefix": prefix.strip() or base["prefix"],
        "padding": int(padding),
        "outputSize": int(output_size),
        "minArea": int(min_area),
        "maxArea": int(max_area),
        "removeBackground": bool(remove_background),
        "gpuBackend": gpu_backend,
        "requireNvidiaGpu": bool(require_nvidia),
        "allowCpuFallback": bool(allow_cpu),
        "tags": parsed_tags or base["tags"],
    }


def apply_preset(preset_name: str):
    preset = {**DEFAULT_CONFIG, **PRESETS.get(preset_name, {})}
    return (
        preset["category"],
        preset["prefix"],
        ", ".join(preset["tags"]),
        int(preset["padding"]),
        int(preset["outputSize"]),
        int(preset["minArea"]),
        int(preset["maxArea"]),
    )


def copy_uploads(files: list[str] | None) -> int:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for item in files or []:
        source = Path(item)
        if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        target = INPUT_DIR / source.name
        if target.resolve() != source.resolve():
            shutil.copy2(source, target)
        copied += 1
    return copied


def run_extractor(
    files: list[str] | None,
    preset_name: str,
    category: str,
    prefix: str,
    padding: int,
    output_size: int,
    min_area: int,
    max_area: int,
    remove_background: bool,
    gpu_backend: str,
    require_nvidia: bool,
    allow_cpu: bool,
    dry_run: bool,
    tags: str,
) -> tuple[str, str, list[str], str]:
    copied = copy_uploads(files)
    config = build_config(
        preset_name,
        category,
        prefix,
        padding,
        output_size,
        min_area,
        max_area,
        remove_background,
        gpu_backend,
        require_nvidia,
        allow_cpu,
        tags,
    )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as temp_config:
        json.dump(config, temp_config, ensure_ascii=False, indent=2)
        config_path = temp_config.name

    command = [sys.executable, str(BASE_DIR / "extract_assets.py"), "--config", config_path]
    if allow_cpu:
        command.append("--allow-cpu")
    if dry_run:
        command.append("--dry-run")
    result = subprocess.run(command, cwd=str(BASE_DIR), capture_output=True, text=True)
    status = [
        f"Copied uploads: {copied}",
        f"Exit code: {result.returncode}",
        "",
        "STDOUT:",
        result.stdout.strip(),
        "",
        "STDERR:",
        result.stderr.strip(),
        "",
        "LOG TAIL:",
        tail_log(),
    ]
    return "\n".join(status), read_manifest(), output_gallery(), report_link()


def check_env(gpu_backend: str, require_nvidia: bool, allow_cpu: bool) -> str:
    config = {
        **DEFAULT_CONFIG,
        "gpuBackend": gpu_backend,
        "requireNvidiaGpu": require_nvidia,
        "allowCpuFallback": allow_cpu,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as temp_config:
        json.dump(config, temp_config, ensure_ascii=False, indent=2)
        config_path = temp_config.name
    command = [sys.executable, str(BASE_DIR / "extract_assets.py"), "--config", config_path, "--check-env"]
    if allow_cpu:
        command.append("--allow-cpu")
    result = subprocess.run(command, cwd=str(BASE_DIR), capture_output=True, text=True)
    return result.stdout.strip() or result.stderr.strip()


with gr.Blocks(title="Image Multi Asset Extractor") as demo:
    gr.Markdown(
        """
        # Image Multi Asset Extractor

        Split 2.5D/isometric sprite sheets into individual transparent PNG assets.
        GPU mode requires an NVIDIA CUDA GPU. AMD GPU acceleration is not supported.
        """
    )
    with gr.Row():
        with gr.Column(scale=1):
            uploads = gr.File(label="Input sprite sheets", file_count="multiple", file_types=[".png", ".jpg", ".jpeg", ".webp"])
            preset = gr.Dropdown(label="Preset", choices=[""] + sorted(PRESETS), value="", info="Optional tuning preset.")
            category = gr.Textbox(label="Category", value=DEFAULT_CONFIG["category"])
            prefix = gr.Textbox(label="Filename prefix / subCategory", value=DEFAULT_CONFIG["prefix"])
            tags = gr.Textbox(label="Tags, comma separated", value=", ".join(DEFAULT_CONFIG["tags"]))
            padding = gr.Slider(24, 48, value=36, step=1, label="Padding")
            output_size = gr.Number(label="Output size", value=512, precision=0)
            min_area = gr.Number(label="Minimum detected area", value=8000, precision=0)
            max_area = gr.Number(label="Maximum detected area", value=1200000, precision=0)
            remove_background = gr.Checkbox(label="Remove background with rembg", value=True)
            gpu_backend = gr.Dropdown(
                label="GPU / background backend",
                choices=["auto", "nvidia-cuda", "amd-directml", "amd-rocm", "cpu"],
                value="auto",
                info="AMD Windows users can try amd-directml; Linux AMD users can try amd-rocm.",
            )
            require_nvidia = gr.Checkbox(label="Require NVIDIA CUDA GPU", value=False)
            allow_cpu = gr.Checkbox(label="Allow CPU fallback for testing", value=True)
            dry_run = gr.Checkbox(label="Preview only: detect boxes without exporting PNGs", value=False)
            with gr.Row():
                env_button = gr.Button("Check Environment")
                run_button = gr.Button("Extract Assets", variant="primary")
        with gr.Column(scale=2):
            log_box = gr.Textbox(label="Processing log", lines=18)
            manifest_box = gr.Code(label="Generated manifest", language="json")
            gallery = gr.Gallery(label="Output PNG preview", columns=5, height=420)
            report_box = gr.Textbox(label="HTML report path", interactive=False)

    env_button.click(check_env, inputs=[gpu_backend, require_nvidia, allow_cpu], outputs=[log_box])
    preset.change(
        apply_preset,
        inputs=[preset],
        outputs=[category, prefix, tags, padding, output_size, min_area, max_area],
    )
    run_button.click(
        run_extractor,
        inputs=[
            uploads,
            preset,
            category,
            prefix,
            padding,
            output_size,
            min_area,
            max_area,
            remove_background,
            gpu_backend,
            require_nvidia,
            allow_cpu,
            dry_run,
            tags,
        ],
        outputs=[log_box, manifest_box, gallery, report_box],
    )


if __name__ == "__main__":
    demo.launch()
