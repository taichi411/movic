# MOVIC — 鉛筆線の揺らぎ基準 (Line Boil)

## 目的
シーンごとに異なる画像を描き直すのではなく、**元画像の色・デザイン・表情を維持したまま**、鉛筆線だけが不規則に描き直される紙芝居風アニメーションを毎回同じルールで書き出します。

## 基準素材
- **基準GIF**: `assets/references/line-boil/line-boil-standard.gif`
- **設定**: `assets/references/line-boil/standard.json`
- **生成コード**: `tools/line_boil.py`

> 注意: 先に選んだ「基準GIF」は画像生成で制作されたもので、元の生成アルゴリズムとパラメータは取得できません。ここに保存したコードと数値は、過去の線揺れ加工を基にした**決定的な近似実装**です。GIFの各フレームをピクセル単位で再現するものではありません。目視で比較して数値調整してください。

### 基準GIFを追加する手順
このPRにはGIF本体をまだ含めていません。選定済みの基準GIFをダウンロードし、GitHubの当該ディレクトリに **`line-boil-standard.gif`** の名前でアップロードしてください。GIFなしでも生成コードは動きます。

## インストールと使い方
PCのPython環境で実行します（Remotionの機能ではありません）。

```sh
python -m pip install -r tools/line_boil_requirements.txt
python tools/line_boil.py assets/scene01.png --output output/scene01.gif
python tools/line_boil.py assets/scene01.png --output output/scene01.mp4
```

- デフォルト出力: **1280×720（16:9）／24fps／3秒**。
- `--width 1920 --height 1080` でフルHD出力できます。
- `--config` で別のJSON設定を指定できます。
- 入力画像を拡大して出力する場合は、元画像の精細さそのものは増えません。
- `standard.json` に設定が固定されており、**同じ画像＋同じ設定＝毎回同じフレーム列**です。

## 固定パラメータと効果

| キー | 基準値 | 内容 |
|---|---:|---|
| `fps` | 24 | 出力フレームレート |
| `boil_fps` | 8 | 1秒あたりの線の描き直し回数 |
| `duration_seconds` | 3 | 1シーンの長さ |
| `horizontal_amplitude_px` | 7.5 | 1920px幅換算の横揺れの強さ |
| `vertical_amplitude_px` | 6.4 | 1080px高換算の縦揺れの強さ |
| `grid_columns` / `grid_rows` | 37 / 22 | 変形フィールドの粗さ |
| `line_blend` | 0.94 | 鉛筆線の変形の強さ |
| `background_blend` | 0.06 | 紙・淡色部分に残るわずかな変化 |
| `seed` | 4357 | 乱数を固定して再現性を確保 |

## 制作ルール
1. 元画像は**横長16:9**で用意する。
2. キャラクターの形、目、髪型、猫の模様、衣服、淡い色合いは**変更しない**。
3. 紙の質感はできる限り固定し、暗い鉛筆の輪郭・ハッチングを中心に揺らす。
4. 揺れ幅を変更する必要があれば、新しいJSONを別名保存して元の基準設定を維持する。
5. 完全な線ごとの独立描画ではなく画像ベースの局所変形なので、描画に合わせた微小な色変形が生じ得る。

## 今後
描画領域をマスクで手動指定できるモード、Webエディター上でのプレビュー、FFmpegによる配布向けH.264書き出しを別PRで追加できます。
