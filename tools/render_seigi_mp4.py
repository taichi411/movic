#!/usr/bin/env python3
"""MOVIC '動画にして' contract: render an approved still to 4K/60fps MP4.

For the canonical delivery format, do NOT use image generation to make a GIF.
The line boil is a deterministic *approximation* of the reference GIF.
Requires FFmpeg (ffmpeg and ffprobe on PATH) and line_boil_requirements.txt.

Usage:
    python tools/render_seigi_mp4.py path/to/clip-12.png \
        --output output/clip-12_4k60_loop.mp4

For a quick technical smoke test only (NOT a standard delivery):
    python tools/render_seigi_mp4.py path/to/clip-12.png \
        --output output/smoke-test.mp4 --test-size 640x360
"""
import argparse
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from line_boil import DEFAULT_CONFIG, frames, load_config

STANDARD_WIDTH = 3840
STANDARD_HEIGHT = 2160
STANDARD_FPS = 60
STANDARD_SECONDS = 3
STANDARD_BOIL_FPS = 8
STANDARD_FRAMES = STANDARD_FPS * STANDARD_SECONDS


def check_tools():
    for cmd in ("ffmpeg", "ffprobe"):
        if shutil.which(cmd) is None:
            raise RuntimeError(
                f"{cmd} not found. Install FFmpeg and ensure both "
                "ffmpeg and ffprobe are available on PATH."
            )


def check_video(path, width, height):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries",
         "stream=codec_name,width,height,avg_frame_rate,nb_read_frames,pix_fmt:"
         "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    if not data.get("streams"):
        raise RuntimeError("No video stream in output")
    stream = data["streams"][0]
    actual = {
        "codec": stream.get("codec_name"),
        "size": [stream.get("width"), stream.get("height")],
        "fps": stream.get("avg_frame_rate"),
        "frames": stream.get("nb_read_frames"),
        "pixel_format": stream.get("pix_fmt"),
        "duration": data.get("format", {}).get("duration"),
    }
    if actual["codec"] != "h264":
        raise RuntimeError(f"Expected H.264, got {actual}")
    if actual["size"] != [width, height]:
        raise RuntimeError(f"Incorrect resolution: {actual}")
    if Fraction(actual["fps"]) != STANDARD_FPS:
        raise RuntimeError(f"Incorrect fps: {actual}")
    if int(actual["frames"] or -1) != STANDARD_FRAMES:
        raise RuntimeError(f"Incorrect frame count: {actual}")
    if actual["pixel_format"] != "yuv420p":
        raise RuntimeError(f"Incorrect pixel format: {actual}")
    if abs(float(actual["duration"]) - STANDARD_SECONDS) > 0.05:
        raise RuntimeError(f"Incorrect duration: {actual}")
    return actual


def render(input_path, output_path, config_path, width, height):
    if not input_path.is_file():
        raise FileNotFoundError(f"Input illustration not found: {input_path}")
    if output_path.suffix != ".mp4":
        raise ValueError("MOVIC delivery output must be a .mp4 file, not a GIF")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output paths must differ")
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {output_path}")
    check_tools()
    settings = load_config(config_path)
    if settings.get("motion_mode") != "approved_mp4_motion_profile":
        raise ValueError(
            "MOVIC delivery must use the approved MP4 motion profile. "
            "Read assets/seigi/VIDEO_STANDARD.md."
        )
    if settings.get("boil_fps") != STANDARD_BOIL_FPS:
        raise ValueError("Expected 8 line changes/second from approved MP4")
    if settings.get("reference_sha256") != (
            "b9a7d6bbbc040aeb5b1e74843366282e0f7ee20e5273b17a435524e16140c611"):
        raise ValueError("Approved MP4 fingerprint has changed; confirm reference")

    # The renderer may also be used for previews; the VIDEO STANDARD owns
    # final MP4 timing, irrespective of the generic preview script's defaults.
    settings["fps"] = STANDARD_FPS
    settings["duration_seconds"] = STANDARD_SECONDS
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v", f"{width}x{height}",
        "-r", str(STANDARD_FPS), "-i", "pipe:0",
        "-an", "-frames:v", str(STANDARD_FRAMES),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_path),
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        assert proc.stdin is not None
        for frame in frames(input_path, settings, width, height):
            # Stream frames, avoiding 180 huge PNGs stored in memory/on disk.
            proc.stdin.write(frame.tobytes(order="C"))
        proc.stdin.close()
        assert proc.stderr is not None
        stderr = proc.stderr.read().decode("utf-8", errors="replace")
        ret = proc.wait()
        if ret:
            raise RuntimeError("ffmpeg failed: " + stderr[-2000:])
        actual = check_video(output_path, width, height)
    except Exception:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        output_path.unlink(missing_ok=True)
        raise
    actual["bytes"] = output_path.stat().st_size
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Approved still PNG/JPEG")
    parser.add_argument("--output", type=Path, required=True, help="Final .mp4")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--test-size", help="TEST ONLY: render smaller (e.g. 640x360); "
        "not a 4K delivery."
    )
    args = parser.parse_args()
    width, height = STANDARD_WIDTH, STANDARD_HEIGHT
    if args.test_size:
        try:
            width, height = (int(v) for v in args.test_size.split("x"))
        except (ValueError, TypeError) as exc:
            parser.error("--test-size must be WIDTHxHEIGHT, e.g. 640x360")
        if width <= 0 or height <= 0 or width % 2 or height % 2:
            parser.error("--test-size width/height must be positive, even")
        print("WARNING: nonstandard TEST output, NOT 4K.", file=sys.stderr)
    try:
        data = render(args.input, args.output, args.config, width, height)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(json.dumps({"file": str(args.output), **data}, ensure_ascii=False))


if __name__ == "__main__":
    main()
