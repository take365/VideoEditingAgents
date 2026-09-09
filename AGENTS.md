# Video Editing Agent Guide

このフォルダは、画像 + ナレーション + 字幕の動画制作をCodex/ChatGPTで回すための作業テンプレートです。

## 基本方針

- まず依頼内容、用途、尺、トーン、納品形式、公開範囲を確認する。
- いきなり動画化せず、先にシーン構成、画像プロンプト、ナレーション/字幕原稿をファイルに整理する。
- 画像は低コスト運用ではChatGPTに1枚ずつ生成してもらい、`images/` に配置する。
- `.env` が用意されている場合だけ、OpenAI APIで画像生成やTTSを行う。
- 音声はローカル環境の AivisSpeech / VOICEVOX を優先し、必要に応じてOpenAI TTSも使う。
- クライアント確認用に、動画だけでなく、シーン画像と字幕を一覧できるHTMLを作る。

## 推奨ワークフロー

1. ヒアリング
   - 目的、視聴者、尺、画風、ナレーション声、字幕有無、BGM有無、公開範囲を確認する。

2. シーン設計
   - `scene_plan.md` を作る。
   - 1シーン1画像を基本にし、長い説明は `01a`, `01b` のように音声だけ分割する。

3. 原稿整理
   - `narration_segments.tsv` を作る。
   - 列は `scene_id / narration_text / subtitle_ja / subtitle_other` を基本にする。
   - 読み間違えそうな語は読み上げ文だけ平仮名やカタカナに寄せる。

4. 画像プロンプト作成
   - `image_prompts.md` を作る。
   - ChatGPT手生成の場合は、各シーンのプロンプトをコピーしやすい形にする。
   - API生成の場合は、`.env` に `OPENAI_API_KEY=` または `API_KEY=` を置いてから実行する。

5. 画像確認
   - `images/` に生成画像を入れる。
   - `generate_review_html.py` で確認用HTMLを作り、画像と字幕を一覧する。

6. 音声生成
   - AivisSpeech: `synthesize_aivis.ps1`
   - VOICEVOX: `synthesize_voicevox.ps1`
   - OpenAI TTS: `synthesize_openai_tts.py`

7. 動画結合
   - `build_slideshow_video.py` で画像、音声、字幕、BGMを結合する。
   - ffmpeg / ffprobe が必要。

8. 納品整理
   - 完成mp4、確認用HTML、字幕TSV、画像、プロンプト、使用素材メモをまとめる。
   - APIキーや `.env` は絶対に納品物へ入れない。

## フォルダ構成例

```text
project_name/
  .env                         # API利用時のみ。納品しない
  scene_plan.md
  image_prompts.md
  narration_segments.tsv
  images/
    scene_01.png
    scene_02.png
  audio/
  subtitles/
  segments/
  output/
  review/
  bgm/
```

## 注意

- BGM、音声、AI画像生成の利用条件は案件ごとに確認する。
- 外部公開や広告利用では、翻訳、固有名詞、人物名、製品名、ロゴ、BGMの権利を再確認する。
- 生成画像は実写や実在人物の正確な再現ではなく、説明用イメージとして扱う。

## ローカルWeb / Codex連携の編集境界

- Web版は動画制作案件の作業だけを扱う。字幕、台本、音声、画像、動画、FFmpeg、レビュー、設定、案件専用スクリプト以外の依頼は拒否する。
- Codex App Serverの作業ディレクトリは案件ごとの `worktree/` に限定する。共通リポジトリ、他案件、ホスト全体を変更しない。
- 外部送信、認証情報の取得・表示、APIキーの読み取り、YouTube投稿、課金・契約操作、動画制作と無関係なシステム操作は拒否する。
- 案件の `logs/` は変更禁止。アプリケーションが追記するログをCodexが編集、削除、短縮、置換してはならない。
- `.env`、秘密情報、認証トークン、会話に含まれる秘密値を画面、ログ、成果物、コミットへ出さない。
- 動画生成は検証済みスクリプトを優先し、コード変更が必要な場合も案件専用コピーで行い、小さな試作と差分確認を先に実施する。
