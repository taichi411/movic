# MOVIC video production standard — line boil baseline v1.0 (2026-11-13)

## Adopted look
**Position shift stronger; switching weaker.** This replaces ALL previous attempts based on GIF playback, optical-flow extraction, and Nov-12 MP4 analysis. The approved baseline is the 3-second video named `movic_posstrong_switchweaker_4k60.mp4` created on Nov 13.

- Source art composition, paper and background remain completely fixed.
- Black pencil outlines, orange pencil strokes and the **hand-drawn frame** shift locally.
- Thickness and opacity fluctuations are *weak* (not entirely zero).
- Each cel is independently generated; no optical interpolation between cels.
- 30 states × six 60fps frames each = 180 frames / 3 seconds = **10 cel changes/second**.
- Deterministic RNG seed `2026111304`.
- Full delivery: 3840×2160, 60fps, H.264, yuv420p, exactly 3.000 seconds, loop.
- Compare visually with the approved MP4. Exact identity of compressed output is not guaranteed across FFmpeg versions or source image differences.

## Run

```bash
python -m pip install -r tools/lineboil_baseline_requirements.txt
python tools/render_lineboil_baseline.py path/to/approved-scene.png --output output/clip-01_4k60_loop.mp4
# quick diagnostic only
python tools/render_lineboil_baseline.py path/to/approved-scene.png --output output/clip-01_smoke.mp4 --test-size 640x360
```

FFmpeg and ffprobe must be on PATH. The script does not need the previous `assets/standard-motion.MP4` or any reference video at runtime.

### For new drawings
Current mask extraction is tuned to the orange-and-black reference illustration. On other palettes or particularly delicate contours, review an output before accepting; adjust the hue/gray masks in a new branch rather than silently claiming an exact style match. External border should be a hand-drawn line; it shifts like other ink while the frame/canvas itself stays anchored.

## Short request template

> movicの2026-11-13基準版（位置ズレ強化・切り替え弱め）で、この画像を鉛筆線のラインボイル動画にして。元の色・構図・紙背景は固定。黒線・オレンジ線・手描き外枠のみ、コマごとに線位置が少し違う表現に。線の太さ・濃さの変化は弱め。30セル、6フレーム保持、4K/60fps/3秒/H.264 MP4、ループ、ffprobe検証。GIFや画像生成動画は使用しないで。

This is a **PR** change. Do not merge `main` without user instruction.
