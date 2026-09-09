#!/usr/bin/env python3
import csv
import json
import math
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
TSV = BASE / "narration" / "segments.tsv"
IMAGES = BASE / "scenes" / "images"
AUDIO = BASE / "audio"
SEGMENTS = BASE / "segments"
SUBS = BASE / "subtitles"
OUTPUT = BASE / "output"
BGM = BASE.parent / "sample" / "bgm" / "03_Tabiji_no_Hate_Greenfield.mp3"

WIDTH = 1920
HEIGHT = 1080
ENDING_HOLD_SECONDS = 5.0
ENDING_FADE_SECONDS = 2.2
TITLE_SCENE_ID = "01a"
TITLE_ES = "La historia de un luchador que logró numerosos milagros"
TITLE_JP = "メキシコの水処理業界で数々の奇跡を起こした挑戦者の物語"

SCENE_FILES = {
    "01": "scene_01_mexico_treatment_plant_intro.png",
    "02": "scene_02_exhibition_meets_volute.png",
    "03": "scene_03_volute_mechanism.png",
    "04": "scene_04_sales_across_mexico.png",
    "05": "scene_05_conflict_at_previous_company.png",
    "06": "scene_06_decision_to_start_company.png",
    "07": "scene_07_startup_with_little_money.png",
    "08": "scene_08_old_pickup_truck.png",
    "09": "scene_09_truck_with_demo_unit.png",
    "10": "scene_10_customer_demo.png",
    "11": "scene_11_jose_luis_support.png",
    "12": "scene_12_pandemic_never_give_up.png",
    "13": "scene_13_large_order_success.png",
    "13b": "scene_13b_san_antonio_project_explanation.png",
    "13c": "scene_13b_san_antonio_project_explanation.png",
    "14a": "scene_13b_san_antonio_project_explanation.png",
    "14b": "scene_13b_san_antonio_project_explanation.png",
    "14c": "scene_13b_san_antonio_project_explanation.png",
    "14d": "scene_13b_san_antonio_project_explanation.png",
    "14": "scene_14_san_antonio_future_team.png",
}


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


def split_sentences(text: str) -> list[str]:
    parts = re.findall(r"[^。！？.!?]+[。！？.!?]?", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str, max_chars: int, lang: str) -> list[str]:
    if lang == "es":
        words = text.split()
        chunks, current = [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = word
        if current:
            chunks.append(current)
        return chunks or [text]

    chunks, current = [], ""
    for sentence in split_sentences(text):
        if len(current) + len(sentence) <= max_chars:
            current += sentence
        else:
            if current:
                chunks.append(current)
            while len(sentence) > max_chars:
                chunks.append(sentence[:max_chars])
                sentence = sentence[max_chars:]
            current = sentence
    if current:
        chunks.append(current)
    return chunks or [text]


def visual_len(token: str) -> float:
    # ASCII words/numbers are narrower than Japanese glyphs in the subtitle font.
    return sum(0.58 if ord(ch) < 128 else 1.0 for ch in token)


def wrap_jp(text: str, limit: int = 40) -> str:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*|[ァ-ヶー]+|[ぁ-んー]+|[一-龯々]+|.", text)
    lines, current, current_len = [], "", 0.0
    for token in tokens:
        token_len = visual_len(token)
        if current and token in "。、！？,.!?）」』】":
            current += token
            current_len += token_len
        elif current and current_len + token_len > limit:
            lines.append(current)
            current, current_len = token, token_len
        else:
            current += token
            current_len += token_len
    if current:
        lines.append(current)
    return r"\N".join(lines)


def wrap_es(text: str, limit: int = 94) -> str:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return r"\N".join(lines)


def ass_escape(text: str) -> str:
    # Preserve ASS newline marker \N while escaping style braces.
    return text.replace("{", "\\{").replace("}", "\\}")


def timed_chunks(jp: str, es: str, scene_duration: float):
    jp_chunks = chunk_text(jp, 92, "jp")
    es_chunks = chunk_text(es, 220, "es")
    n = max(len(jp_chunks), len(es_chunks))
    if len(jp_chunks) < n:
        jp_chunks += [""] * (n - len(jp_chunks))
    if len(es_chunks) < n:
        es_chunks += [""] * (n - len(es_chunks))
    weights = [max(1, len(j) + len(e) * 0.8) for j, e in zip(jp_chunks, es_chunks)]
    total = sum(weights)
    cursor = 0.0
    result = []
    for i, (j, e, w) in enumerate(zip(jp_chunks, es_chunks, weights)):
        end = scene_duration if i == n - 1 else min(scene_duration, cursor + scene_duration * w / total)
        result.append((cursor, end, j, e))
        cursor = end
    return result


def title_events(scene_id: str, scene_duration: float) -> list[str]:
    if scene_id != TITLE_SCENE_ID:
        return []
    end = ass_time(min(scene_duration, 7.5))
    return [
        f"Dialogue: 2,0:00:00.35,{end},TitleES,,0,0,0,,{{\\fad(500,700)}}{ass_escape(TITLE_ES)}",
        f"Dialogue: 3,0:00:00.70,{end},TitleJP,,0,0,0,,{{\\fad(500,700)}}{ass_escape(TITLE_JP)}",
    ]


def write_ass(path: Path, scene_id: str, jp: str, es: str, scene_duration: float):
    events = []
    events.extend(title_events(scene_id, scene_duration))
    if scene_id != TITLE_SCENE_ID:
        for start, end, jp_chunk, es_chunk in timed_chunks(jp, es, scene_duration):
            if jp_chunk:
                events.append(
                    f"Dialogue: 0,{ass_time(start)},{ass_time(end)},JP,,0,0,0,,{ass_escape(wrap_jp(jp_chunk))}"
                )
            if es_chunk:
                events.append(
                    f"Dialogue: 1,{ass_time(start)},{ass_time(end)},ES,,0,0,0,,{ass_escape(wrap_es(es_chunk))}"
                )

    content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: JP,Noto Sans CJK JP,37,&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,1,0,0,0,100,100,0,0,1,3,0,2,160,160,126,1
Style: ES,Noto Sans CJK JP,35,&H00D8F0FF,&H00FFFFFF,&H00000000,&H99000000,1,0,0,0,100,100,0,0,1,3,0,2,35,35,45,1
Style: TitleES,Noto Sans CJK JP,42,&H00D8F0FF,&H00FFFFFF,&H00201008,&H66000000,1,0,0,0,100,100,0,0,1,3,1,7,120,120,240,1
Style: TitleJP,Noto Sans CJK JP,58,&H00FFFFFF,&H00FFFFFF,&H00201008,&H66000000,1,0,0,0,100,100,0,0,1,4,1,7,120,120,305,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(events)}
"""
    path.write_text(content, encoding="utf-8")


def scene_image(scene_id: str) -> Path:
    if scene_id in SCENE_FILES:
        return IMAGES / SCENE_FILES[scene_id]
    base_id = re.match(r"\d+", scene_id)
    if base_id and base_id.group(0) in SCENE_FILES:
        return IMAGES / SCENE_FILES[base_id.group(0)]
    raise KeyError(f"No image mapping for scene id: {scene_id}")


def main():
    for d in (SEGMENTS, SUBS, OUTPUT):
        d.mkdir(parents=True, exist_ok=True)

    rows = []
    with TSV.open(encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) >= 4:
                rows.append((row[0], row[1], row[2], row[3]))

    concat = BASE / "segments.txt"
    with concat.open("w", encoding="utf-8") as cf:
        for scene_id, _audio_text, jp_sub, es_sub in rows:
            image = scene_image(scene_id)
            wav = AUDIO / f"scene_{scene_id}.wav"
            ass = SUBS / f"scene_{scene_id}.ass"
            segment = SEGMENTS / f"scene_{scene_id}.mp4"
            scene_duration = duration(wav) + 0.65
            write_ass(ass, scene_id, jp_sub, es_sub, scene_duration)
            vf_filters = [
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase",
                f"crop={WIDTH}:{HEIGHT}",
            ]
            if scene_id != TITLE_SCENE_ID:
                vf_filters.append("drawbox=x=0:y=830:w=iw:h=238:color=black@0.50:t=fill")
            vf_filters.extend([
                f"subtitles='{ass}':fontsdir='/usr/share/fonts/opentype/noto'",
                "format=yuv420p",
            ])
            vf = ",".join(vf_filters)
            run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
                "-loop", "1", "-t", f"{scene_duration:.3f}", "-i", str(image),
                "-i", str(wav),
                "-vf", vf,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "25",
                "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
                "-shortest", str(segment),
            ])
            cf.write(f"file '{segment}'\n")

        ending = SEGMENTS / "scene_ending_hold.mp4"
        ending_image = IMAGES / "scene_14_san_antonio_future_team.png"
        ending_vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},"
            f"fade=t=out:st={ENDING_HOLD_SECONDS - ENDING_FADE_SECONDS:.3f}:d={ENDING_FADE_SECONDS:.3f},"
            "format=yuv420p"
        )
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-loop", "1", "-t", f"{ENDING_HOLD_SECONDS:.3f}", "-i", str(ending_image),
            "-f", "lavfi", "-t", f"{ENDING_HOLD_SECONDS:.3f}", "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
            "-vf", ending_vf,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "25",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            "-shortest", str(ending),
        ])
        cf.write(f"file '{ending}'\n")

    no_bgm = OUTPUT / "amcon_production_v2_no_bgm.mp4"
    final = OUTPUT / "amcon_production_v2_aida_bilingual_bgm.mp4"
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-movflags", "+faststart", str(no_bgm),
    ])
    fade_out_start = max(0.0, duration(no_bgm) - 7.0)
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(no_bgm), "-stream_loop", "-1", "-i", str(BGM),
        "-filter_complex",
        f"[1:a]volume='if(isnan(t),0.12,if(lt(t,95),0.12,min(0.24,0.12+(t-95)*0.0016)))':eval=frame,"
        f"afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.3f}:d=5[bgm];"
        "[0:a]volume=1.0[voice];"
        "[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map", "0:v:0", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", str(final),
    ])
    print(final)


if __name__ == "__main__":
    main()
