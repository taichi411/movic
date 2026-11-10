#!/usr/bin/env python3
"""MOVIC deterministic line-boil renderer for a single still illustration.

Only the dark pencil detail is locally displaced; most paper and pale colors
stay anchored. The result is an approximation of the visual reference GIF,
NOT the original hidden generation algorithm used to create that GIF.

Usage:
  python tools/line_boil.py assets/scene01.png --output scene01.gif
  python tools/line_boil.py assets/scene01.png --output scene01.mp4
  python tools/line_boil.py assets/scene01.png --output scene01.gif --width 960 --height 540
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from reference_line_boil import generate_frames as reference_motion_frames


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "assets/references/line-boil/standard.json"


def load_config(path):
    settings = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("fps", "boil_fps", "duration_seconds", "horizontal_amplitude_px",
                "vertical_amplitude_px", "grid_columns", "grid_rows", "seed"):
        if key not in settings:
            raise ValueError("Missing setting: " + key)
    if settings["fps"] <= 0 or settings["boil_fps"] <= 0:
        raise ValueError("fps and boil_fps must be positive")
    if settings["duration_seconds"] <= 0:
        raise ValueError("duration_seconds must be positive")
    return settings


def create_base(path, width, height):
    image = Image.open(path).convert("RGB")
    source = np.asarray(image)
    ih, iw = source.shape[:2]
    scale = min(width / iw, height / ih)
    rw, rh = round(iw * scale), round(ih * scale)
    resized = cv2.resize(source, (rw, rh), interpolation=cv2.INTER_LANCZOS4)
    paper = np.median(resized.reshape(-1, 3)[::200], axis=0).astype(np.uint8)
    base = np.empty((height, width, 3), dtype=np.uint8)
    base[:] = paper
    x, y = (width - rw) // 2, (height - rh) // 2
    base[y:y + rh, x:x + rw] = resized
    return base


def detail_mask(base, settings):
    """Highlight gray/dark ink while keeping light paper/flat colors stable."""
    gray = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY)
    smooth = cv2.GaussianBlur(gray, (0, 0), sigmaX=4)
    edge = np.clip(
        (smooth.astype(np.float32) - gray.astype(np.float32) - 2) / 24,
        0, 1
    )
    edge = cv2.GaussianBlur(edge, (0, 0), sigmaX=1.1)
    dark = np.clip((170 - gray.astype(np.float32)) / 75, 0, .8)
    mask = np.maximum(edge * .90, dark * .45)
    return np.clip(mask * settings["line_blend"] + settings["background_blend"],
                   0, 1)[:, :, None].astype(np.float32)


def frames(source_path, settings, width, height):
    if settings.get("motion_mode") == "reference_gif_optical_flow":
        reference = DEFAULT_CONFIG.parent / settings.get(
            "reference_file", "line-boil-standard.GIF"
        )
        yield from reference_motion_frames(
            source_path, settings, width, height, reference
        )
        return
    # Legacy algorithm retained for explicit experimental configs only.
    base = create_base(source_path, width, height)
    mask = detail_mask(base, settings)
    xx, yy = np.meshgrid(np.arange(width, dtype=np.float32),
                         np.arange(height, dtype=np.float32))
    frames_total = round(settings["duration_seconds"] * settings["fps"])
    cache_step, cached = -1, None
    for i in range(frames_total):
        # No cumulative warping; same time and seed -> same source frame.
        tick = (i * settings["boil_fps"]) // settings["fps"]
        if tick != cache_step:
            rng = np.random.default_rng(settings["seed"] + int(tick))
            shape = (settings["grid_rows"], settings["grid_columns"])
            dx = cv2.resize(rng.standard_normal(shape).astype(np.float32),
                            (width, height), interpolation=cv2.INTER_CUBIC)
            dy = cv2.resize(rng.standard_normal(shape).astype(np.float32),
                            (width, height), interpolation=cv2.INTER_CUBIC)
            mapped = cv2.remap(
                base,
                xx + dx * settings["horizontal_amplitude_px"] * width / 1920,
                yy + dy * settings["vertical_amplitude_px"] * height / 1080,
                cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101
            )
            cached = np.clip(base.astype(np.float32) * (1 - mask) +
                             mapped.astype(np.float32) * mask,
                             0, 255).astype(np.uint8)
            cache_step = tick
        yield cached


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Single still PNG/JPEG")
    parser.add_argument("--output", type=Path, required=True, help="GIF or MP4")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error("Input image not found: " + str(args.input))
    if args.width <= 0 or args.height <= 0:
        parser.error("width/height must be positive")
    settings = load_config(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stream = frames(args.input, settings, args.width, args.height)
    suffix = args.output.suffix.lower()
    if suffix == ".gif":
        # GIFs are 256-color by design; MP4 preserves gradients better.
        images = [Image.fromarray(f, "RGB") for f in stream]
        images[0].save(args.output, save_all=True, append_images=images[1:],
                       loop=0, duration=round(1000 / settings["fps"]),
                       optimize=False)
    elif suffix == ".mp4":
        writer = cv2.VideoWriter(str(args.output),
                                 cv2.VideoWriter_fourcc(*"mp4v"),
                                 settings["fps"], (args.width, args.height))
        if not writer.isOpened():
            raise RuntimeError("Failed to open MP4 writer")
        try:
            for frame in stream:
                writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        finally:
            writer.release()
    else:
        parser.error("output extension must be .gif or .mp4")
    print("Wrote " + str(args.output))


if __name__ == "__main__":
    main()
