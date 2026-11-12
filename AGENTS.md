# MOVIC — 作業エージェント向けプロジェクト規約

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



## まず読むファイル

- シーン説明／脚本：`assets/seigi/story.md`
- **動画出力の最優先規約：`assets/seigi/VIDEO_STANDARD.md`**
- 鉛筆線の**旧基準MP4本体**：`assets/standard-motion.MP4`（拡張子大文字・assets直下）。実装と解析：`tools/approved_mp4_line_boil.py`、`assets/references/line-boil/README.md`。旧GIFや以前のプロファイルのみを根拠にしない。

## 利用者の短い指示に対する対応

- 「story.mdだして」→ `assets/seigi/story.md` を確認して内容を提示する。
- 「Clip XX／シーンXXのイラスト描いて」→ `story.md` の指示に沿い、基準の水彩・色鉛筆タッチ／16:9の高画質PNGを生成する。人物の手足、猫の体、表情に破綻がないか確認する。
- **「動画にして」「イラストを動画にして」→ 画像生成ツールによるGIF制作ではなく、承認したPNGから `tools/render_seigi_mp4.py` を実行し、必ず4K・60fps・3秒のMP4を納品する。** **画面・紙・枠・被写体全体の上下移動は禁止**。鉛筆線の局所的な描き直しだけを動かす。
- 「GIFにして」→ 明示的にGIFを求めた場合のみGIF形式で出力する。

動画仕様の詳細は必ず `assets/seigi/VIDEO_STANDARD.md` を読むこと。**揺れの基準は2026-11-10に承認されたMP4由来の24状態（3秒で約8Hz）であり、旧GIFを使って推測しない。**現行のデフォルトは 3840×2160／60fps／3秒／180フレーム／線の変化8回毎秒／H.264 MP4。出力できなければ、GIFで代替せず未完了と報告する。

このファイルはGitHubリポジトリ内のエージェントに向けた規約。ChatGPTの会話だけで自動読込が保証されるわけではないため、ユーザーが短い指示を出した場合も適切なGitHubファイルを取得してから実行する。

## 映像の揺れに関する禁止事項

- **全画面の上下バウンド・カメラシェイク・左右シフト・ズームは禁止**。画像全体の位置をアニメーションさせない。
- 正式基準 `standard-motion-approved-2026-11-12.MP4` のフローから全体共通の動き成分を除去し、線の局所的な揺れだけを転写する。設定の `prevent_global_translation=true` を変更しない。
- 背景・外枠を固定。実際の動画ファイルをチェックしてから提供し、**GIFやスプライトシートをMP4と称して渡さない**。
