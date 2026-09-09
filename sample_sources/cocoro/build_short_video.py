#!/usr/bin/env python3
import csv
import json
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
TSV = BASE / "narration_segments.tsv"
IMAGES = BASE / "images"
AUDIO = BASE / "audio_aivis_nise_normal"
SEGMENTS = BASE / "segments"
SUBS = BASE / "subtitles"
OUTPUT = BASE / "output"

WIDTH = 1080
HEIGHT = 1920
ENDING_HOLD_SECONDS = 2.5


def run(cmd):
    subprocess.run(cmd, check=True)


def duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path)
    ])
    return float(json.loads(out)["format"]["duration"])


def ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def scene_key(scene_id: str) -> str:
    m = re.match(r"(\d+)", scene_id)
    return m.group(1) if m else scene_id


def find_image(scene_id: str) -> Path:
    key = scene_key(scene_id)
    candidates = sorted(IMAGES.glob(f"scene_{key}*.*")) or sorted(IMAGES.glob(f"{key}*.*"))
    if not candidates:
        raise FileNotFoundError(f"No image for scene {scene_id}")
    return candidates[0]


def find_audio(scene_id: str) -> Path:
    for suffix in [".wav", ".mp3", ".m4a"]:
        path = AUDIO / f"scene_{scene_id}{suffix}"
        if path.exists():
            return path
    raise FileNotFoundError(f"No audio for scene {scene_id}")


def esc_ass(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}")


def wrap_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    lines = []
    rest = text
    while len(rest) > max_chars:
        cut = -1
        for mark in ["。", "、"]:
            pos = rest.rfind(mark, 0, max_chars + 1)
            if pos >= 0:
                cut = pos + 1
                break
        if cut <= 0:
            cut = max_chars
            while cut > 1 and rest[cut - 1] in "。、,.!?！？":
                cut -= 1
        lines.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        if len(rest) <= 2 and lines:
            lines[-1] += rest
        else:
            lines.append(rest)
    return r"\N".join(lines)


def write_ass(path: Path, duration_seconds: float, ja: str):
    ja_line = wrap_text(ja, 18)
    content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: JA,Noto Sans CJK JP,58,&H00FFFFFF,&H000000FF,&H553A2A22,&H993A2A22,1,0,0,0,100,100,0,0,1,4,1,2,78,78,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,{ass_time(0)},{ass_time(duration_seconds)},JA,,0,0,0,,{esc_ass(ja_line)}
"""
    path.write_text(content, encoding="utf-8")


def video_filter(image: Path, ass: Path | None = None) -> str:
    filters = [
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase",
        f"crop={WIDTH}:{HEIGHT}",
    ]
    if ass is not None:
        ass_path = ass.as_posix().replace(":", "\\:")
        filters.append(f"subtitles='{ass_path}'")
    return ",".join(filters)


def make_segment(scene_id: str, image: Path, audio: Path, ja: str) -> Path:
    SEGMENTS.mkdir(parents=True, exist_ok=True)
    SUBS.mkdir(parents=True, exist_ok=True)
    out = SEGMENTS / f"scene_{scene_id}.mp4"
    ass = SUBS / f"scene_{scene_id}.ass"
    dur = duration(audio)
    write_ass(ass, dur, ja)
    run([
        "ffmpeg", "-y", "-loop", "1", "-t", f"{dur:.3f}", "-i", str(image), "-i", str(audio),
        "-vf", video_filter(image, ass), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)
    ])
    return out


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    with TSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            scene_id = row["scene_id"].strip()
            ja = row["subtitle_ja"].strip()
            rows.append((scene_id, find_image(scene_id), find_audio(scene_id), ja))

    segments = [make_segment(*row) for row in rows]

    if ENDING_HOLD_SECONDS and rows:
        last = rows[-1][1]
        ending = SEGMENTS / "scene_ending_hold.mp4"
        run([
            "ffmpeg", "-y", "-loop", "1", "-t", str(ENDING_HOLD_SECONDS), "-i", str(last),
            "-f", "lavfi", "-t", str(ENDING_HOLD_SECONDS), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", video_filter(last), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-shortest", str(ending)
        ])
        segments.append(ending)

    list_file = BASE / "segments.txt"
    list_file.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segments), encoding="utf-8")
    final = OUTPUT / "cocoro_short_aivis_nise_normal.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", "-movflags", "+faststart", str(final)])
    print(final)


if __name__ == "__main__":
    main()
