#!/usr/bin/env python3
"""End-to-end smoke test: '動画にして' produces a verified MP4, never GIF."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "tools/render_seigi_mp4.py"


class SeigiMp4SmokeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.src = self.dir / "input.png"
        img = Image.new("RGB", (320, 180), (248, 234, 223))
        draw = ImageDraw.Draw(img)
        draw.ellipse((70, 35, 240, 160), outline=(63, 54, 56), width=3)
        draw.line((10, 90, 310, 98), fill=(130, 80, 115), width=2)
        img.save(self.src)

    def call_renderer(self, output):
        return subprocess.run(
            [sys.executable, str(RENDER), str(self.src),
             "--output", str(output), "--test-size", "320x180"],
            capture_output=True, text=True, timeout=120,
        )

    def test_delivers_mp4_with_60fps_and_180_frames(self):
        output = self.dir / "clip-12_4k60_loop_test.mp4"
        result = self.call_renderer(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())
        info = json.loads(result.stdout.strip())
        self.assertEqual(info["codec"], "h264")
        self.assertEqual(info["size"], [320, 180])  # explicit smoke-test mode
        self.assertEqual(info["fps"], "60/1")
        self.assertEqual(int(info["frames"]), 180)
        self.assertAlmostEqual(float(info["duration"]), 3.0, places=1)

    def test_rejects_gif_delivery(self):
        output = self.dir / "clip-12.gif"
        result = self.call_renderer(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".mp4", result.stderr)
        self.assertFalse(output.exists())


    def test_production_4k_requires_new_approved_reference(self):
        from importlib.util import spec_from_file_location, module_from_spec
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "tools"))
        from render_seigi_mp4 import render
        from line_boil import DEFAULT_CONFIG
        output = self.dir / "should-not-exist.mp4"
        with self.assertRaisesRegex(ValueError, "Approved Nov 12 reference required"):
            render(self.src, output, DEFAULT_CONFIG, 3840, 2160)
        self.assertFalse(output.exists())

    def test_wrong_reference_is_rejected_even_for_smoke_test(self):
        fake_reference = self.dir / "fake.MP4"
        fake_reference.write_bytes(b"not the approved MP4")
        output = self.dir / "wrong.mp4"
        result = subprocess.run(
            [sys.executable, str(RENDER), str(self.src), "--output", str(output),
             "--test-size", "320x180", "--reference", str(fake_reference)],
            capture_output=True, text=True, timeout=120,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fingerprint mismatch", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
