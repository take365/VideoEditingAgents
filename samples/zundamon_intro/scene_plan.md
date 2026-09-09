# シーン構成

| scene_id | 画像 | 内容 | セリフ |
|---|---|---|---|
| 01a | `images/scene_01.png` | システムの紹介 | ローカルWebで動画制作を進める説明 |
| 01b | `images/scene_01.png` | 素材の添付 | 案件、台本、画像、音声を準備 |
| 02a | `images/scene_02.png` | チャット指示 | 字幕・音声・動画生成を依頼 |
| 02b | `images/scene_02.png` | 確認と成果物 | ブラウザ確認、MP4・レビュー取得、Codexの作業範囲 |

## 制作メモ

- `01a`/`01b` は同じ画像、`02a`/`02b` も同じ画像を使う。
- 音声ファイルは `audio/scene_01a.wav` などの名前で生成する。
- 字幕は `narration_segments.tsv` の3列目を使用する。
