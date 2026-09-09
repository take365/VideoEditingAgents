#!/usr/bin/env python3
import csv
import json
import os
import re
import subprocess
from pathlib import Path

BASE = Path.cwd()
TSV = BASE / "narration_segments.tsv"
IMAGES = BASE / "images"
AUDIO = BASE / "audio"
SEGMENTS = BASE / "segments"
SUBS = BASE / "subtitles"
OUTPUT = BASE / "output"
BGM = BASE / "bgm" / "bgm.mp3"

WIDTH = 1920
HEIGHT = 1080
ENDING_HOLD_SECONDS = 4.0


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
    if not candidates and key.isdigit():
        media = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".m4v", ".webm"}
        candidates = sorted(path for path in IMAGES.iterdir() if path.is_file() and path.suffix.lower() in media)
        index = int(key) - 1
        if 0 <= index < len(candidates):
            return candidates[index]
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
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def ffmpeg_filter_path(path: Path) -> str:
    value = (path.resolve() if path.is_absolute() else path).as_posix()
    if os.name == "nt":
        value = value.replace(":", r"\:")
    return value.replace("'", r"\'")


def subtitle_font_size() -> int:
    settings_path = BASE / "worktree" / "video_settings.json"
    if not settings_path.exists():
        settings_path = BASE / "video_settings.json"
    if not settings_path.exists():
        return 42
    try:
        value = int(json.loads(settings_path.read_text(encoding="utf-8")).get("subtitle_font_size", 42))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 42
    return max(24, min(value, 96))


def apply_video_settings() -> None:
    global WIDTH, HEIGHT
    settings_path = BASE / "worktree" / "video_settings.json"
    if not settings_path.exists():
        settings_path = BASE / "video_settings.json"
    try:
        orientation = json.loads(settings_path.read_text(encoding="utf-8")).get("orientation", "landscape")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        orientation = "landscape"
    WIDTH, HEIGHT = (1080, 1920) if orientation == "portrait" else (1920, 1080)


def wrap_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if " " in text:
        words = text.split()
        lines, current = [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return r"\N".join(lines)
    return r"\N".join(text[i:i + max_chars] for i in range(0, len(text), max_chars))


def write_ass(path: Path, duration_seconds: float, ja: str, other: str):
    other_line = wrap_text(other, 58)
    ja_line = wrap_text(ja, 34)
    events = []
    if other_line:
        events.append(f"Dialogue: 0,{ass_time(0)},{ass_time(duration_seconds)},Other,,0,0,0,,{esc_ass(other_line)}")
    if ja_line:
        events.append(f"Dialogue: 1,{ass_time(0)},{ass_time(duration_seconds)},JA,,0,0,0,,{esc_ass(ja_line)}")
    content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: JA,Noto Sans CJK JP,{subtitle_font_size()},&H00FFFFFF,&H000000FF,&H00000000,&H99000000,1,0,0,0,100,100,0,0,1,3,0,2,120,120,58,1
Style: Other,Arial,34,&H00F4E6C5,&H000000FF,&H00000000,&H99000000,0,0,0,0,100,100,0,0,1,3,0,8,90,90,54,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(events)}
"""
    path.write_text(content, encoding="utf-8")


def make_segment(scene_id: str, image: Path, audio: Path, ja: str, other: str) -> Path:
    SEGMENTS.mkdir(parents=True, exist_ok=True)
    SUBS.mkdir(parents=True, exist_ok=True)
    out = SEGMENTS / f"scene_{scene_id}.mp4"
    ass = SUBS / f"scene_{scene_id}.ass"
    dur = duration(audio)
    write_ass(ass, dur, ja, other)
    # A relative ASS path avoids drive-letter parsing problems on Windows.
    subtitle_path = ass.relative_to(BASE) if ass.is_relative_to(BASE) else ass
    subtitle_filter = f"subtitles={ffmpeg_filter_path(subtitle_path)}"
    fonts_dir = Path("/usr/share/fonts")
    if fonts_dir.exists():
        subtitle_filter += f":fontsdir={ffmpeg_filter_path(fonts_dir)}"
    vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},{subtitle_filter}"
    visual_input = (["-stream_loop", "-1"] if image.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"} else ["-loop", "1"])
    run([
        "ffmpeg", "-y", *visual_input, "-t", f"{dur:.3f}", "-i", str(image), "-i", str(audio),
        "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)
    ])
    return out


def main():
    apply_video_settings()
    if not TSV.exists():
        raise SystemExit(f"Missing {TSV}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    with TSV.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) < 3:
                continue
            scene_id = row[0].strip()
            ja = row[2].strip()
            other = row[3].strip() if len(row) > 3 else ""
            rows.append((scene_id, find_image(scene_id), find_audio(scene_id), ja, other))

    segments = [make_segment(*row) for row in rows]

    if ENDING_HOLD_SECONDS and rows:
        last = rows[-1][1]
        ending = SEGMENTS / "scene_ending_hold.mp4"
        visual_input = (["-stream_loop", "-1"] if last.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"} else ["-loop", "1"])
        run([
            "ffmpeg", "-y", *visual_input, "-t", str(ENDING_HOLD_SECONDS), "-i", str(last),
            "-f", "lavfi", "-t", str(ENDING_HOLD_SECONDS), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-shortest", str(ending)
        ])
        segments.append(ending)

    list_file = BASE / "segments.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in segments), encoding="utf-8")
    no_bgm = OUTPUT / "video_no_bgm.mp4"
    final = OUTPUT / "video_bgm.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", "-movflags", "+faststart", str(no_bgm)])

    if BGM.exists():
        fade_out_start = max(0.0, duration(no_bgm) - 6.0)
        run([
            "ffmpeg", "-y", "-i", str(no_bgm), "-stream_loop", "-1", "-i", str(BGM),
            "-filter_complex",
            f"[1:a]volume=0.18,afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d=5[bgm];"
            "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(final)
        ])
        print(final)
    else:
        print(no_bgm)


if __name__ == "__main__":
    main()
