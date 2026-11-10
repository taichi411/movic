#!/usr/bin/env python3
"""Regression tests for the real reference-GIF-driven line-boil path."""
import hashlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from reference_line_boil import generate_frames, ink_detail_mask, reference_fields

REFERENCE = ROOT / "assets/references/line-boil/line-boil-standard.GIF"
EXPECTED_SHA256 = "9f0e4369169d4233ea45f9afed20eab2696043203e426653eaf5a7f09069039b"


class ReferenceBoilTests(unittest.TestCase):
    def test_reference_is_exact_approved_gif(self):
        self.assertTrue(REFERENCE.is_file())
        self.assertEqual(hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
                         EXPECTED_SHA256)
        fields = reference_fields(str(REFERENCE))
        self.assertEqual(len(fields), 9)
        self.assertEqual(fields[0].shape, (298, 541, 2))
        self.assertTrue(np.all(fields[0] == 0))
        self.assertGreater(float(np.abs(fields[1]).max()), 0.5)

    def test_exact_loop_and_stationary_background(self):
        with TemporaryDirectory() as tempdir:
            src = Path(tempdir) / "test.png"
            img = Image.new("RGB", (320, 180), (245, 229, 215))
            painter = ImageDraw.Draw(img)
            painter.ellipse((60, 30, 225, 155),
                            fill=(226, 189, 169),
                            outline=(48, 41, 42), width=4)
            painter.arc((90, 65, 180, 150), 20, 320,
                        fill=(50, 42, 45), width=3)
            img.save(src)
            config = {
                "fps": 60, "duration_seconds": 3,
                "line_blend": 0.94, "reference_motion_gain": 0.75
            }
            frames = generate_frames(src, config, 320, 180, REFERENCE)
            samples = {}
            for i, image in enumerate(frames):
                if i in (0, 9, 10, 19, 20, 80, 89, 90, 100, 170, 179):
                    samples[i] = image.copy()
            self.assertEqual(i + 1, 180)
            self.assertTrue(np.array_equal(samples[0], samples[90]))
            self.assertTrue(np.array_equal(samples[10], samples[100]))
            self.assertTrue(np.array_equal(samples[9], samples[0]))
            self.assertTrue(np.array_equal(samples[19], samples[10]))
            self.assertFalse(np.array_equal(samples[10], samples[0]))
            self.assertTrue(np.array_equal(samples[0][5, 5],
                                           samples[10][5, 5]))
            self.assertTrue(np.array_equal(samples[0][5, 5],
                                           samples[170][5, 5]))
            self.assertFalse(np.array_equal(samples[80], samples[0]))
            self.assertFalse(np.array_equal(samples[179], samples[0]))

    def test_mask_prefers_ink_over_white_space(self):
        canvas = np.full((180, 320, 3), 245, dtype=np.uint8)
        canvas[70:74, 40:280] = (30, 30, 30)
        mask = ink_detail_mask(canvas)
        self.assertGreater(float(mask[71, 100]), 0.35)
        self.assertLess(float(mask[15, 15]), 0.02)
        self.assertEqual(mask.shape, (180, 320))


if __name__ == "__main__":
    unittest.main()
