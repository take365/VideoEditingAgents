#!/usr/bin/env python3
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: create_project.py /path/to/new_project")
    dest = Path(sys.argv[1]).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for name in ["brief.md", "scene_plan.md", "image_prompts.md", "narration_segments.tsv", "license_and_tools_note.txt", ".env.example"]:
        target = dest / name
        if not target.exists():
            shutil.copy2(TEMPLATES / name, target)
    for dirname in ["images", "audio", "subtitles", "segments", "output", "review", "bgm"]:
        (dest / dirname).mkdir(exist_ok=True)
    print(dest)


if __name__ == "__main__":
    main()
