"""Apply the approved line-wobble MP4's measured motion to any MOVIC illustration.

The 24 motion states are extracted from the user's approved 3-second/30fps
video. Only the residual, ink-centered local displacement is transferred;
common vertical/horizontal motion is removed. Watercolor, frame and paper
remain in the exact same position throughout the video. This approximates the *movement*, not the video generator's
original hand-drawn reconstruction and appearance.
"""
import base64
import json
import zlib
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from extract_approved_mp4_motion import DEFAULT_MP4, extract

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = (PROJECT_ROOT / "assets/references/line-boil/standard-motion-profile.json")


@lru_cache(maxsize=2)
def load_profile(path=PROFILE_PATH):
    path = Path(path)
    # The uploaded case-sensitive MP4 is the source of truth. Never use a
    # stale JSON extracted from a different video.
    profile = extract(DEFAULT_MP4)
    states = int(profile["reference_video"]["motion_states"])
    height = int(profile["grid_height"])
    width = int(profile["grid_width"])
    if states != 24 or abs(float(profile["reference_video"]["seconds"]) - 3) > .05:
        raise ValueError("Expected 24-state, 3-second approved MP4")
    starts = profile["reference_video"]["detected_motion_starts"]
    if len(starts) != states or starts[0] != 0 or starts != sorted(starts):
        raise ValueError("Motion starts must contain exactly 24 ordered states")
    buf = zlib.decompress(base64.b64decode(profile["motion_blob"], validate=True))
    expected = states * height * width * 2
    if len(buf) != expected:
        raise ValueError(f"Profile data is {len(buf)} bytes; expected {expected}")
    fields = np.frombuffer(buf, np.int8).reshape(states, height, width, 2)
    return profile, fields


def line_ink_mask(source):
    """Return a 2D mask, high on pencil contours, near zero on bare paper."""
    h, w = source.shape[:2]
    shrink = min(1.0, 910 / max(w, 1))
    dst = (round(w * shrink), round(h * shrink))
    low = cv2.resize(source, dst, interpolation=cv2.INTER_AREA) if shrink < 1 else source
    gray = cv2.cvtColor(low, cv2.COLOR_RGB2GRAY).astype(np.float32)
    blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=2.0)
    highpass = np.clip((blur - gray - 5) / 28, 0, 1)
    dx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    sobel = np.clip((cv2.magnitude(dx, dy) - 28) / 170, 0, 1)
    mask = np.maximum(highpass, sobel * 0.83)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=1.0)
    if dst != (w, h):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(mask, 0, 0.98).astype(np.float32)



def stabilize_motion_field(field, ink_weights, max_displacement):
    """Remove whole-frame/camera translation; retain only local line variation.

    Field values are measured at the 455px-wide reference flow resolution.
    Removing the ink-weighted common dx/dy before remapping is critical:
    otherwise a camera bob in the reference can move all lines together.
    """
    if field.ndim != 3 or field.shape[2] != 2:
        raise ValueError("Expected an HxWx2 optical-flow field")
    if max_displacement <= 0:
        raise ValueError("max_displacement must be positive")
    weights = cv2.resize(
        ink_weights.astype(np.float32),
        (field.shape[1], field.shape[0]),
        interpolation=cv2.INTER_AREA,
    )
    total = float(np.sum(weights, dtype=np.float64))
    source = field.astype(np.float32)
    if total > 1e-8:
        offset = (source * weights[..., None]).sum(
            axis=(0, 1), dtype=np.float64
        ) / total
    else:
        offset = source.mean(axis=(0, 1), dtype=np.float64)
    local = source - offset.astype(np.float32)
    # Limit any optical-flow mismatch to a local, hand-drawn-size wobble.
    magnitude = np.linalg.norm(local, axis=2)
    local *= np.minimum(
        1.0, float(max_displacement) / np.maximum(magnitude, 1e-6)
    )[..., None]
    # Clamping can reintroduce small DC shifts; remove those as well.
    if total > 1e-8:
        residual = (local * weights[..., None]).sum(
            axis=(0, 1), dtype=np.float64
        ) / total
    else:
        residual = local.mean(axis=(0, 1), dtype=np.float64)
    return local - residual.astype(np.float32)


def video_frames(source_path, settings, width, height):
    """Yield 180 60fps frames, with 24 measured poses over 3 seconds.

    Source MP4 is read from assets/standard-motion.MP4. Its native frame
    boundaries are mapped proportionally to the 60fps output timeline.
    The repeat from last pose back to pose 0 is the same strength as any
    other state boundary; we make no interpolated crossfade (hand drawn boil).
    """
    if int(settings["fps"]) != 60 or float(settings["duration_seconds"]) != 3:
        raise ValueError("Video standard is 60fps and 3 seconds")
    if settings.get("prevent_global_translation") is not True:
        raise ValueError(
            "MOVIC line-boil delivery must lock the camera and remove "
            "whole-image translation (prevent_global_translation=true)."
        )
    max_px_at_910 = float(settings.get("max_local_wobble_px_at_910", 4.0))
    if not 0 < max_px_at_910 <= 12:
        raise ValueError("max_local_wobble_px_at_910 must be within (0, 12]")
    border_fraction = float(settings.get("fixed_border_fraction", 0.025))
    if not 0 <= border_fraction <= 0.08:
        raise ValueError("fixed_border_fraction must be within [0, 0.08]")
    profile, fields = load_profile()
    source_frame_count = int(profile["reference_video"]["frames"])
    rgb = np.asarray(Image.open(source_path).convert("RGB"))
    ih, iw = rgb.shape[:2]
    scale = min(width / iw, height / ih)
    rw, rh = round(iw * scale), round(ih * scale)
    art = cv2.resize(rgb, (rw, rh), interpolation=cv2.INTER_LANCZOS4)
    base = np.empty((height, width, 3), np.uint8)
    base[:] = np.median(art.reshape(-1, 3)[::200], axis=0).astype(np.uint8)
    offset_x, offset_y = (width - rw) // 2, (height - rh) // 2
    base[offset_y:offset_y+rh, offset_x:offset_x+rw] = art
    ink_weights = line_ink_mask(base)
    # Keep composition, paper background and the hand-drawn frame anchored.
    border_x = round(width * border_fraction)
    border_y = round(height * border_fraction)
    if border_x:
        ink_weights[:, :border_x] = 0.0
        ink_weights[:, width-border_x:] = 0.0
    if border_y:
        ink_weights[:border_y, :] = 0.0
        ink_weights[height-border_y:, :] = 0.0
    alpha = ink_weights[..., None] * float(profile["strength"]["ink_mask_gain"])
    xs, ys = np.meshgrid(np.arange(width, dtype=np.float32),
                         np.arange(height, dtype=np.float32))
    starts = np.asarray(profile["reference_video"]["detected_motion_starts"])
    last_state = -1
    result = base
    for frame_index in range(180):
        source_frame = min(source_frame_count - 1, frame_index * source_frame_count // 180)
        state = int(np.searchsorted(starts, source_frame, side="right") - 1)
        if state != last_state:
            if state == 0:
                result = base
            else:
                # The profile was measured on a 455x256 reference image.
                raw_field = fields[state].astype(np.float32) / float(profile["quantization"])
                local = stabilize_motion_field(
                    raw_field,
                    ink_weights,
                    max_displacement=max_px_at_910 / 2.0,
                )
                field = cv2.resize(
                    local, (width, height), interpolation=cv2.INTER_CUBIC
                )
                mx = xs - field[..., 0] * (width / float(profile["flow_source_width"])) * float(profile["strength"]["flow_gain"])
                my = ys - field[..., 1] * (height / float(profile["flow_source_height"])) * float(profile["strength"]["flow_gain"])
                warped = cv2.remap(base, mx, my, interpolation=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REFLECT101)
                result = np.clip(base.astype(np.float32) * (1-alpha)
                                 + warped.astype(np.float32) * alpha,0,255).astype(np.uint8)
            last_state = state
        yield result