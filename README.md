# MOVIC — SOUND × VISUAL × LIVE

邦楽ロック中心・映像演出あり・全7バンドのライブイベント特設サイト試作版。

## 動作・公開
`index.html` をブラウザで開くだけで表示できます。GitHub Pages / Vercelなどに静的サイトとして公開可能です。

## 実装済み
- SYSTEM BOOT演出（スキップ・2回目以降の省略）
- ネオン・グリッチ風のヒーローとイベント紹介
- 7バンドのカードとプロフィールモーダル
- タイムテーブル、梅田 LIVESPACE ODYSSEYへのアクセス、チケット予告
- スマートフォン対応とモーション軽減設定

## 情報が決まり次第変更
- `index.html` 末尾の `const lineup` を正式バンド名・紹介文に差し替える
- `DATE TBA` を実際の開催日に変更
- `TIME — TBA` を正式な出演時刻に変更
- チケット料金・購入リンクを追記
- 会場住所等の公開前最終確認

参考サイトの画像・HTML・ロゴは流用していません。

## seigi のイラスト・動画制作フロー

- 全20シーンの脚本：[`assets/seigi/story.md`](assets/seigi/story.md)
- **「イラストを動画にして」「動画にして」** の標準仕様：**[`assets/seigi/VIDEO_STANDARD.md`](assets/seigi/VIDEO_STANDARD.md)**
- 決定的な線揺れで **4K（3840×2160）／60fps／3秒／H.264 MP4**を作るコマンド：`tools/render_seigi_mp4.py`
- スクリプトは `ffprobe` で動画仕様を自動検証。**GIFは動画の納品物として扱わない。**
- コーディングエージェント向け入口：[`AGENTS.md`](AGENTS.md)

```sh
python -m pip install -r tools/line_boil_requirements.txt
# ffmpeg / ffprobe をインストール済みの環境で実行
python tools/render_seigi_mp4.py path/to/approved-image.png --output output/clip-12_4k60_loop.mp4
```

**注：** リポジトリに仕様書を置くだけで、会話AIが毎回自動的に読むとは限りません。実行前に該当ファイルを取得・確認する運用が必要です。

## PRのプレビュー手順（マージ前の表示確認）

MOVICは **GitHub Pages（main）** を本番サイトとして使います。PRの確認時には本番を変更せず、**raw.githack の開発用プレビュー**でPRブランチの `index.html` を開いてください。

### 毎回の標準手順

1. GitHubで対象PRを作成（**mainにはマージしない**）。
2. GitHubのPRから **最新の head commit SHA（40桁）** を取得する。例：GitHub API `GET /repos/taichi411/movic/pulls/25` の `head.sha`。
3. 以下のURLで、該当コミットのHTMLをブラウザ表示する。

   ```text
   https://raw.githack.com/taichi411/movic/<40桁のhead SHA>/index.html
   ```

4. GitHubに `index.html` と参照画像（例：`assets/movic-hero-character.png`）がそのコミットで存在するか確認する。スマートフォン縦向き・横向き、PC表示、イントロ→ヒーローの切替を目視確認する。
5. **毎回、ユーザーへの回答にPR URLとプレビューURLをセットで載せる。** 最初に開いた際に、raw.githack のHTML表示確認が出ることがある。確認画面で続行すると表示される。
6. PRに追加コミットが入ったら **新しい head SHA でURLを再発行**する。以前のSHAのURLはその時点の固定スナップショットで、変更を自動反映しない。
7. ユーザーからマージ指示があって初めてmainへ取り込む。公開URL（main）とPRプレビューURLを混同しない。

### PR #25 のプレビュー例

- PR: https://github.com/taichi411/movic/pull/25
- HTMLプレビューはPRの **最新head SHA** から上記の形式で都度生成。過去のコミットURLを使い回さない。PRの会話コメントにも最新版リンクを記載する。

### 制約と代替手段

- raw.githack はGitHub公式のホスティングではなく**外部のプレビューサービス**。公開リポジトリの静的HTML向けで、初回の安全確認画面や一時的なサービス障害の可能性がある。**実ブラウザで表示できたかどうかは確認できた場合のみ「確認済み」と記載する。**
- 将来的にVercel等のPRデプロイが利用可能になれば、その**実際に生成・確認できたURL**を優先する。推測のVercel URLは発行しない。
- raw.githackで表示できないときの代替リンク（表示保証なし）：
  `https://htmlpreview.github.io/?https://github.com/taichi411/movic/blob/<PRブランチ名>/index.html`
- この手順は **`taichi411/movic` 用**。別リポジトリ `movic-visuals` のプレビューと混同しない。

## 動画化の最新基準（2026-11-10）

「イラストを動画にして」の揺れ方は、**承認済みMP4から抽出した24状態・約8Hzの動き**が正本。旧GIF基準の再現ではありません。

- 生成・検証の標準：[VIDEO_STANDARD.md](assets/seigi/VIDEO_STANDARD.md)
- 参照動画の情報と保存状態：[鉛筆線の新しい基準](assets/references/line-boil/README.md)
- 抽出済み動きデータ：[standard-motion-profile.json](assets/references/line-boil/standard-motion-profile.json)
- 実装：[approved_mp4_line_boil.py](tools/approved_mp4_line_boil.py)
- 実際の完成動画は **4K・60fps・3秒・H.264 MP4**。元参照動画は実測3840×2160・30fps・3秒で、解像度・fpsは別物。
- 基準MP4を `assets/standard-motion.MP4` としてGitHubへ保存済み。**`.MP4` は大文字**、読み込む場所は assets 直下。レンダラーが直接参照し、`standard-motion-profile.json` は実測データのスナップショット。


> **MOVIC基準動画の正しいパス:** `assets/standard-motion.MP4`（大文字の `.MP4`）。動画納品は `clip-XX_4k60_loop.mp4`（小文字）として従来どおり4K・60fps・3秒。
> **seigi動画の画面固定ルール（2026-11-10）:** 画面全体の上下移動・ズーム・カメラ揺れはしない。鉛筆の局所的な線の動きだけを残し、色・構図・背景・枠を維持。`assets/seigi/VIDEO_STANDARD.md` と `assets/references/line-boil/standard.json` を参照。

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

