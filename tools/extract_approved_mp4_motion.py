#!/usr/bin/env python3
"""Derive MOVIC pencil motion from the actual uppercase .MP4 in assets/.

The approved video is assets/standard-motion.MP4 (case-sensitive). Check its
Git blob SHA-1 to avoid accidentally analysing a different render. The final
output is still a 3840x2160, 60fps, 3s H.264 MP4, never a GIF.

Usage:
    python tools/extract_approved_mp4_motion.py
    python tools/extract_approved_mp4_motion.py --check
"""
import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MP4 = REPO / "assets/standard-motion.MP4"
DEFAULT_PROFILE = REPO / "assets/references/line-boil/standard-motion-profile.json"
EXPECTED_GIT_BLOB_SHA1 = "5809b7915eb520b6724a85eaf860e5793511f36f"
GRID_HEIGHT, GRID_WIDTH = 15, 27
QUANTIZATION = 8


def git_blob_sha1(binary):
    header = b"blob " + str(len(binary)).encode("ascii") + b"\0"
    return hashlib.sha1(header + binary).hexdigest()


def select_redraw_starts(gray_frames, fps):
    """Identify the strongest 23 redraw boundaries (24 total states).

    Prioritize sudden real changes over re-encoding/compression noise, with
    a minimum gap so consecutive frames of one motion are not double counted.
    """
    n = len(gray_frames)
    deltas = np.array([
        float(np.mean(cv2.absdiff(gray_frames[i-1], gray_frames[i])))
        for i in range(1, n)
    ], np.float64)
    # States change approximately every 1/8 second. At 30fps this is 3-4
    # frames; at 60fps 7-8. Allow some deviation but avoid adjacent peaks.
    min_gap = max(2, round(fps / 16))
    minimum_signal = max(1.8, float(np.median(deltas)) + 1.0)
    selected = []
    for index in np.argsort(deltas)[::-1]:
        boundary = int(index + 1)
        if deltas[index] < minimum_signal:
            break
        if all(abs(boundary - previous) >= min_gap for previous in selected):
            selected.append(boundary)
        if len(selected) == 23:
            break
    if len(selected) != 23:
        raise ValueError(
            f"Expected 23 strong redraw boundaries (24 poses); found "
            f"{len(selected)}, fps={fps:.3f}, threshold={minimum_signal:.3f}, "
            f"median={np.median(deltas):.3f}, max={deltas.max():.3f}. "
            "Do not silently substitute a different motion profile."
        )
    return [0] + sorted(selected)


def extract(input_path=DEFAULT_MP4, expected_git_blob_sha1=EXPECTED_GIT_BLOB_SHA1):
    input_path = Path(input_path)
    binary = input_path.read_bytes()
    actual_blob = git_blob_sha1(binary)
    if actual_blob != expected_git_blob_sha1:
        raise ValueError(
            f"Incorrect approved MP4: Git blob SHA-1 is {actual_blob}, "
            f"expected {expected_git_blob_sha1} ({input_path})"
        )
    sha256 = hashlib.sha256(binary).hexdigest()
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError("Cannot open approved assets/standard-motion.MP4")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or source_width <= 0 or source_height <= 0:
        cap.release()
        raise ValueError("Invalid reference MP4 video metadata")
    gray_frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(
            cv2.resize(frame, (455, 256), interpolation=cv2.INTER_AREA),
            cv2.COLOR_BGR2GRAY
        )
        gray_frames.append(gray)
        if len(gray_frames) > 300:
            cap.release()
            raise ValueError("Unexpectedly long reference MP4")
    cap.release()
    count = len(gray_frames)
    duration = count / fps
    if count < 24 or not (2.95 <= duration <= 3.05):
        raise ValueError(
            f"Expected 3-second MP4: {count} frames at {fps}fps = {duration}s"
        )
    starts = select_redraw_starts(gray_frames, fps)
    original = gray_frames[0]
    motion = []
    for i in starts:
        field = cv2.calcOpticalFlowFarneback(
            original, gray_frames[i], None, 0.5, 5, 19, 3, 5, 1.1, 0
        )
        field = cv2.GaussianBlur(field, (0, 0), sigmaX=1.8)
        field = cv2.resize(field, (GRID_WIDTH, GRID_HEIGHT),
                           interpolation=cv2.INTER_AREA)
        motion.append(np.clip(np.rint(field * QUANTIZATION),
                              -96, 96).astype(np.int8))
    compressed = zlib.compress(np.asarray(motion).tobytes(), level=9)
    return {
        "version": 2,
        "title": "MOVIC approved MP4 line-boil motion profile",
        "reference_file": "assets/standard-motion.MP4",
        "reference_git_blob_sha1": actual_blob,
        "reference_sha256": sha256,
        "reference_video": {
            "width": source_width, "height": source_height,
            "fps": fps, "frames": count, "seconds": duration,
            "codec": "h264", "detected_motion_starts": starts,
            "motion_states": 24
        },
        "grid_width": GRID_WIDTH, "grid_height": GRID_HEIGHT,
        "flow_source_width": 455, "flow_source_height": 256,
        "quantization": QUANTIZATION,
        "data_format": "int8 displacement dx dy per grid point; 24 poses, zlib+base64",
        "motion_blob": base64.b64encode(compressed).decode("ascii"),
        "strength": {
            "flow_gain": 1.0, "ink_mask_gain": 0.85,
            "detail_noise_gain": 0.08
        },
        "output": {
            "width": 3840, "height": 2160, "fps": 60,
            "duration_seconds": 3, "frame_count": 180,
            "change_rate_hz": 8
        },
        "note": "Regenerated from real assets/standard-motion.MP4; optical-flow approximation."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", nargs="?", type=Path, default=DEFAULT_MP4)
    parser.add_argument("--output", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--check", action="store_true",
                        help="Validate source against stored motion profile")
    parser.add_argument("--stdout-json", action="store_true",
                        help="Print compact profile to stdout for review")
    args = parser.parse_args()
    result = extract(args.video)
    if args.stdout_json:
        print("MOTION_PROFILE_BEGIN")
        print(json.dumps(result, separators=(",", ":"), ensure_ascii=False))
        print("MOTION_PROFILE_END")
    elif args.check:
        stored = json.loads(args.output.read_text(encoding="utf-8"))
        if stored != result:
            parser.exit(1, "ERROR: saved profile differs from uploaded MP4\n")
        print("PASS: reference assets/standard-motion.MP4 matches profile")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
