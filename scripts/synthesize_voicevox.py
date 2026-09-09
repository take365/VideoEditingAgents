#!/usr/bin/env python3
"""Generate WAV files from a project's narration_segments.tsv using local VOICEVOX."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--engine", default="http://127.0.0.1:50021")
    parser.add_argument("--speaker", type=int, default=3)
    parser.add_argument("--speed", type=float, default=1.05)
    args = parser.parse_args()
    tsv = args.project / "narration_segments.tsv"
    out_dir = args.project / "audio"
    query_dir = out_dir / "queries"
    out_dir.mkdir(exist_ok=True)
    query_dir.mkdir(exist_ok=True)
    if not tsv.exists():
        raise SystemExit(f"Missing {tsv}")
    with httpx.Client(timeout=120) as client:
        with tsv.open(encoding="utf-8", newline="") as handle:
            for row in csv.reader(handle, delimiter="\t"):
                if len(row) < 2 or not row[0].strip():
                    continue
                scene_id, text = row[0].strip(), row[1].strip()
                response = client.post(f"{args.engine.rstrip('/')}/audio_query", params={"text": text, "speaker": args.speaker})
                response.raise_for_status()
                query = response.json()
                query["speedScale"] = args.speed
                query["prePhonemeLength"] = 0.08
                query["postPhonemeLength"] = 0.18
                (query_dir / f"scene_{scene_id}.json").write_text(json.dumps(query, ensure_ascii=False, indent=2), encoding="utf-8")
                audio = client.post(f"{args.engine.rstrip('/')}/synthesis", params={"speaker": args.speaker}, json=query)
                audio.raise_for_status()
                (out_dir / f"scene_{scene_id}.wav").write_bytes(audio.content)
                print(f"created audio/scene_{scene_id}.wav")


if __name__ == "__main__":
    main()
