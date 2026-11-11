#!/usr/bin/env python3
"""Ensure new MOVIC standard reads the actual uppercase .MP4 (not stale JSON)."""
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

from approved_mp4_line_boil import load_profile, video_frames, stabilize_motion_field
from extract_approved_mp4_motion import DEFAULT_MP4, EXPECTED_GIT_BLOB_SHA1, git_blob_sha1

REFERENCE_FILE = ROOT / "assets/standard-motion.MP4"
PROFILE = ROOT / "assets/references/line-boil/standard-motion-profile.json"
CONFIG = ROOT / "assets/references/line-boil/standard.json"


class ApprovedMp4Tests(unittest.TestCase):
    def test_actual_video_is_loaded_with_exact_case(self):
        self.assertEqual(DEFAULT_MP4, REFERENCE_FILE)
        self.assertTrue(REFERENCE_FILE.is_file(), "Missing assets/standard-motion.MP4")
        blob_sha = git_blob_sha1(REFERENCE_FILE.read_bytes())
        self.assertEqual(blob_sha, EXPECTED_GIT_BLOB_SHA1)
        config = json.loads(CONFIG.read_text("utf-8"))
        self.assertEqual(config["reference_file"], "assets/standard-motion.MP4")
        self.assertEqual(config["reference_git_blob_sha1"], blob_sha)

    def test_approved_mp4_drives_motion_profile(self):
        profile, data = load_profile(PROFILE)
        self.assertEqual(profile["reference_file"], "assets/standard-motion.MP4")
        self.assertEqual(profile["reference_git_blob_sha1"], EXPECTED_GIT_BLOB_SHA1)
        self.assertEqual(data.shape, (24, 15, 27, 2))
        self.assertEqual(profile["reference_video"]["motion_states"], 24)
        self.assertAlmostEqual(profile["reference_video"]["seconds"], 3, places=1)
        starts = profile["reference_video"]["detected_motion_starts"]
        self.assertEqual(len(starts), 24)
        self.assertEqual(starts[0], 0)
        self.assertEqual(starts, sorted(starts))
        self.assertGreater(int(np.abs(data).max()), 0)
        # Prevent stale data from a previous reference video being checked in.
        stored = json.loads(PROFILE.read_text("utf-8"))
        self.assertEqual(stored["reference_sha256"], profile["reference_sha256"])
        self.assertEqual(stored["reference_git_blob_sha1"], profile["reference_git_blob_sha1"])
        self.assertEqual(stored["motion_blob"], profile["motion_blob"])

    def test_60fps_three_second_video_preserves_background(self):
        profile, _ = load_profile()
        starts = profile["reference_video"]["detected_motion_starts"]
        count = profile["reference_video"]["frames"]
        first_transition = min(179, (starts[1] * 180 + count - 1) // count)
        with TemporaryDirectory() as d:
            source = Path(d) / "sample.png"
            image = Image.new("RGB", (320, 180), (242, 226, 212))
            drawer = ImageDraw.Draw(image)
            drawer.ellipse((65, 28, 240, 155), outline=(45, 39, 39), width=5)
            drawer.line((35, 100, 280, 95), fill=(60, 51, 46), width=4)
            image.save(source)
            images = list(video_frames(source, {"fps": 60, "duration_seconds": 3, "prevent_global_translation": True, "max_local_wobble_px_at_910": 4.0, "fixed_border_fraction": 0.025}, 320, 180))
            self.assertEqual(len(images), 180)
            self.assertTrue(np.array_equal(images[0], images[first_transition - 1]))
            self.assertFalse(np.array_equal(images[0], images[first_transition]))
            self.assertTrue(np.array_equal(images[0][5, 5],
                                           images[first_transition][5, 5]))
            self.assertGreater(np.mean(np.abs(images[0].astype(np.int16)
                                            - images[first_transition].astype(np.int16))), 0.01)


    def test_full_frame_vertical_translation_is_removed(self):
        """A camera moving up/down must not move the drawing."""
        field = np.zeros((15, 27, 2), np.float32)
        field[..., 0] = -1.7
        field[..., 1] = 7.0
        weights = np.ones((180, 320), np.float32)
        stabilized = stabilize_motion_field(field, weights, 2.0)
        self.assertLess(float(np.max(np.abs(stabilized))), 1e-5)

    def test_local_pencil_variation_remains_after_camera_lock(self):
        flow = np.zeros((15, 27, 2), np.float32)
        x = np.linspace(-1.6, 1.6, 27, dtype=np.float32)
        flow[:, :, 1] = x[None, :] + 3.4  # local wobble + uniform bob
        weights = np.ones((180, 320), np.float32)
        result = stabilize_motion_field(flow, weights, 2.0)
        self.assertGreater(float(np.std(result[..., 1])), 0.3)
        self.assertLess(float(abs(np.mean(result[..., 1]))), 1e-4)
        self.assertLess(float(np.max(np.abs(result))), 2.1)

    def test_frame_and_paper_positions_are_frozen(self):
        with TemporaryDirectory() as d:
            source = Path(d) / "sample.png"
            im = Image.new("RGB", (320, 180), (242, 226, 212))
            painter = ImageDraw.Draw(im)
            painter.rectangle((4, 3, 315, 175), outline=(39, 37, 38), width=2)
            painter.ellipse((60, 30, 220, 152), outline=(40, 38, 38), width=4)
            im.save(source)
            config = {
                "fps": 60, "duration_seconds": 3,
                "prevent_global_translation": True,
                "max_local_wobble_px_at_910": 4.0,
                "fixed_border_fraction": 0.025,
            }
            generator = video_frames(source, config, 320, 180)
            baseline = next(generator)
            for i, frame in enumerate(generator, 1):
                if i % 7 == 0:
                    # All four sides of the illustrated frame stay fixed.
                    self.assertTrue(np.array_equal(frame[:4], baseline[:4]))
                    self.assertTrue(np.array_equal(frame[-4:], baseline[-4:]))
                    self.assertTrue(np.array_equal(frame[:, :8], baseline[:, :8]))
                    self.assertTrue(np.array_equal(frame[:, -8:], baseline[:, -8:]))
                    self.assertTrue(np.array_equal(frame[15, 15], baseline[15, 15]))

    def test_camera_lock_is_required_for_video_rendering(self):
        with TemporaryDirectory() as d:
            source = Path(d) / "sample.png"
            Image.new("RGB", (320, 180), "white").save(source)
            with self.assertRaisesRegex(ValueError, "prevent_global_translation"):
                next(video_frames(source, {"fps": 60, "duration_seconds": 3},
                                  320, 180))


if __name__ == "__main__":
    unittest.main()
