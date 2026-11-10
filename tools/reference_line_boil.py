"""Reference-GIF-driven line boil, derived from the actual MOVIC GIF.

Instead of random noise, extract optical-flow displacement fields from the
nine drawings in line-boil-standard.GIF and apply those fields to line detail
of the supplied illustration. This is a deterministic approximation; the
GIF's original generative redraw algorithm cannot be recovered.
"""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@lru_cache(maxsize=2)
def reference_fields(reference_path):
    """Return the nine displacement maps measured relative to reference pose 0.

    The approved GIF must have nine distinct frames, each held for 180 ms.
    Cache the motion templates; they are independent of the artwork.
    """
    reference_path = Path(reference_path)
    if not reference_path.is_file():
        raise FileNotFoundError(f"Reference GIF not found: {reference_path}")
    gif = Image.open(reference_path)
    images, durations = [], []
    for i in range(gif.n_frames):
        gif.seek(i)
        images.append(cv2.cvtColor(np.asarray(gif.convert("RGB")),
                                    cv2.COLOR_RGB2GRAY))
        durations.append(gif.info.get("duration"))
    if len(images) != 9 or durations != [180] * 9:
        raise ValueError(
            f"Reference GIF mismatch: {len(images)} frames, "
            f"durations={durations}; expected nine frames at 180 ms each."
        )
    fields = [np.zeros((*images[0].shape, 2), dtype=np.float32)]
    for frame in images[1:]:
        flow = cv2.calcOpticalFlowFarneback(
            images[0], frame, None, 0.5, 4, 21, 3, 5, 1.2, 0
        )
        # Smooth unreliable pixel-to-pixel matches but keep the local wobble.
        flow = cv2.GaussianBlur(flow, (0, 0), sigmaX=2.0)
        fields.append(np.clip(flow, -9.0, 9.0).astype(np.float32))
    return tuple(fields)


def ink_detail_mask(base):
    """Prefer graphite outlines over pale watercolor fills and paper texture.

    Thresholds are applied at up to 960px wide; the mask is then scaled to
    the output dimensions so 4K and HD produce comparable motion weighting.
    """
    gray = cv2.cvtColor(base, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    scale = min(1.0, 960.0 / max(height, width))
    if scale < 1:
        gray_small = cv2.resize(
            gray, (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA
        )
    else:
        gray_small = gray
    blur = cv2.GaussianBlur(gray_small, (0, 0), 1.9)
    detail = np.clip(
        (blur.astype(np.float32) - gray_small.astype(np.float32) - 10) / 38,
        0, 1
    )
    gx = cv2.Sobel(gray_small, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray_small, cv2.CV_32F, 0, 1, ksize=3)
    edge = np.clip((np.hypot(gx, gy) - 70) / 220, 0, 1)
    mask = np.maximum(detail, edge * 0.90)
    mask = cv2.dilate(
        mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    )
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=1.0)
    if mask.shape != (height, width):
        mask = cv2.resize(mask, (width, height), cv2.INTER_LINEAR)
    return np.clip(mask, 0, 0.96).astype(np.float32)


def generate_frames(source_path, settings, width, height, reference_path):
    """Stream a fixed-duration MP4's reference-motion frames.

    The nine approved reference poses are repeated twice over 3 seconds:
    18 holds / 180 output frames = 10 frames (166.7 ms) per pose at 60fps.
    This differs by 7.4% from the GIF's 180 ms native timing, but guarantees
    the 3-second loop repeats the entire nine-pose cycle without phase drift.
    """
    image = Image.open(source_path).convert("RGB")
    iw, ih = image.size
    scale = min(width / iw, height / ih)
    rw, rh = round(iw * scale), round(ih * scale)
    art = cv2.resize(
        np.asarray(image), (rw, rh), interpolation=cv2.INTER_LANCZOS4
    )
    base = np.empty((height, width, 3), dtype=np.uint8)
    base[:] = np.median(art.reshape(-1, 3)[::200], axis=0).astype(np.uint8)
    x, y = (width - rw) // 2, (height - rh) // 2
    base[y:y + rh, x:x + rw] = art

    fields = reference_fields(str(Path(reference_path).resolve()))
    ref_h, ref_w = fields[0].shape[:2]
    mask = ink_detail_mask(base)
    alpha = (mask * float(settings.get("line_blend", 0.94)))[..., None]
    xx, yy = np.meshgrid(
        np.arange(width, dtype=np.float32),
        np.arange(height, dtype=np.float32)
    )
    gain = float(settings.get("reference_motion_gain", 0.75))
    if not 0 <= gain <= 2:
        raise ValueError("reference_motion_gain must be between 0 and 2")
    fps = int(settings["fps"])
    total_frames = round(float(settings["duration_seconds"]) * fps)
    if total_frames < 18:
        raise ValueError("At least 18 output frames are needed for two cycles")

    last_pose, result = -1, None
    for index in range(total_frames):
        pose = (index * 18 // total_frames) % len(fields)
        if pose != last_pose:
            if pose == 0:
                result = base
            else:
                field = cv2.resize(
                    fields[pose], (width, height),
                    interpolation=cv2.INTER_CUBIC
                )
                map_x = xx - field[..., 0] * width / ref_w * gain
                map_y = yy - field[..., 1] * height / ref_h * gain
                warped = cv2.remap(
                    base, map_x, map_y, cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REFLECT101
                )
                # Background is anchored; only detected ink/edges shift.
                result = np.clip(
                    base.astype(np.float32) * (1 - alpha)
                    + warped.astype(np.float32) * alpha,
                    0, 255
                ).astype(np.uint8)
            last_pose = pose
        yield result
