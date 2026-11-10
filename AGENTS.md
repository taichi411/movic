# MOVIC — 作業エージェント向けプロジェクト規約

## まず読むファイル

- シーン説明／脚本：`assets/seigi/story.md`
- **動画出力の最優先規約：`assets/seigi/VIDEO_STANDARD.md`**
- 鉛筆線の基準と実装：`assets/references/line-boil/README.md`

## 利用者の短い指示に対する対応

- 「story.mdだして」→ `assets/seigi/story.md` を確認して内容を提示する。
- 「Clip XX／シーンXXのイラスト描いて」→ `story.md` の指示に沿い、基準の水彩・色鉛筆タッチ／16:9の高画質PNGを生成する。人物の手足、猫の体、表情に破綻がないか確認する。
- **「動画にして」「イラストを動画にして」→ 画像生成ツールによるGIF制作ではなく、承認したPNGから `tools/render_seigi_mp4.py` を実行し、必ずMP4を納品する。**
- 「GIFにして」→ 明示的にGIFを求めた場合のみGIF形式で出力する。

動画仕様の詳細は必ず `assets/seigi/VIDEO_STANDARD.md` を読むこと。現行のデフォルトは 3840×2160／60fps／3秒／180フレーム／線の変化8回毎秒／H.264 MP4。出力できなければ、GIFで代替せず未完了と報告する。

このファイルはGitHubリポジトリ内のエージェントに向けた規約。ChatGPTの会話だけで自動読込が保証されるわけではないため、ユーザーが短い指示を出した場合も適切なGitHubファイルを取得してから実行する。
