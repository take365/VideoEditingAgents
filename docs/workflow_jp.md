# 動画制作ワークフロー

## 1. まず聞くこと

- 動画の目的
- 視聴者
- 希望尺
- 画風
- ナレーションの声
- 字幕の有無
- BGMの有無
- 公開範囲
- 納品形式
- 修正回数の前提

## 2. 最初に作るファイル

- `brief.md`
- `scene_plan.md`
- `narration_segments.tsv`
- `image_prompts.md`

この段階では動画を作らず、方向性を固める。

## 3. 画像生成

低コスト運用:

- `image_prompts.md` から1シーンずつChatGPTへ貼る
- 生成画像を `images/` に保存
- ファイル名は `scene_01.png` のようにする

API運用:

- `.env` に `OPENAI_API_KEY=` を置く
- `python scripts/generate_openai_images.py` を案件フォルダで実行

## 4. 確認HTML

案件フォルダで実行:

```bash
python /mnt/d/project/VideoEditingAgents/scripts/generate_review_html.py
```

出力:

```text
review/scene_review.html
```

## 5. 読み上げ

AivisSpeech:

```powershell
powershell -ExecutionPolicy Bypass -File D:\project\VideoEditingAgents\scripts\synthesize_aivis.ps1
```

VOICEVOX:

```powershell
powershell -ExecutionPolicy Bypass -File D:\project\VideoEditingAgents\scripts\synthesize_voicevox.ps1
```

OpenAI TTS:

```bash
python /mnt/d/project/VideoEditingAgents/scripts/synthesize_openai_tts.py
```

## 6. 動画化

案件フォルダで実行:

```bash
python /mnt/d/project/VideoEditingAgents/scripts/build_slideshow_video.py
```

BGMを入れる場合:

```text
bgm/bgm.mp3
```

に配置しておく。

## 7. 納品

- `output/video_bgm.mp4` または `output/video_no_bgm.mp4`
- `review/scene_review.html`
- `narration_segments.tsv`
- `image_prompts.md`
- `images/`
- `license_and_tools_note.txt`

`.env` は納品しない。
