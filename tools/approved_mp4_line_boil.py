"""Apply the approved line-wobble MP4's measured motion to any MOVIC illustration.

The 24 motion states are extracted from the user's approved 3-second/30fps
video. The profile is independent of the image subject; line-detail of the
input is warped by these measured fields while watercolor and paper are
left anchored. This approximates the *movement*, not the video generator's
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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = (PROJECT_ROOT / "assets/references/line-boil/standard-motion-profile.json")


@lru_cache(maxsize=2)
def load_profile(path=PROFILE_PATH):
    path = Path(path)
    profile = json.loads(path.read_text(encoding="utf-8"))
    states = int(profile["reference_video"]["motion_states"])
    height = int(profile["grid_height"])
    width = int(profile["grid_width"])
    if (states, profile["reference_video"]["frames"],
            profile["reference_video"]["fps"]) != (24, 90, 30):
        raise ValueError("Unexpected reference MP4 profile timing")
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


def video_frames(source_path, settings, width, height):
    """Yield 180 60fps frames, with 24 measured poses over 3 seconds.

    At 30fps source: pose starts [0,4,8,12,...,87] and holds 3 or 4 frames.
    At 60fps output: each source frame is doubled, so holds become 6 or 8.
    The repeat from last pose back to pose 0 is the same strength as any
    other state boundary; we make no interpolated crossfade (hand drawn boil).
    """
    if int(settings["fps"]) != 60 or float(settings["duration_seconds"]) != 3:
        raise ValueError("Video standard is 60fps and 3 seconds")
    profile, fields = load_profile()
    rgb = np.asarray(Image.open(source_path).convert("RGB"))
    ih, iw = rgb.shape[:2]
    scale = min(width / iw, height / ih)
    rw, rh = round(iw * scale), round(ih * scale)
    art = cv2.resize(rgb, (rw, rh), interpolation=cv2.INTER_LANCZOS4)
    base = np.empty((height, width, 3), np.uint8)
    base[:] = np.median(art.reshape(-1, 3)[::200], axis=0).astype(np.uint8)
    offset_x, offset_y = (width - rw) // 2, (height - rh) // 2
    base[offset_y:offset_y+rh, offset_x:offset_x+rw] = art
    alpha = line_ink_mask(base)[..., None] * float(profile["strength"]["ink_mask_gain"])
    flow_scale = float(profile["strength"]["flow_gain"]) / float(profile["quantization"])
    xs, ys = np.meshgrid(np.arange(width, dtype=np.float32),
                         np.arange(height, dtype=np.float32))
    starts = np.asarray(profile["reference_video"]["detected_motion_starts"])
    last_state = -1
    result = base
    for frame_index in range(180):
        source_frame = frame_index // 2
        state = int(np.searchsorted(starts, source_frame, side="right") - 1)
        if state != last_state:
            if state == 0:
                result = base
            else:
                # The profile was measured on a 455x256 reference image.
                field = cv2.resize(fields[state].astype(np.float32), (width,height),
                                   interpolation=cv2.INTER_CUBIC)
                mx = xs - field[..., 0] * (width / float(profile["flow_source_width"])) * flow_scale
                my = ys - field[..., 1] * (height / float(profile["flow_source_height"])) * flow_scale
                warped = cv2.remap(base, mx, my, interpolation=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REFLECT101)
                result = np.clip(base.astype(np.float32) * (1-alpha)
                                 + warped.astype(np.float32) * alpha,0,255).astype(np.uint8)
            last_state = state
        yield result