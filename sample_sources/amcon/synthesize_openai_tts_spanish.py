#!/usr/bin/env python3
import csv
import json
import os
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).resolve().parent
ENV_ROOT = BASE.parent / "video_samples"
TSV = BASE / "narration" / "segments.tsv"
OUT = BASE / "audio"
LOGS = BASE / "logs"

MODEL = "gpt-4o-mini-tts"
VOICE = "onyx"

INSTRUCTIONS = {
    "early": (
        "Speak in Mexican Spanish with a serious, calm corporate documentary narration style. "
        "Use a mature, grounded male narrator tone, warm but restrained. "
        "Use natural Mexican Spanish pronunciation, rhythm, and intonation; do not sound like Spain Spanish. "
        "Pace clearly and professionally. Avoid theatrical overacting."
    ),
    "middle": (
        "Speak in Mexican Spanish with a serious corporate documentary narration style. "
        "Keep a mature, grounded male tone, but add more momentum and emotional weight. "
        "The mood is challenge, hardship, persistence, and determination. "
        "Use natural Mexican Spanish pronunciation and rhythm, not Spain Spanish. "
        "Pace naturally with clear articulation; do not overact."
    ),
    "climax": (
        "Speak in Mexican Spanish like the climax of an inspiring corporate documentary. "
        "Use a mature, grounded male narrator tone. "
        "Add emotional uplift, scale, and a sense of achievement. "
        "Use natural Mexican Spanish pronunciation and rhythm; do not sound like Spain Spanish. "
        "Do not shout or overact; keep it professional, sincere, and moving. "
        "Slightly emphasize key achievements and final phrases."
    ),
}


def load_env():
    for env_name in [".env", ".evn"]:
        path = ENV_ROOT / env_name
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


def instruction_key(scene_id: str) -> str:
    major = int("".join(ch for ch in scene_id if ch.isdigit())[:2])
    if major <= 6:
        return "early"
    if major <= 12:
        return "middle"
    return "climax"


def main():
    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY/API_KEY not found")

    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    client = OpenAI()

    logs = []
    with TSV.open(encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) < 4:
                continue
            scene_id, text = row[0], row[3]
            key = instruction_key(scene_id)
            out_file = OUT / f"scene_{scene_id}.mp3"
            with client.audio.speech.with_streaming_response.create(
                model=MODEL,
                voice=VOICE,
                input=text,
                instructions=INSTRUCTIONS[key],
                response_format="mp3",
            ) as response:
                response.stream_to_file(out_file)
            logs.append({
                "scene_id": scene_id,
                "model": MODEL,
                "voice": VOICE,
                "instruction_key": key,
                "output": str(out_file),
                "bytes": out_file.stat().st_size,
            })
            print(f"created {out_file} ({key})")

    (LOGS / "openai_tts_usage_v2_6_es_mx.json").write_text(
        json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
