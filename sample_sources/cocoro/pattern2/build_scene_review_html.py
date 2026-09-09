from __future__ import annotations

import csv
import html
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
NARRATION_TSV = BASE_DIR / "narration_segments.tsv"
PROMPTS_MD = BASE_DIR / "image_prompts.md"
REVIEW_DIR = BASE_DIR / "review"
OUTPUT_HTML = REVIEW_DIR / "pattern2_scene_review.html"

BGM_CREDIT_TEXT = """Relaxing Ballad by Alexander Nakarada (CreatorChords) | https://creatorchords.com
Royalty Free Music by https://www.free-stock-music.com
Creative Commons / Attribution 4.0 International (CC BY 4.0)
https://creativecommons.org/licenses/by/4.0/"""


def load_segments() -> list[dict[str, str]]:
    with NARRATION_TSV.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_prompts() -> dict[str, str]:
    text = PROMPTS_MD.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^## scene_(\d{2})\.png\s*$", text, flags=re.MULTILINE))
    prompts: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        prompts[match.group(1)] = text[start:end].strip()
    return prompts


def e(value: str) -> str:
    return html.escape(value, quote=True)


def render_scene(segment: dict[str, str], prompt: str) -> str:
    scene_id = segment["scene_id"]
    return f"""
  <section class="scene">
    <img src="../images/scene_{scene_id}.png" alt="scene {scene_id}">
    <div>
      <h2>Scene {scene_id}</h2>
      <div class="block"><b>読み上げ</b><p>{e(segment["narration_text"])}</p></div>
      <div class="block"><b>字幕</b><p>{e(segment["subtitle_ja"])}</p></div>
      <div class="block prompt"><b>画像生成プロンプト</b><pre>{e(prompt)}</pre></div>
    </div>
  </section>"""


def build_html() -> str:
    segments = load_segments()
    prompts = load_prompts()
    scenes = "\n".join(render_scene(segment, prompts.get(segment["scene_id"], "")) for segment in segments)
    credit = e(BGM_CREDIT_TEXT)

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>こころのよりどころ相談室 Pattern 2 シーン確認・BGM出典</title>
  <style>
    body {{ margin: 0; font-family: "Yu Gothic", "Yu Gothic UI", "Meiryo", sans-serif; line-height: 1.7; color: #2d261f; background: #fbf8f2; }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 32px auto; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin: 0 0 10px; font-size: 20px; }}
    h3 {{ margin: 0 0 8px; font-size: 18px; }}
    .lead {{ margin: 0 0 24px; color: #6c5e52; }}
    .scene {{ display: grid; grid-template-columns: minmax(360px, 560px) 1fr; gap: 24px; padding: 24px 0; border-top: 1px solid #eadfd2; break-inside: avoid; page-break-inside: avoid; }}
    .scene img {{ width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 8px; box-shadow: 0 10px 28px rgba(64, 48, 36, 0.14); background: #fff; }}
    .block {{ margin: 0 0 12px; padding: 12px 14px; background: #fff; border: 1px solid #efe5da; border-radius: 8px; }}
    .block b {{ display: block; margin-bottom: 4px; color: #8c5d48; font-size: 13px; }}
    .block p {{ margin: 0; white-space: pre-wrap; }}
    pre, code {{ margin: 0; white-space: pre-wrap; font-family: Consolas, "Courier New", monospace; font-size: 12px; line-height: 1.55; color: #4d3b31; }}
    .credit {{ background: #fff; border: 1px solid #efe5da; border-radius: 8px; padding: 16px 18px; margin: 18px 0; break-inside: avoid; page-break-inside: avoid; }}
    .credit p {{ margin: 4px 0; }}
    .credit pre {{ margin-top: 8px; padding: 12px; background: #fbf8f2; border: 1px solid #eadfd2; border-radius: 6px; }}
    a {{ color: #8c5d48; }}
    @media print {{ body {{ background: #fff; }} main {{ width: calc(100% - 28px); margin: 14px; }} .scene {{ grid-template-columns: 46% 1fr; gap: 16px; padding: 16px 0; }} pre, code {{ font-size: 10px; }} .block {{ padding: 9px 10px; }} }}
  </style>
</head>
<body>
<main>
  <h1>こころのよりどころ相談室 Pattern 2 シーン確認・BGM出典</h1>
  <p class="lead">横長16:9、水彩・絵本寄り、AivisSpeech「まい（ノーマル）」用。各シーンの画像、読み上げ、字幕、画像生成プロンプト、BGM出典の一覧です。</p>

  <section class="credit">
    <h3>出力ファイル</h3>
    <p>BGM入り: ../output/cocoro_pattern2_horizontal_mai_bgm100.mp4</p>
    <p>BGMなし: ../output/cocoro_pattern2_horizontal_mai_clean.mp4</p>
    <p>尺: 約35.4秒 / 解像度: 1920x1080 / 音声: AivisSpeech まい（ノーマル） + BGM</p>
  </section>

{scenes}

  <section class="credit">
    <h3>BGM出典・クレジット</h3>
    <p>使用曲: Relaxing Ballad</p>
    <p>アーティスト: Alexander Nakarada (CreatorChords)</p>
    <p>配布元: <a href="https://www.free-stock-music.com/alexander-nakarada-relaxing-ballad.html">Free Stock Music</a></p>
    <p>作者サイト: <a href="https://creatorchords.com">https://creatorchords.com</a></p>
    <p>ライセンス: Creative Commons / Attribution 4.0 International (CC BY 4.0)</p>
    <p>ライセンスURL: <a href="https://creativecommons.org/licenses/by/4.0/">https://creativecommons.org/licenses/by/4.0/</a></p>
    <p>編集メモ: BGM音量100%、フェードイン1.5秒、フェードアウト3秒。</p>
    <h3>表記例</h3>
    <pre>{credit}</pre>
  </section>
</main>
</body>
</html>
"""


def main() -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(build_html(), encoding="utf-8", newline="\n")
    print(OUTPUT_HTML)


if __name__ == "__main__":
    main()
