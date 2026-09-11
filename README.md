# VideoEditingAgents

画像、読み上げ、字幕を組み合わせた動画制作を、CodexなどのAIエージェントから進めるための作業テンプレートです。

## サンプル

実際にこの構成で作成した紹介動画です。GitHub Releaseの公開アセットを使って、ブラウザから再生・ダウンロードできます。

<video src="https://github.com/take365/VideoEditingAgents/releases/download/demo-video-20260911/video_no_bgm.mp4" controls width="800"></video>

- [紹介動画 MP4を開く](https://github.com/take365/VideoEditingAgents/releases/download/demo-video-20260911/video_no_bgm.mp4)
- [紹介動画デモIssue](https://github.com/take365/VideoEditingAgents/issues/1)
- [動画レビュー HTML](workspaces/project-codex-video-guide-illustrated-20260910/review/video_review.html)
- [シーン・台本確認 HTML](workspaces/project-codex-video-guide-illustrated-20260910/review/scene_review.html)

動画には、読み上げに使用した `VOICEVOX 四国めたん（ノーマル）` のクレジットを左下に表示しています。

## まず試す

1. CodexまたはClaude Codeのデスクトップアプリで、このリポジトリを取得します。
2. リポジトリを開いた状態で、次のように目的をまとめて伝えます。

```text
このプロジェクトを把握して。
「AIエージェントの使い方」を紹介する横型の短い動画を作って。
説明用の画像、シナリオ、読み上げ、字幕、動画、レビューまで進めて。
足りないツールがあれば確認して、まず実行できるところまで準備して。
```

3. 生成された `scene_plan.md`、`narration_segments.tsv`、画像を確認します。
4. 音声と動画を生成し、`review/video_review.html` を確認します。
5. 「字幕を大きくして」「この言葉の読み方を直して」のように追加で依頼します。

最初からコマンドを細かく指定する必要はありません。目的、対象、画面の向き、雰囲気、尺の目安を伝え、結果を見ながら直す使い方を想定しています。

## 収録内容

- `AGENTS.md`: AIエージェント向けの作業ルール
- `templates/`: 案件作成用の台本、シーン、画像プロンプト、ライセンスメモの雛形
- `scripts/`: 画像確認HTML、音声生成、FFmpeg動画化、完成動画レビュー
- `sample_sources/`: 参考案件の素材・手順
- `webapp/`: 案件管理とチャット操作を行うローカルWeb版

案件は次のような構成で管理します。

```text
project_name/
  brief.md
  scene_plan.md
  narration_segments.tsv
  images/
  audio/
  subtitles/
  segments/
  output/
  review/
  bgm/
```

## 手動実行

```bash
python scripts/create_project.py --name my-video
python scripts/synthesize_voicevox.py --project workspaces/my-video --speaker 2
python scripts/build_slideshow_video.py
python scripts/review_video.py --project workspaces/my-video
```

通常はローカルの VOICEVOX Engine（`http://127.0.0.1:50021`）を使います。完成動画のレビューでは、MP4の形式、解像度、音声、代表フレーム、音声の再文字起こしを確認します。

## 必要な環境

- Python 3.10以上
- FFmpeg / ffprobe
- VOICEVOX Engine または AivisSpeech
- 任意: OpenAI API（画像生成、TTS、文字起こしをAPIで行う場合）

ローカルWeb版の起動方法は [docs/local_web_setup_linux.md](docs/local_web_setup_linux.md) を参照してください。

```bash
./scripts/run_local_linux.sh
```

## 注意

- `.env`、APIキー、認証トークンはGitに追加しないでください。設定例は `.env.example` を使います。
- BGM、画像、音声の利用条件は案件ごとに確認してください。
- 外部公開・広告利用の前に、固有名詞、ロゴ、素材ライセンス、字幕と読み上げを確認してください。
