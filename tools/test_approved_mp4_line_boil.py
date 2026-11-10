#!/usr/bin/env python3
"""Tests ensuring the approved 30fps MP4's 24-state 8Hz wobble drives output."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from approved_mp4_line_boil import load_profile, video_frames
from extract_approved_mp4_motion import EXPECTED_SHA256

PROFILE = ROOT / "assets/references/line-boil/standard-motion-profile.json"
MP4 = ROOT / "assets/references/line-boil/standard-motion.mp4"


class Mp4BaselineTests(unittest.TestCase):
    def test_motion_profile_is_from_the_approved_mp4(self):
        profile, data = load_profile(PROFILE)
        self.assertEqual(profile["reference_sha256"], EXPECTED_SHA256)
        self.assertEqual(data.shape, (24, 15, 27, 2))
        self.assertEqual(profile["reference_video"]["frames"], 90)
        self.assertEqual(profile["reference_video"]["fps"], 30)
        changes = profile["reference_video"]["detected_motion_starts"]
        holds = np.diff(changes + [90])
        self.assertEqual(len(changes), 24)
        self.assertEqual(set(holds.tolist()), {3, 4})
        self.assertEqual(sum(holds), 90)
        self.assertGreater(int(np.abs(data).max()), 0)

    def test_approved_source_file_if_present(self):
        # GitHub binary MP4 upload may be a separate user action.
        if MP4.is_file():
            self.assertEqual(hashlib.sha256(MP4.read_bytes()).hexdigest(),
                             EXPECTED_SHA256)

    def test_60fps_frame_holds_and_paper_is_anchored(self):
        with TemporaryDirectory() as tmp:
            picture = Path(tmp) / "test.png"
            img = Image.new("RGB", (320, 180), (242, 226, 212))
            d = ImageDraw.Draw(img)
            d.ellipse((65, 28, 240, 155), outline=(45, 39, 39), width=5)
            d.line((35, 100, 280, 95), fill=(60, 51, 46), width=4)
            img.save(picture)
            snapshots = {}
            for i, frame in enumerate(
                    video_frames(picture, {"fps": 60, "duration_seconds": 3}, 320, 180)):
                if i in (0, 1, 7, 8, 15, 16, 178, 179):
                    snapshots[i] = frame.copy()
            self.assertEqual(i + 1, 180)
            self.assertTrue(np.array_equal(snapshots[0], snapshots[7]))
            self.assertTrue(np.array_equal(snapshots[8], snapshots[15]))
            self.assertFalse(np.array_equal(snapshots[0], snapshots[8]))
            self.assertTrue(np.array_equal(snapshots[178], snapshots[179]))
            self.assertTrue(np.array_equal(
                snapshots[0][5, 5], snapshots[8][5, 5]
            ))


if __name__ == "__main__":
    unittest.main()
