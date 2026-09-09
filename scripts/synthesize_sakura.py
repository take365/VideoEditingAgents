#!/usr/bin/env python3
"""Generate WAV files through Sakura AI Engine's VOICEVOX-compatible API."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
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
    headers = {"Authorization": f"Bearer {args.token}"}
    with httpx.Client(timeout=120, headers=headers) as client, tsv.open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) < 2 or not row[0].strip():
                continue
            scene_id, text = row[0].strip(), row[1].strip()
            query = client.post(f"{args.base_url.rstrip('/')}/tts/v1/audio_query", params={"text": text, "speaker": args.speaker})
            query.raise_for_status()
            payload = query.json()
            payload["speedScale"] = args.speed
            payload["prePhonemeLength"] = 0.08
            payload["postPhonemeLength"] = 0.18
            (query_dir / f"scene_{scene_id}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            audio = client.post(f"{args.base_url.rstrip('/')}/tts/v1/synthesis", params={"speaker": args.speaker}, json=payload)
            audio.raise_for_status()
            (out_dir / f"scene_{scene_id}.wav").write_bytes(audio.content)
            print(f"created audio/scene_{scene_id}.wav")


if __name__ == "__main__":
    main()
