#!/usr/bin/env python3
"""Regenerate MOVIC's approved-MP4 motion profile from the original MP4.

The user-provided original must match the immutable SHA-256 fingerprint.
The extractor records 24 optical-flow motion states at ~8Hz over 3 seconds.
The resulting JSON may be compared against the checked-in profile.
"""
import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

import cv2
import numpy as np

EXPECTED_SHA256 = "b9a7d6bbbc040aeb5b1e74843366282e0f7ee20e5273b17a435524e16140c611"
REPO = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = REPO / "assets/references/line-boil/standard-motion-profile.json"
GRID_HEIGHT, GRID_WIDTH = 15, 27
QUANTIZATION = 8


def extract(input_path):
    binary = Path(input_path).read_bytes()
    actual_sha = hashlib.sha256(binary).hexdigest()
    if actual_sha != EXPECTED_SHA256:
        raise ValueError(
            f"Wrong source MP4; expected sha256 {EXPECTED_SHA256}, got {actual_sha}"
        )
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError("Cannot read approved MP4")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    cap.release()
    height, width = frames[0].shape if frames else (0, 0)
    if (width, height) != (910, 512) or len(frames) != 90 or abs(fps - 30) > 0.01:
        raise ValueError(
            f"Unexpected MP4 metadata: {(width,height)} {len(frames)} frames, {fps}fps"
        )
    change = [np.mean(cv2.absdiff(frames[i - 1], frames[i]))
              for i in range(1, len(frames))]
    starts = [0] + [i for i, delta in enumerate(change, 1) if delta > 4]
    if len(starts) != 24:
        raise ValueError(f"Expected 24 motion changes/states, found {len(starts)}")
    original = cv2.resize(frames[0], (455, 256), interpolation=cv2.INTER_AREA)
    motion = []
    for idx in starts:
        frame = cv2.resize(frames[idx], (455, 256), interpolation=cv2.INTER_AREA)
        field = cv2.calcOpticalFlowFarneback(
            original, frame, None, 0.5, 5, 19, 3, 5, 1.1, 0
        )
        field = cv2.GaussianBlur(field, (0, 0), sigmaX=1.8)
        field = cv2.resize(
            field, (GRID_WIDTH, GRID_HEIGHT), interpolation=cv2.INTER_AREA
        )
        motion.append(
            np.clip(np.rint(field * QUANTIZATION), -96, 96).astype(np.int8)
        )
    data = zlib.compress(np.asarray(motion).tobytes(), level=9)
    return {
        "version": 1,
        "title": "MOVIC approved MP4 line boil motion profile",
        "reference_file": "standard-motion.mp4",
        "reference_sha256": EXPECTED_SHA256,
        "reference_video": {
            "width": 910, "height": 512, "fps": 30, "frames": 90,
            "seconds": 3, "codec": "h264",
            "detected_motion_starts": starts, "motion_states": 24
        },
        "grid_width": GRID_WIDTH, "grid_height": GRID_HEIGHT,
        "flow_source_width": 455, "flow_source_height": 256,
        "quantization": QUANTIZATION,
        "data_format": "int8, displacement dx dy per grid point, 24 states, zlib+base64, row-major",
        "motion_blob": base64.b64encode(data).decode("ascii"),
        "strength": {"flow_gain": 1.0, "ink_mask_gain": 0.85, "detail_noise_gain": 0.08},
        "output": {
            "width": 3840, "height": 2160, "fps": 60,
            "duration_seconds": 3, "frame_count": 180, "change_rate_hz": 8
        },
        "note": (
            "Video-derived optical-flow approximate motion. Texture redraw "
            "not exactly reproducible; original MP4 binary not in repo unless explicitly uploaded later."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Original approved MP4")
    parser.add_argument("--output", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument(
        "--check", action="store_true",
        help="Compare to existing checked-in profile without writing"
    )
    args = parser.parse_args()
    result = extract(args.video)
    if args.check:
        current = json.loads(args.output.read_text(encoding="utf-8"))
        if current != result:
            parser.exit(1, "ERROR: motion profile differs from reference video\n")
        print("PASS: source MP4 recreates the committed profile")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
        print(f"Saved reference profile: {args.output}")


if __name__ == "__main__":
    main()
