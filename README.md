# VideoEditingAgents

動画制作案件用のCodex作業テンプレートです。

今回のAMCON案件で使った流れを、次回以降に使い回せるようにまとめています。

## 入っているもの

- `AGENTS.md`
  - Codexに読ませる作業指示書。

- `templates/`
  - ヒアリング、シーン構成、画像プロンプト、字幕/ナレーションTSV、ライセンスメモ、`.env` のテンプレート。

- `scripts/`
  - 汎用の確認HTML生成、OpenAI画像生成、OpenAI TTS、動画結合スクリプト。
  - AivisSpeech / VOICEVOX のPowerShell音声生成スクリプト。

- `sample_sources/amcon/`
  - AMCON案件で実際に使ったスクリプトの参考コピー。
  - 案件固有の素材やAPIキーは含めていません。

## 使い方

1. 新しい案件フォルダを作る。
2. `templates/` の中身を案件フォルダへコピーする。
3. `scene_plan.md` と `narration_segments.tsv` を埋める。
4. `image_prompts.md` を作り、ChatGPTまたはAPIで画像を生成する。
5. `scripts/generate_review_html.py` で確認HTMLを作る。
6. AivisSpeech / VOICEVOX / OpenAI TTSで音声を作る。
7. `scripts/build_slideshow_video.py` で動画化する。

## 想定ツール

- ffmpeg / ffprobe
- Python 3.10+
- PowerShell
- AivisSpeech Engine
- VOICEVOX Engine
- OpenAI API optional

## コスト感

低コストにする場合は、画像生成をChatGPT側で手作業にして、Codex側ではファイル管理、字幕、音声、結合だけ行うのが現実的です。
OpenAI APIの画像生成は一括生成や再現性では便利ですが、シーン数が多い案件では費用が積み上がります。

## ローカルWeb版

Linux優先のチャット型Web試作は `webapp/` にあります。起動手順は [docs/local_web_setup_linux.md](docs/local_web_setup_linux.md) を参照してください。

```bash
./scripts/run_local_linux.sh
```

案件ごとにSQLiteの記録と専用作業領域を作成します。Basic認証はlocalhost利用を前提にし、Codex App ServerはWebから直接公開せずPythonバックエンドからstdioで接続します。

## Docker / サーバ版デモ

`server-version` ブランチには、Docker DesktopのUbuntuコンテナで動かす構成を含めています。初回起動時に画像2枚とシナリオ付きのサンプル案件を作成し、動画生成時は音声生成からMP4作成まで自動で進めます。起動手順は [docs/server_local_docker.md](docs/server_local_docker.md) を参照してください。
