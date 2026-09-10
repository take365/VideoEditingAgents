#!/usr/bin/env python3
"""Create a technical, visual-capture, and narration review for a rendered video."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(video: Path) -> dict:
    result = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)])
    return json.loads(result.stdout)


def duration(info: dict) -> float:
    values = [float(info.get("format", {}).get("duration", 0) or 0)]
    values.extend(float(stream.get("duration", 0) or 0) for stream in info.get("streams", []))
    values = [value for value in values if value > 0]
    return min(values) if values else 0.0


def expected_text(project: Path) -> str:
    path = project / "narration_segments.tsv"
    if not path.exists():
        return ""
    lines = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() and not line.startswith("scene_id"):
            fields = line.split("\t")
            if len(fields) > 1:
                lines.append(fields[1])
    return "".join(lines)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("、", "").replace("。", "")


def transcribe(video: Path, review_dir: Path, model_name: str) -> tuple[str, list[dict], str | None]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return "", [], "faster-whisper is not installed; install requirements-local.txt"
    try:
        # Prefer CPU so a machine without the CUDA runtime can review locally.
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(video), language="ja", vad_filter=True)
        rows = []
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text)
            rows.append({"start": segment.start, "end": segment.end, "text": segment.text})
        text = "".join(text_parts).strip()
        (review_dir / "transcription.txt").write_text(text + "\n", encoding="utf-8")
        (review_dir / "transcription.json").write_text(
            json.dumps({"model": model_name, "language": info.language, "segments": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return text, rows, None
    except Exception as exc:  # Keep the rendered video usable if optional ASR fails.
        return "", [], f"local transcription failed: {type(exc).__name__}: {exc}"


def capture_frames(video: Path, capture_dir: Path, length: float) -> list[Path]:
    capture_dir.mkdir(parents=True, exist_ok=True)
    for old in capture_dir.glob("frame_*.jpg"):
        old.unlink()
    # Some containers report a duration slightly beyond the last decodable frame.
    points = [0.0, max(0.0, length * 0.5), max(0.0, length * 0.9)]
    paths = []
    for index, point in enumerate(points, 1):
        target = capture_dir / f"frame_{index:02d}.jpg"
        run(["ffmpeg", "-y", "-ss", f"{point:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(target)])
        paths.append(target)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--model", default="large-v3-turbo")
    args = parser.parse_args()
    project = args.project.resolve()
    review_dir = project / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    video = next((project / "output" / name for name in ("video_bgm.mp4", "video_no_bgm.mp4") if (project / "output" / name).exists()), None)
    if video is None:
        raise SystemExit("rendered MP4 not found in output/")

    info = probe(video)
    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    length = duration(info)
    captures = capture_frames(video, review_dir / "captures", length)
    asr_text, segments, asr_error = transcribe(video, review_dir, args.model)
    expected = expected_text(project)
    similarity = None
    if expected and asr_text:
        similarity = difflib.SequenceMatcher(None, normalize(expected), normalize(asr_text)).ratio()

    checks = [
        ("MP4 exists", "OK"),
        ("Video codec", video_stream.get("codec_name", "unknown")),
        ("Resolution", f"{video_stream.get('width', '?')}x{video_stream.get('height', '?')}"),
        ("Audio track", "OK" if audio_stream else "MISSING"),
        ("Duration", f"{length:.2f}s"),
        ("Captures", f"{len(captures)} frames"),
    ]
    check_rows = "".join(f"<tr><th>{name}</th><td>{value}</td></tr>" for name, value in checks)
    capture_html = "".join(f'<figure><img src="captures/{p.name}" alt="{p.name}"><figcaption>{p.name}</figcaption></figure>' for p in captures)
    asr_status = "未実施: " + asr_error if asr_error else f"実施済み（{args.model}）"
    similarity_html = "未算出" if similarity is None else f"{similarity:.1%}（参考値。最終確認は音声を再生して行う）"
    html = f"""<!doctype html><html lang=\"ja\"><meta charset=\"utf-8\"><title>動画レビュー</title>
<style>body{{font-family:system-ui,sans-serif;line-height:1.6;max-width:1100px;margin:2rem auto;padding:0 1rem}} table{{border-collapse:collapse}}th,td{{border:1px solid #ccc;padding:.35rem .7rem;text-align:left}} .captures{{display:flex;gap:1rem;flex-wrap:wrap}} figure{{margin:0;width:min(31%,320px)}} img{{max-width:100%;height:auto;border:1px solid #ccc}} .warn{{background:#fff4d6;padding:1rem}}</style>
<h1>動画レビュー</h1><p>対象: {video.name} / {length:.2f}秒</p><h2>自動チェック</h2><table>{check_rows}</table>
<h2>キャプチャ</h2><p>以下を目視確認: 画像の破損、字幕の豆腐文字（□）、位置・切れ、行間・改行、背景とのコントラスト。</p><div class=\"captures\">{capture_html}</div>
<h2>ナレーション再文字起こし</h2><p>状態: {asr_status}</p><p>原稿との類似度: {similarity_html}</p>
<h3>原稿</h3><pre>{expected or 'narration_segments.tsv がありません'}</pre><h3>再文字起こし</h3><pre>{asr_text or '結果なし'}</pre>
<div class=\"warn\">類似度は読み間違いの候補を見つける補助指標です。固有名詞・数字・助詞は、音声を再生して確認してください。</div></html>"""
    (review_dir / "video_review.html").write_text(html, encoding="utf-8")
    print(review_dir / "video_review.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
