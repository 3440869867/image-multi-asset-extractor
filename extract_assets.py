from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import importlib.util
import io
import json
import logging
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # pragma: no cover - handled before image processing starts
    Image = None

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - handled before image processing starts
    cv2 = None
    np = None

rembg_remove = None
rembg_session = None
_REMBG_IMPORT_ATTEMPTED = False


BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input_sheets"
CROPPED_DIR = BASE_DIR / "cropped"
OUTPUT_DIR = BASE_DIR / "output_png"
REVIEW_DIR = BASE_DIR / "review_needed"
MANIFEST_DIR = BASE_DIR / "manifest"
REPORT_DIR = BASE_DIR / "reports"
LOG_PATH = BASE_DIR / "processing.log"
MANIFEST_PATH = MANIFEST_DIR / "map_assets.generated.json"
REPORT_PATH = REPORT_DIR / "extraction_report.html"
PRESETS_PATH = BASE_DIR / "presets.json"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class ExtractorConfig:
    category: str
    prefix: str
    padding: int
    min_area: int
    max_area: int
    remove_background: bool
    output_size: int
    ignore_text_regions: bool
    commercial_safe: bool
    tags: list[str]
    background_tolerance: float = 28.0
    header_ignore_ratio: float = 0.11
    require_nvidia_gpu: bool = False
    allow_cpu_fallback: bool = True
    gpu_backend: str = "auto"
    license_status: str = "ai-generated"
    manifest_sprite_base: str = "/assets/map/isometric"


@dataclass(frozen=True)
class AssetBox:
    x: int
    y: int
    width: int
    height: int
    contour_area: float
    bbox_area: int


def setup_logging() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def ensure_directories() -> None:
    for directory in [INPUT_DIR, CROPPED_DIR, OUTPUT_DIR, REVIEW_DIR, MANIFEST_DIR, REPORT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def load_presets(path: Path = PRESETS_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    presets = raw.get("presets", raw)
    if not isinstance(presets, dict):
        return {}
    return {str(key): value for key, value in presets.items() if isinstance(value, dict)}


def load_config(path: Path, preset_name: str = "") -> ExtractorConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if preset_name:
        presets = load_presets()
        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}. Use --list-presets to see available presets.")
        raw = {**raw, **presets[preset_name]}
    padding = int(raw.get("padding", 36))
    if padding < 24 or padding > 48:
        logging.warning("Padding %s is outside 24-48px. Clamped for final output.", padding)
        padding = max(24, min(48, padding))
    return ExtractorConfig(
        category=str(raw.get("category", "map-assets")),
        prefix=slugify(str(raw.get("prefix", "asset"))),
        padding=padding,
        min_area=int(raw.get("minArea", 8000)),
        max_area=int(raw.get("maxArea", 1200000)),
        remove_background=bool(raw.get("removeBackground", True)),
        output_size=int(raw.get("outputSize", 512)),
        ignore_text_regions=bool(raw.get("ignoreTextRegions", True)),
        commercial_safe=bool(raw.get("commercialSafe", True)),
        tags=[str(tag) for tag in raw.get("tags", ["2.5d", "isometric", "map"])],
        background_tolerance=float(raw.get("backgroundTolerance", 28.0)),
        header_ignore_ratio=float(raw.get("headerIgnoreRatio", 0.11)),
        require_nvidia_gpu=bool(raw.get("requireNvidiaGpu", False)),
        allow_cpu_fallback=bool(raw.get("allowCpuFallback", True)),
        gpu_backend=str(raw.get("gpuBackend", "auto")).lower(),
        license_status=str(raw.get("licenseStatus", "ai-generated")),
        manifest_sprite_base=str(raw.get("manifestSpriteBase", "/assets/map/isometric")).rstrip("/"),
    )


def slugify(value: str) -> str:
    value = value.strip().lower().replace(" ", "_").replace("-", "_")
    value = re.sub(r"[^a-z0-9_]+", "", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "asset"


def ensure_image_dependencies() -> None:
    if cv2 is None or np is None or Image is None:
        raise RuntimeError("Missing image dependencies. Run: pip install -r requirements.txt")


def get_rembg_remove():
    global rembg_remove, _REMBG_IMPORT_ATTEMPTED
    if _REMBG_IMPORT_ATTEMPTED:
        return rembg_remove
    _REMBG_IMPORT_ATTEMPTED = True
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from rembg import remove as imported_remove
        rembg_remove = imported_remove
    except BaseException as exc:  # pragma: no cover - rembg may SystemExit when onnxruntime is missing
        logging.warning("rembg is not available or lacks an onnxruntime backend: %s", exc)
        rembg_remove = None
    return rembg_remove


def get_rembg_session(config: ExtractorConfig):
    global rembg_session
    if rembg_session is not None:
        return rembg_session
    providers = choose_onnx_provider(config)
    if not providers:
        return None
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from rembg import new_session

        rembg_session = new_session("u2net", providers=providers)
        logging.info("rembg session created with providers: %s", providers)
    except BaseException as exc:
        logging.warning("Could not create rembg session with providers %s: %s", providers, exc)
        rembg_session = None
    return rembg_session


def detect_nvidia_gpu() -> tuple[bool, str]:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return False, "nvidia-smi was not found. NVIDIA CUDA GPU acceleration is unavailable."
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception as exc:
        return False, f"Failed to execute nvidia-smi: {exc}"
    output = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0:
        return False, output or "nvidia-smi returned a non-zero exit code."
    return True, output or "NVIDIA GPU detected."


def detect_gpu_vendors() -> dict[str, Any]:
    commands: list[list[str]] = []
    if sys.platform.startswith("win"):
        commands = [["wmic", "path", "win32_VideoController", "get", "name"]]
    elif sys.platform.startswith("linux"):
        commands = [["sh", "-lc", "lspci | grep -Ei 'vga|3d|display' || true"]]
    elif sys.platform == "darwin":
        commands = [["system_profiler", "SPDisplaysDataType"]]

    raw_output = ""
    for command in commands:
        try:
            result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=8)
        except Exception:
            continue
        raw_output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        if raw_output:
            break

    lowered = raw_output.lower()
    vendors = []
    if any(token in lowered for token in ["nvidia", "geforce", "rtx", "gtx", "quadro"]):
        vendors.append("nvidia")
    if any(token in lowered for token in ["amd", "radeon", "advanced micro devices"]):
        vendors.append("amd")
    if any(token in lowered for token in ["intel", "iris", "uhd graphics"]):
        vendors.append("intel")
    if any(token in lowered for token in ["apple", "m1", "m2", "m3", "m4"]):
        vendors.append("apple")
    return {"vendors": sorted(set(vendors)), "raw": raw_output}


def get_onnxruntime_providers() -> list[str]:
    try:
        import onnxruntime as ort

        return list(ort.get_available_providers())
    except Exception:
        return []


def choose_onnx_provider(config: ExtractorConfig) -> list[str]:
    available = get_onnxruntime_providers()
    backend = config.gpu_backend
    preference = {
        "auto": ["CUDAExecutionProvider", "DmlExecutionProvider", "ROCMExecutionProvider", "CPUExecutionProvider"],
        "nvidia-cuda": ["CUDAExecutionProvider", "CPUExecutionProvider"],
        "amd-directml": ["DmlExecutionProvider", "CPUExecutionProvider"],
        "amd-rocm": ["ROCMExecutionProvider", "CPUExecutionProvider"],
        "cpu": ["CPUExecutionProvider"],
    }.get(backend, ["CUDAExecutionProvider", "DmlExecutionProvider", "ROCMExecutionProvider", "CPUExecutionProvider"])
    selected = [provider for provider in preference if provider in available]
    return selected or available


def check_environment(config: ExtractorConfig, allow_cpu_override: bool = False) -> dict[str, Any]:
    has_nvidia, nvidia_message = detect_nvidia_gpu()
    gpu_vendors = detect_gpu_vendors()
    ort_providers = get_onnxruntime_providers()
    selected_providers = choose_onnx_provider(config)
    dependencies = {
        "pillow": Image is not None,
        "opencv-python": cv2 is not None,
        "numpy": np is not None,
        "rembg": importlib.util.find_spec("rembg") is not None,
    }
    onnxruntime_available = importlib.util.find_spec("onnxruntime") is not None
    cpu_allowed = config.allow_cpu_fallback or allow_cpu_override
    nvidia_required = config.require_nvidia_gpu and not cpu_allowed
    ok = all(dependencies.values()) and (has_nvidia or not nvidia_required)
    return {
        "ok": ok,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "dependencies": dependencies,
        "nvidia": {
            "detected": has_nvidia,
            "message": nvidia_message,
            "required": nvidia_required,
            "amdGpuAccelerationSupported": False,
        },
        "backgroundBackend": {
            "onnxruntime": onnxruntime_available,
            "requested": config.gpu_backend,
            "availableProviders": ort_providers,
            "selectedProviders": selected_providers,
            "amdDirectMLSupported": "DmlExecutionProvider" in ort_providers,
            "amdRocmSupported": "ROCMExecutionProvider" in ort_providers,
            "note": "NVIDIA uses CUDAExecutionProvider; AMD on Windows can use DirectML; AMD on Linux can use ROCm when available; CPU remains the broad fallback.",
        },
        "detectedGpuVendors": gpu_vendors,
        "cpuFallbackAllowed": cpu_allowed,
    }


def enforce_environment(config: ExtractorConfig, allow_cpu_override: bool = False) -> None:
    report = check_environment(config, allow_cpu_override)
    logging.info("Environment check: %s", json.dumps(report, ensure_ascii=False))
    missing = [name for name, ok in report["dependencies"].items() if not ok]
    if missing:
        raise RuntimeError(f"Missing dependencies: {', '.join(missing)}. Run: pip install -r requirements.txt")
    if report["nvidia"]["required"] and not report["nvidia"]["detected"]:
        raise RuntimeError(
            "NVIDIA CUDA GPU is required by this configuration. AMD GPU acceleration is not supported. "
            "Install an NVIDIA driver/CUDA runtime or run with --allow-cpu for slower CPU-only testing."
        )


def read_image(path: Path):
    ensure_image_dependencies()
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        if image is None:
            logging.error("OpenCV could not decode image: %s", path.name)
        return image
    except Exception as exc:
        logging.exception("Failed to read image %s: %s", path.name, exc)
        return None


def to_rgb(image):
    if image.ndim == 2:
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        return rgb, None
    if image.shape[2] == 4:
        bgra = image
        rgb = cv2.cvtColor(bgra[:, :, :3], cv2.COLOR_BGR2RGB)
        alpha = bgra[:, :, 3]
        return rgb, alpha
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return rgb, None


def estimate_background(rgb):
    height, width = rgb.shape[:2]
    band = max(4, min(width, height) // 45)
    samples = np.concatenate(
        [
            rgb[:band, :, :].reshape(-1, 3),
            rgb[-band:, :, :].reshape(-1, 3),
            rgb[:, :band, :].reshape(-1, 3),
            rgb[:, -band:, :].reshape(-1, 3),
        ],
        axis=0,
    )
    return np.median(samples, axis=0)


def build_foreground_mask(rgb, alpha, config: ExtractorConfig):
    bg = estimate_background(rgb)
    diff = np.linalg.norm(rgb.astype(np.float32) - bg.astype(np.float32), axis=2)
    mask = diff > config.background_tolerance

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    mask |= (saturation > 28) & (value < 248)

    if alpha is not None:
        mask |= alpha > 18

    mask_u8 = (mask.astype(np.uint8) * 255)
    mask_u8 = cv2.medianBlur(mask_u8, 5)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, close_kernel, iterations=2)
    mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, open_kernel, iterations=1)
    mask_u8 = cv2.dilate(mask_u8, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)), iterations=1)
    return mask_u8


def is_probable_text_or_frame(box: AssetBox, sheet_width: int, sheet_height: int, config: ExtractorConfig) -> bool:
    x, y, w, h = box.x, box.y, box.width, box.height
    aspect = w / max(1, h)
    bbox_area = w * h
    total_area = sheet_width * sheet_height

    touches_edges = x <= 4 or y <= 4 or x + w >= sheet_width - 4 or y + h >= sheet_height - 4
    if touches_edges and bbox_area > total_area * 0.42:
        return True
    if w > sheet_width * 0.92 and h > sheet_height * 0.92:
        return True
    if w > sheet_width * 0.78 and h < sheet_height * 0.08:
        return True
    if h > sheet_height * 0.78 and w < sheet_width * 0.08:
        return True

    if not config.ignore_text_regions:
        return False

    if y < sheet_height * config.header_ignore_ratio and h < sheet_height * 0.16:
        return True
    if aspect > 5.8 and bbox_area < total_area * 0.12:
        return True
    if aspect < 0.16 and bbox_area < total_area * 0.12:
        return True
    if h < 52 and aspect > 2.2:
        return True
    if w < 52 and h < 52:
        return True
    return False


def find_asset_boxes(mask: np.ndarray, config: ExtractorConfig) -> list[AssetBox]:
    sheet_height, sheet_width = mask.shape[:2]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[AssetBox] = []

    for contour in contours:
        contour_area = float(cv2.contourArea(contour))
        x, y, w, h = cv2.boundingRect(contour)
        bbox_area = w * h
        if contour_area < config.min_area or bbox_area < config.min_area:
            continue
        if contour_area > config.max_area or bbox_area > config.max_area:
            continue
        box = AssetBox(x=x, y=y, width=w, height=h, contour_area=contour_area, bbox_area=bbox_area)
        if is_probable_text_or_frame(box, sheet_width, sheet_height, config):
            continue
        boxes.append(box)

    boxes = sorted(boxes, key=lambda item: (item.y // 80, item.x))
    return suppress_nested_or_duplicate_boxes(boxes)


def write_detection_preview(path: Path, rgb, boxes: list[AssetBox]) -> Path:
    image = Image.fromarray(rgb, mode="RGB").convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    try:
        from PIL import ImageDraw

        draw = ImageDraw.Draw(overlay)
        for index, box in enumerate(boxes, start=1):
            x1, y1 = box.x, box.y
            x2, y2 = box.x + box.width, box.y + box.height
            draw.rectangle((x1, y1, x2, y2), outline=(201, 150, 62, 255), width=4)
            draw.text((x1 + 6, y1 + 6), str(index), fill=(140, 73, 20, 255))
    except Exception as exc:
        logging.warning("Could not draw detection preview for %s: %s", path.name, exc)
    preview = Image.alpha_composite(image, overlay)
    preview_path = REPORT_DIR / f"{path.stem}.detected.png"
    preview.save(preview_path)
    return preview_path


def suppress_nested_or_duplicate_boxes(boxes: list[AssetBox]) -> list[AssetBox]:
    kept: list[AssetBox] = []
    for box in boxes:
        duplicate = False
        for existing in kept:
            overlap = intersection_area(box, existing)
            smaller = min(box.bbox_area, existing.bbox_area)
            if smaller and overlap / smaller > 0.78:
                duplicate = True
                break
        if not duplicate:
            kept.append(box)
    return kept


def intersection_area(a: AssetBox, b: AssetBox) -> int:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.width, b.x + b.width)
    y2 = min(a.y + a.height, b.y + b.height)
    return max(0, x2 - x1) * max(0, y2 - y1)


def crop_with_padding(rgb, box: AssetBox, padding: int) -> Image.Image:
    height, width = rgb.shape[:2]
    x1 = max(0, box.x - padding)
    y1 = max(0, box.y - padding)
    x2 = min(width, box.x + box.width + padding)
    y2 = min(height, box.y + box.height + padding)
    crop = rgb[y1:y2, x1:x2]
    return Image.fromarray(crop, mode="RGB")


def remove_background(image: Image.Image, enabled: bool, config: ExtractorConfig) -> Image.Image:
    rgba = image.convert("RGBA")
    if not enabled:
        return rgba
    remove_fn = get_rembg_remove()
    if remove_fn is not None:
        session = get_rembg_session(config)
        if session is not None:
            return remove_fn(rgba, session=session)
        return remove_fn(rgba)
    logging.warning("rembg is not available; using local border-color alpha fallback.")
    return remove_background_by_border_color(rgba)


def remove_background_by_border_color(image: Image.Image) -> Image.Image:
    arr = np.array(image.convert("RGBA"))
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    bg = estimate_background(rgb)
    diff = np.linalg.norm(rgb.astype(np.float32) - bg.astype(np.float32), axis=2)
    next_alpha = np.where(diff > 24, alpha, 0).astype(np.uint8)
    next_alpha = cv2.GaussianBlur(next_alpha, (3, 3), 0)
    arr[:, :, 3] = next_alpha
    return Image.fromarray(arr, mode="RGBA")


def normalize_png(image: Image.Image, output_size: int, padding: int) -> Image.Image:
    rgba = image.convert("RGBA")
    bbox = rgba.getbbox()
    if bbox is None:
        return Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))

    trimmed = rgba.crop(bbox)
    if output_size <= 0:
        canvas = Image.new("RGBA", (trimmed.width + padding * 2, trimmed.height + padding * 2), (0, 0, 0, 0))
        canvas.alpha_composite(trimmed, (padding, padding))
        return canvas

    max_side = max(1, output_size - padding * 2)
    scale = min(max_side / trimmed.width, max_side / trimmed.height, 1.0 if max(trimmed.width, trimmed.height) <= max_side else math.inf)
    new_size = (max(1, round(trimmed.width * scale)), max(1, round(trimmed.height * scale)))
    resized = trimmed.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((output_size - new_size[0]) // 2, (output_size - new_size[1]) // 2))
    return canvas


def next_asset_index(prefix: str) -> int:
    max_index = 0
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.png$")
    for path in OUTPUT_DIR.glob(f"{prefix}_*.png"):
        match = pattern.match(path.name)
        if match:
            max_index = max(max_index, int(match.group(1)))
    return max_index + 1


def write_review_copy(path: Path, reason: str) -> None:
    target = REVIEW_DIR / path.name
    shutil.copy2(path, target)
    reason_path = target.with_suffix(target.suffix + ".reason.txt")
    reason_path.write_text(reason, encoding="utf-8")
    logging.warning("%s moved to review_needed: %s", path.name, reason)


def build_manifest_item(filename: str, config: ExtractorConfig) -> dict[str, Any]:
    asset_id = filename.removesuffix(".png")
    display_name = asset_id.replace("_", " ").title()
    sprite_url = f"{config.manifest_sprite_base}/{config.category}/{filename}"
    return {
        "id": asset_id,
        "name": display_name,
        "category": config.category,
        "subCategory": config.prefix,
        "spriteUrl": sprite_url,
        "thumbnail": sprite_url,
        "defaultWidth": config.output_size,
        "defaultHeight": config.output_size,
        "anchorX": 0.5,
        "anchorY": 0.8,
        "tags": config.tags,
        "licenseStatus": config.license_status,
        "commercialSafe": config.commercial_safe,
    }


def process_sheet(path: Path, config: ExtractorConfig, start_index: int, dry_run: bool = False) -> tuple[int, list[dict[str, Any]]]:
    ensure_image_dependencies()
    image = read_image(path)
    if image is None:
        write_review_copy(path, "image_decode_failed")
        return start_index, []

    rgb, alpha = to_rgb(image)
    mask = build_foreground_mask(rgb, alpha, config)
    boxes = find_asset_boxes(mask, config)
    logging.info("%s: detected %s candidate assets", path.name, len(boxes))
    preview_path = write_detection_preview(path, rgb, boxes)
    logging.info("Detection preview written: %s", preview_path)

    if not boxes:
        write_review_copy(path, "no_asset_boxes_detected")
        return start_index, []
    if dry_run:
        return start_index, []

    manifest_items: list[dict[str, Any]] = []
    index = start_index
    for box in boxes:
        filename = f"{config.prefix}_{index:03d}.png"
        cropped_path = CROPPED_DIR / f"{config.prefix}_{index:03d}.cropped.png"
        output_path = OUTPUT_DIR / filename

        crop = crop_with_padding(rgb, box, config.padding)
        crop.save(cropped_path)
        transparent = remove_background(crop, config.remove_background, config)
        normalized = normalize_png(transparent, config.output_size, config.padding)
        normalized.save(output_path)

        manifest_items.append(build_manifest_item(filename, config))
        logging.info("Wrote %s from %s bbox=(%s,%s,%s,%s)", filename, path.name, box.x, box.y, box.width, box.height)
        index += 1

    return index, manifest_items


def write_manifest(items: list[dict[str, Any]]) -> None:
    payload = {
        "generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("Manifest written: %s (%s items)", MANIFEST_PATH, len(items))


def write_run_summary(config: ExtractorConfig, items: list[dict[str, Any]], reviewed_count: int) -> None:
    summary_path = MANIFEST_DIR / "run_summary.json"
    payload = {
        "generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "category": config.category,
        "prefix": config.prefix,
        "outputCount": len(items),
        "reviewNeededCount": reviewed_count,
        "outputDirectory": str(OUTPUT_DIR),
        "manifestPath": str(MANIFEST_PATH),
        "nvidia": check_environment(config, allow_cpu_override=True)["nvidia"],
    }
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.info("Run summary written: %s", summary_path)


def write_html_report(config: ExtractorConfig, items: list[dict[str, Any]], dry_run: bool) -> None:
    previews = sorted(REPORT_DIR.glob("*.detected.png"))
    outputs = sorted(OUTPUT_DIR.glob(f"{config.prefix}_*.png"))
    reviews = sorted(path for path in REVIEW_DIR.iterdir() if path.is_file() and not path.name.endswith(".reason.txt"))

    def rel(path: Path) -> str:
        return path.relative_to(BASE_DIR).as_posix()

    output_cards = "\n".join(
        f'<figure><img src="{rel(path)}" alt="{path.name}"><figcaption>{path.name}</figcaption></figure>' for path in outputs[-160:]
    ) or "<p>No PNG assets exported yet.</p>"
    preview_cards = "\n".join(
        f'<figure><img src="{rel(path)}" alt="{path.name}"><figcaption>{path.name}</figcaption></figure>' for path in previews[-80:]
    ) or "<p>No detection previews yet.</p>"
    review_cards = "\n".join(f"<li>{path.name}</li>" for path in reviews) or "<li>No sheets need manual review.</li>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Extraction Report</title>
  <style>
    body {{ margin: 0; font-family: Inter, Segoe UI, Arial, sans-serif; background: #f7f1e6; color: #2e2419; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px; }}
    header, section {{ background: #fffdf8; border: 1px solid #e8d7b6; border-radius: 18px; padding: 20px; margin-bottom: 18px; box-shadow: 0 16px 44px rgba(80, 52, 20, .08); }}
    h1, h2 {{ margin: 0 0 12px; font-weight: 700; }}
    .meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }}
    .pill {{ border: 1px solid #e8d7b6; border-radius: 999px; padding: 8px 12px; background: #fbf7ef; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 14px; }}
    figure {{ margin: 0; border: 1px solid #efe2ca; border-radius: 14px; padding: 10px; background: #fbf7ef; }}
    img {{ width: 100%; height: 132px; object-fit: contain; background: repeating-conic-gradient(#eee 0% 25%, #fff 0% 50%) 50% / 18px 18px; border-radius: 10px; }}
    figcaption {{ font-size: 12px; color: #8a7a65; overflow-wrap: anywhere; margin-top: 8px; }}
    code {{ background: #f8efe2; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Image Multi Asset Extractor Report</h1>
      <div class="meta">
        <div class="pill">Category: <strong>{config.category}</strong></div>
        <div class="pill">Prefix: <strong>{config.prefix}</strong></div>
        <div class="pill">Mode: <strong>{"Dry run" if dry_run else "Export"}</strong></div>
        <div class="pill">Manifest items: <strong>{len(items)}</strong></div>
      </div>
    </header>
    <section>
      <h2>Detection Previews</h2>
      <p>Use these images to check whether bounding boxes are finding the correct visual elements before exporting a large batch.</p>
      <div class="grid">{preview_cards}</div>
    </section>
    <section>
      <h2>Output PNG Assets</h2>
      <div class="grid">{output_cards}</div>
    </section>
    <section>
      <h2>Manual Review Needed</h2>
      <ul>{review_cards}</ul>
    </section>
    <section>
      <h2>Next Steps</h2>
      <p>Copy <code>output_png/*.png</code> into your asset library and merge <code>manifest/map_assets.generated.json</code> into your map manifest.</p>
    </section>
  </main>
</body>
</html>
"""
    REPORT_PATH.write_text(html, encoding="utf-8")
    logging.info("HTML report written: %s", REPORT_PATH)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract 2.5D map assets from sprite sheets and output transparent PNG files.")
    parser.add_argument("--config", type=Path, default=BASE_DIR / "config.json", help="Path to config JSON.")
    parser.add_argument("--input", type=Path, default=INPUT_DIR, help="Input sprite-sheet directory.")
    parser.add_argument("--prefix", type=str, default="", help="Override filename prefix/subCategory.")
    parser.add_argument("--category", type=str, default="", help="Override manifest category.")
    parser.add_argument("--check-env", action="store_true", help="Print dependency and NVIDIA CUDA status, then exit.")
    parser.add_argument("--allow-cpu", action="store_true", help="Allow CPU-only processing even when config requires NVIDIA GPU.")
    parser.add_argument("--preset", type=str, default="", help="Apply a named preset from presets.json.")
    parser.add_argument("--list-presets", action="store_true", help="List available preset names, then exit.")
    parser.add_argument("--dry-run", action="store_true", help="Only detect boxes and generate report previews; do not export PNG assets.")
    parser.add_argument("--no-report", action="store_true", help="Skip HTML report generation.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_presets:
        presets = load_presets()
        print("\n".join(sorted(presets)) if presets else "No presets found.")
        return 0
    config = load_config(args.config, args.preset)
    if args.prefix:
        config = ExtractorConfig(**{**config.__dict__, "prefix": slugify(args.prefix)})
    if args.category:
        config = ExtractorConfig(**{**config.__dict__, "category": args.category})
    if args.check_env:
        print(json.dumps(check_environment(config, args.allow_cpu), ensure_ascii=False, indent=2))
        return 0
    setup_logging()
    ensure_directories()
    enforce_environment(config, args.allow_cpu)

    input_dir = args.input
    input_dir.mkdir(parents=True, exist_ok=True)
    sheets = sorted(path for path in input_dir.iterdir() if path.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not sheets:
        logging.warning("No PNG/JPG/WEBP sheets found in %s", input_dir)
        if not args.dry_run:
            write_manifest([])
        return 0

    next_index = next_asset_index(config.prefix)
    manifest_items: list[dict[str, Any]] = []
    for sheet in sheets:
        next_index, sheet_items = process_sheet(sheet, config, next_index, args.dry_run)
        manifest_items.extend(sheet_items)

    if not args.dry_run:
        write_manifest(manifest_items)
    reviewed_count = len(list(REVIEW_DIR.glob("*")))
    write_run_summary(config, manifest_items, reviewed_count)
    if not args.no_report:
        write_html_report(config, manifest_items, args.dry_run)
    logging.info("Done. Extracted %s assets. Review folder: %s", len(manifest_items), REVIEW_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
