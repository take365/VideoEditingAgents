# サーバ版デモをDockerで動かす

## 起動

Docker DesktopでLinuxコンテナを利用できる状態にして、リポジトリのルートで実行します。

```bash
cp .env.example .env
docker compose up --build
```

ブラウザで `http://127.0.0.1:8787/` を開き、Basic認証でログインします。初回起動時に「サンプル：2枚画像から動画生成」案件が作られます。

## サンプルの確認

サンプル案件には以下が入っています。

- `images/scene_01.png`
- `images/scene_02.png`
- `scenario.md`
- `narration_segments.tsv`

素材一覧のファイル名をクリックするとダウンロードできます。「動画を生成」を押すと、台本から音声を生成し、画像・字幕と合成したMP4を作ります。完了後はチャット履歴に動画結果とCodexの確認内容が表示されます。

## API設定

ローカルの `.env` に実値を設定します。`.env` はGit管理しません。

```dotenv
APP_PASSWORD=local-only-password
SAKURA_AI_TOKEN=
SAKURA_AI_BASE_URL=https://api.ai.sakura.ad.jp
SAKURA_TTS_SPEAKER=3
SAKURA_TRANSCRIPTION_MODEL=whisper-1
OPENAI_API_KEY=
```

`SAKURA_AI_TOKEN` が設定されている場合、音声合成と文字起こしはさくらのAI Engineを優先します。未設定時はローカルVOICEVOX URLへフォールバックします。Codexのサーバー実行には、コンテナ内で利用できる `codex` と認証設定が別途必要です。

## デモ版の注意

App Run共用型など永続ストレージのない環境では、コンテナの更新・再起動で案件、音声、動画が消える可能性があります。必要なファイルは先に画面からダウンロードしてください。本番利用では外部DB・オブジェクトストレージへ保存する構成に切り替えます。
