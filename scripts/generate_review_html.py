#!/usr/bin/env python3
import csv
import html
import re
from pathlib import Path

BASE = Path.cwd()
TSV = BASE / "narration_segments.tsv"
IMAGES = BASE / "images"
OUT_DIR = BASE / "review"
OUT = OUT_DIR / "scene_review.html"


def scene_key(scene_id: str) -> str:
    m = re.match(r"(\d+)", scene_id)
    return m.group(1) if m else scene_id


def find_image(scene_id: str) -> Path | None:
    key = scene_key(scene_id)
    candidates = sorted(IMAGES.glob(f"scene_{key}*.*"))
    if not candidates:
        candidates = sorted(IMAGES.glob(f"{key}*.*"))
    return candidates[0] if candidates else None


def main():
    if not TSV.exists():
        raise SystemExit(f"Missing {TSV}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    with TSV.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) < 3:
                continue
            scene_id = row[0].strip()
            narration = row[1].strip()
            subtitle_ja = row[2].strip()
            subtitle_other = row[3].strip() if len(row) > 3 else ""
            rows.append((scene_id, narration, subtitle_ja, subtitle_other, find_image(scene_id)))

    body = []
    current = None
    for scene_id, narration, subtitle_ja, subtitle_other, image in rows:
        key = scene_key(scene_id)
        if key != current:
            current = key
            body.append(f'<h2>scene_{html.escape(key)}</h2>')
            if image:
                rel = image.relative_to(BASE).as_posix()
                body.append(f'<img class="scene-img" src="../{html.escape(rel)}" alt="scene_{html.escape(key)}">')
            else:
                body.append('<div class="missing">画像なし</div>')

        body.append('<section class="line">')
        body.append(f'<div class="id">{html.escape(scene_id)}</div>')
        body.append(f'<div><b>読み上げ</b><p>{html.escape(narration)}</p></div>')
        body.append(f'<div><b>日本語字幕</b><p>{html.escape(subtitle_ja)}</p></div>')
        if subtitle_other:
            body.append(f'<div><b>字幕2</b><p>{html.escape(subtitle_other)}</p></div>')
        body.append('</section>')

    page = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Scene Review</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; line-height: 1.65; color: #222; }}
    h1 {{ margin-bottom: 8px; }}
    h2 {{ margin-top: 42px; padding-top: 18px; border-top: 2px solid #ddd; }}
    .scene-img {{ width: min(100%, 920px); border: 1px solid #ddd; display: block; margin: 12px 0 18px; }}
    .missing {{ width: min(100%, 920px); padding: 40px; background: #f3f3f3; color: #777; margin: 12px 0 18px; }}
    .line {{ display: grid; grid-template-columns: 84px 1fr 1fr 1fr; gap: 14px; padding: 12px 0; border-top: 1px solid #eee; }}
    .id {{ font-weight: 700; color: #555; }}
    p {{ margin: 4px 0 0; white-space: pre-wrap; }}
    @media (max-width: 900px) {{ .line {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>Scene Review</h1>
  <p>画像、読み上げ、字幕の確認用HTMLです。</p>
  {''.join(body)}
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
