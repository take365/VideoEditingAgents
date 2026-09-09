#!/usr/bin/env python3
import csv
import os
from pathlib import Path

from openai import OpenAI

BASE = Path.cwd()
TSV = BASE / "narration_segments.tsv"
OUT = BASE / "audio"
MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
VOICE = os.environ.get("OPENAI_TTS_VOICE", "onyx")
INSTRUCTIONS = os.environ.get(
    "OPENAI_TTS_INSTRUCTIONS",
    "Speak as a calm, serious corporate documentary narrator. Clear, warm, and professional.",
)


def load_env():
    for path in [BASE / ".env", BASE / ".evn"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value
    if not os.environ.get("OPENAI_API_KEY") and os.environ.get("API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["API_KEY"]


def main():
    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY/API_KEY not found")
    if not TSV.exists():
        raise SystemExit(f"Missing {TSV}")

    OUT.mkdir(parents=True, exist_ok=True)
    client = OpenAI()

    with TSV.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) < 2:
                continue
            scene_id = row[0].strip()
            text = row[1].strip()
            if not scene_id or not text:
                continue
            out = OUT / f"scene_{scene_id}.mp3"
            with client.audio.speech.with_streaming_response.create(
                model=MODEL,
                voice=VOICE,
                input=text,
                instructions=INSTRUCTIONS,
            ) as response:
                response.stream_to_file(out)
            print(out)


if __name__ == "__main__":
    main()
