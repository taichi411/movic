# MOVIC — 鉛筆線の揺らぎ基準 (Line Boil)

## 目的
シーンごとに異なる画像を描き直すのではなく、**元画像の色・デザイン・表情を維持したまま**、鉛筆線だけが不規則に描き直される紙芝居風アニメーションを毎回同じルールで書き出します。

## 2026-11-10 改訂の旧基準（履歴）

**以前のGIFは採用終了。** 当時の基準はユーザーがGitHubにアップロードした **`assets/standard-motion.MP4`** でしたが、**2026-11-12に新しい基準へ更新済み**です。実測 **3840×2160 / H.264 / 30fps / 3秒 / 90フレーム**。これは揺れの参考動画なので、書き出し時に **3840×2160 / 60fps / 3秒 / MP4** へ変換します。ただし、これは揺れ方の参照であり、完成品は従来どおり **3840×2160 / 60fps / 3秒 / MP4** です。

元MP4を解析した結果、実質的な描線の切替は **24回／3秒（約8Hz）**、30fpsの3〜4コマごとです。以下をGitHubに記録しています。

- **動きの正本**: `assets/standard-motion.MP4`。`tools/approved_mp4_line_boil.py` は毎回このMP4を直接読み取り、24状態を抽出。`standard-motion-profile.json` は更新可能な解析スナップショットで、別の動画の内容を流用しない。
- **変換コード**: `tools/approved_mp4_line_boil.py`。水彩・紙目を維持し、インクの輪郭を重点的に局所変形する。
- **設定**: `assets/references/line-boil/standard.json` の `motion_mode=approved_mp4_motion_profile`。
- **GitHubアップロード済みMP4のSHA-256**: `55211c3917bc205493229f970880be3237f19b919061a47ec30e0e4f8a90f3dd`。
- **正式な元MP4本体（登録済み）**: `assets/standard-motion.MP4`（**拡張子は大文字、場所は assets 直下**）。大文字・小文字を変更しない。Git blob SHA-1: `5809b7915eb520b6724a85eaf860e5793511f36f`。
- **元MP4を使ってプロファイルを再抽出する方法**：`tools/extract_approved_mp4_motion.py`（元MP4のハッシュが一致しなければエラー）。

`VIDEO_STANDARD.md` の指示が優先です。GIF生成と4K MP4納品を取り違えないでください。

### 再現性に関する限界

転写されるのは、基準MP4から取得した変位パターン・切替タイミングです。元動画の線が実際に描き直されるときの画素単位の変化や、別シーンのキャラクター固有の動きまで**完全には復元できません**。生成結果を基準と並べて確認し、強度調整が必要なら、別途設定パラメータとして追加し、MP4の実測データと区別して記録します。

---

## 基準素材（旧GIFは履歴として保持）
- **旧基準GIF（履歴）**: `assets/references/line-boil/line-boil-standard.GIF`
- **設定**: `assets/references/line-boil/standard.json`
- **生成コード**: `tools/line_boil.py`

> 注意: 先に選んだ「基準GIF」は画像生成で制作されたもので、元の生成アルゴリズムとパラメータは取得できません。ここに保存したコードと数値は、過去の線揺れ加工を基にした**決定的な近似実装**です。GIFの各フレームをピクセル単位で再現するものではありません。目視で比較して数値調整してください。

### 基準GIFの保存先
選定済みの基準GIFは **`assets/references/line-boil/line-boil-standard.GIF`** に保存済みです。GitHub上のファイル名は大文字の `.GIF` なので、参照時もこの表記に統一してください。

## インストールと使い方

> **動画として納品する場合は必ず [VIDEO_STANDARD.md](../../seigi/VIDEO_STANDARD.md) に従い、`tools/render_seigi_mp4.py` を使うこと。** 下記 `line_boil.py` は線揺れの低解像度テスト・GIF試作用の汎用ツールで、MOVICの4K60納品コマンドではありません。

```sh
python -m pip install -r tools/line_boil_requirements.txt
# 4K60の完成MP4には FFmpeg/ffprobe が必要
python tools/render_seigi_mp4.py path/to/approved-scene.png --output output/clip-12_4k60_loop.mp4
# 任意: ラフな低解像度GIFで線の感じをチェックする場合のみ
python tools/line_boil.py path/to/approved-scene.png --output output/test.gif
```

- `line_boil.py` 単体の省略時解像度は **1280×720**（テスト用）。設定JSONのFPSは **60fps**。動画納品は常に専用コマンドで **3840×2160・60fps・3秒**。
- `--width 1920 --height 1080` でフルHD出力できます。
- `--config` で別のJSON設定を指定できます。
- 入力画像を拡大して出力する場合は、元画像の精細さそのものは増えません。
- `standard.json` に設定が固定されており、**同じ画像＋同じ設定＝毎回同じフレーム列**です。

## 固定パラメータと効果

| キー | 基準値 | 内容 |
|---|---:|---|
| `fps` | 60 | 出力フレームレート |
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
H.264の4K60・3秒MP4書き出しとffprobe検証は `tools/render_seigi_mp4.py` に実装済み。描画領域の個別マスクやWebエディター上のプレビューは別途追加を検討できます。

## ファイル名の大文字・小文字

**必ず `assets/standard-motion.MP4` を読む。** Linux/GitHub Actionsでは `.mp4` と `.MP4` は別ファイル。確認コマンド:

```sh
python tools/extract_approved_mp4_motion.py --check
python tools/render_seigi_mp4.py path/to/approved-scene.png --output output/clip-12_4k60_loop.mp4
```

基準の元動画は `assets/standard-motion.MP4`、完成動画の拡張子は従来どおり小文字の `.mp4` で問題ありません。

## 2026-11-10更新：画面固定・線だけの揺れ

ユーザーが承認した見え方：**位置は一切動かさず、鉛筆の細い線だけが細かく描き直される**こと。以前の、画面全体が上下にバウンドする動画は不採用。

- `standard.json`: `prevent_global_translation=true`、`fixed_border_fraction=0.025`、`max_local_wobble_px_at_910=4.0`。
- 元MP4から得た光学フローの**インク領域に対する共通のdx/dyを減算**。上下方向だけでなく左右方向もゼロ基準にする。
- 残った局所的な揺れは最大値を制限し、紙・水彩・フレーム外枠は同じ座標に固定する。元PNGを毎回基準にし、フレームごとに変形を累積しない。
- `tools/test_approved_mp4_line_boil.py` でカメラ移動除去と背景固定をチェック。
- 本納品は `tools/render_seigi_mp4.py` により **4K (3840x2160)・60fps・3秒・H.264 MP4**。GIF試作を完成動画として渡さない。

これは見え方の制約をコードで再現する方式。別の画像でも同じ動作原則を適用するが、描き直された個々の線がピクセル単位で一致するわけではない。

## 新しい正式基準（2026-11-12承認）

**正式な揺れの基準は ChatGPTファイルライブラリ `/MOVIC/standard-motion-approved-2026-11-12.MP4`。**

- 原本：2026-11-12添付の `movic_scene01_lineboil_4k60_loop(3).mp4`
- SHA-256: `9dd1d33c75c1401f6c47d1b3aaf73910042f75fcdc5570e5997db87034415bd1`
- Git blob SHA-1: `943628a2b9c41f48a969d54dff90919ee2e1ea15`
- 910×512、30fps、3秒、90フレーム、描線変化24状態（約8Hz）
- **GitHub の `assets/standard-motion.MP4` は旧基準のまま**。新基準をGitHubにコピーしたという意味ではない。原本のアップロードが完了するまでは、MOVICの制作環境にライブラリから素材を配置し、`--reference` で指定する。
- **本納品で `--reference` を省略しない。** 4K本番出力は新基準の実ファイルがなければ失敗するよう変更した。旧基準への黙示的なフォールバックは禁止。
- 画面全体・背景・外枠を固定し、線の局所的な変化だけを反映する。最終納品はH.264 MP4、3840×2160、60fps、3秒、180フレーム。

```bash
# 次のコマンドの input は承認したPNG、reference はライブラリから取得した正式MP4
python tools/render_seigi_mp4.py /path/to/approved-illustration.png \
  --reference /path/to/standard-motion-approved-2026-11-12.MP4 \
  --output /mnt/data/clip-XX_4k60_loop.mp4
```

`tools/render_seigi_mp4.py` がSHA-256を検査し、`extract_approved_mp4_motion.py` も参照MP4のGit blob SHA-1を検査する。既存のGitHub Actionsの低解像度スモークテストは旧素材で動作確認するが、正式基準の**見た目の品質保証**とは別である。新MP4をGitHubに追加するまで、CI単体では新基準の4K本番動画を作れない。

