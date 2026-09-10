# ローカルWeb版セットアップ（Linux優先）

## 起動

```bash
cd /path/to/VideoEditingAgents
chmod +x scripts/run_local_linux.sh
./scripts/run_local_linux.sh
```

初回は `.env` が作られて終了します。`APP_PASSWORD` を変更し、必要なら `OPENAI_API_KEY` を設定して再実行します。ブラウザで `http://127.0.0.1:8787/` を開き、Basic認証でログインします。既定ユーザーは `admin` です。

## ローカルVOICEVOX

VOICEVOX Engineを同じPCで起動してください。既定URLは `http://127.0.0.1:50021`、話者は `VOICEVOX_SPEAKER` で変更できます。案件フォルダの `narration_segments.tsv`、`images/`、`audio/` を使って既存の動画生成スクリプトを実行します。

## 生成後レビュー

動画生成が成功すると、案件の `review/video_review.html` と `review/captures/` が自動生成されます。MP4のコーデック・解像度・音声トラックを確認し、代表フレームで画像や字幕の豆腐文字・切れ・位置・改行を目視確認します。音声はローカルの `faster-whisper` で再文字起こしし、原稿との類似度を参考値として表示します。

ASRレビューを有効にするには、仮想環境で次を一度実行してください。

```bash
source .venv/bin/activate
python -m pip install -r requirements-local.txt
```

既定モデルは `large-v3-turbo` です。精度優先で `large-v3` を使う場合は、レビュー用スクリプトを `--model large-v3` で実行します。モデル未導入でも動画生成は止まらず、HTMLにはASR未実施として記録されます。

## Codex App Server

Linux上で `codex` コマンドを使える状態にし、画面の「ログイン」からChatGPT認証を開始します。WebアプリはApp Serverへ直接公開せず、Pythonバックエンドがstdioで接続します。Codexの作業対象は案件ごとの `worktree/` です。

案件外、秘密情報、外部送信、動画編集と無関係な依頼はWeb側とApp Serverの承認処理で拒否し、案件の `AGENTS.md` でも拒否します。`logs/` はアプリが追記するだけで、Codexから変更できない扱いです。初期の承認設定は `on-request` です。

## 現在の範囲

- 案件作成、会話保存、添付保存、SQLiteジョブ管理
- バックグラウンド動画生成と中止
- MP4等の成果物一覧・ダウンロード
- Basic認証、案件領域チェック、秘密情報保護
- チャットからのCodex App Server利用、アカウント確認、ChatGPTログイン、案件専用スレッド継続
- OpenAI文字起こしAPIのサーバー側呼び出し（`OPENAI_API_KEY` 設定時）
- ローカルVOICEVOXのLinux用音声生成API

## 既知の制限

- SSEエンドポイントは実装済みですが、画面は現在ポーリング表示を併用しています。
- Codexの詳細イベント表示は簡易版です。App ServerのJSON-RPC接続、ChatGPTアカウント確認、読み取りだけのスレッド/ターン実行は確認済みです。
- コマンド・ファイル変更の承認要求は動画案件ポリシーで自動判定し、ログ・秘密情報・外部接続・案件外パスは拒否します。
- CodexターンのAPIはターン完了まで待つ同期処理です。長い指示を非同期ジョブ化するのは次段階です。
- Linux上の長尺動画、実際のOpenAI文字起こし、VOICEVOX常駐接続は利用環境で別途確認が必要です。
