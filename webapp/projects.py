from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from .security import project_path


def create_project(data_root: Path, project_id: str, name: str, templates_root: Path | None = None) -> Path:
    project = project_path(data_root, project_id)
    project.mkdir(parents=True, exist_ok=False)
    for folder in ("uploads", "images", "audio", "subtitles", "segments", "output", "review", "bgm", "versions", "logs", "worktree"):
        (project / folder).mkdir()
    policy = (
        f"# Video project policy\n\nProject: {name}\n\n"
        "- Work only inside this project directory and its `worktree/`.\n"
        "- This project is for video editing: scripts, subtitles, audio, images, FFmpeg, and review artifacts.\n"
        "- Common requests: subtitle size changes update `worktree/video_settings.json` only; voice generation runs the local VOICEVOX adapter; video generation runs the existing slideshow script from the project root.\n"
        "- For subtitle-only changes, do not regenerate audio. For a script change, preserve unaffected scene audio and keep prior outputs.\n"
        "- Before declaring a render complete, verify the process exit code and inspect the generated MP4 with ffprobe.\n"
        "- Refuse unrelated software work, credential handling, destructive host changes, and unrequested external communication.\n"
        "- Do not edit, truncate, delete, or rewrite anything under `logs/`. Logs are append-only.\n"
        "- Do not read or expose secrets from `.env`, credentials, or files outside this project.\n"
        "- Use existing scripts first; keep changes reversible and record a summary in `versions/`.\n"
    )
    (project / "AGENTS.md").write_text(
        policy,
        encoding="utf-8",
    )
    (project / "worktree" / "AGENTS.md").write_text(policy, encoding="utf-8")
    (project / "project.json").write_text(json.dumps({"id": project_id, "name": name, "format": "video", "version": 1}, ensure_ascii=False, indent=2), encoding="utf-8")
    (project / "worktree" / "video_settings.json").write_text(json.dumps({"subtitle_font_size": 42}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if templates_root:
        source_scripts = templates_root.parent / "scripts"
        work_scripts = project / "worktree" / "scripts"
        work_scripts.mkdir(exist_ok=True)
        for filename in ("build_slideshow_video.py", "synthesize_voicevox.py", "generate_review_html.py"):
            source = source_scripts / filename
            if source.exists():
                shutil.copy2(source, work_scripts / filename)
    if templates_root:
        for filename in ("brief.md", "scene_plan.md", "image_prompts.md", "narration_segments.tsv", "license_and_tools_note.txt"):
            source = templates_root / filename
            if source.exists():
                shutil.copy2(source, project / filename)
    return project


def seed_demo_project(data_root: Path, project_id: str, templates_root: Path, sample_root: Path) -> Path:
    project = create_project(data_root, project_id, "サンプル：2枚画像から動画生成", templates_root)
    (project / "worktree" / "images").mkdir(parents=True, exist_ok=True)
    for filename in ("scene_01.png", "scene_02.png"):
        source = sample_root / "images" / filename
        if source.exists():
            shutil.copy2(source, project / "images" / filename)
            shutil.copy2(source, project / "worktree" / "images" / filename)
    (project / "scenario.md").write_text(
        "# サンプルシナリオ\n\n"
        "このサンプルは、シナリオと画像を用意して、音声と字幕付き動画を一度に生成する流れを確認するための案件です。\n\n"
        "画面の「動画を生成」を押すと、台本から音声を作成し、2枚の画像と字幕を合成します。\n",
        encoding="utf-8",
    )
    (project / "narration_segments.tsv").write_text(
        "01\tまずはシナリオと画像を用意します。\tまずはシナリオと画像を用意します。\t\n"
        "02\tあとは動画を生成するだけで、音声と字幕付きの動画が完成します。\t音声と字幕付きの動画が完成します。\t\n",
        encoding="utf-8",
    )
    shutil.copy2(project / "narration_segments.tsv", project / "worktree" / "narration_segments.tsv")
    return project
