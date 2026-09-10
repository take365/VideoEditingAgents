from __future__ import annotations

import subprocess
import sys
import threading
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .db import Database
from .security import project_path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobManager:
    def __init__(self, db: Database, data_root: Path, repo_root: Path):
        self.db = db
        self.data_root = data_root
        self.repo_root = repo_root
        self.lock = threading.Lock()
        self.render_slot = threading.Semaphore(1)
        self.running: dict[str, subprocess.Popen[str]] = {}
        self.completion_handler: Callable[[str, str, str, int, str, str | None], None] | None = None

    def set_completion_handler(self, handler: Callable[[str, str, str, int, str, str | None], None]) -> None:
        self.completion_handler = handler

    def recover(self) -> None:
        for row in self.db.execute("SELECT id FROM jobs WHERE status='running'"):
            self.db.execute("UPDATE jobs SET status='failed', error=?, message=?, updated_at=? WHERE id=?", ("server restarted", "再起動時に未完了ジョブを停止しました", now(), row["id"]))

    def get(self, job_id: str) -> dict:
        return self.db.one("SELECT * FROM jobs WHERE id=?", (job_id,)) or {}

    def list_for_project(self, project_id: str) -> list[dict]:
        return self.db.execute("SELECT * FROM jobs WHERE project_id=? ORDER BY created_at DESC", (project_id,))

    def start_render(self, project_id: str) -> str:
        job_id = uuid.uuid4().hex
        timestamp = now()
        self.db.execute("INSERT INTO jobs(id,project_id,kind,status,created_at,updated_at) VALUES(?,?,?,'queued',?,?)", (job_id, project_id, "render", timestamp, timestamp))
        threading.Thread(target=self._render, args=(job_id, project_id), daemon=True).start()
        return job_id

    def _update(self, job_id: str, status: str, progress: int, message: str, error: str | None = None) -> None:
        self.db.execute("UPDATE jobs SET status=?,progress=?,message=?,error=?,updated_at=? WHERE id=?", (status, progress, message, error, now(), job_id))

    def _add_message(self, project_id: str, content: str) -> None:
        self.db.execute(
            "INSERT INTO messages(project_id,role,content,created_at) VALUES(?,?,?,?)",
            (project_id, "assistant", content, now()),
        )

    def _notify_completion(self, project_id: str, job_id: str, status: str, progress: int, message: str, error: str | None = None) -> None:
        if not self.completion_handler:
            return
        try:
            self.completion_handler(project_id, job_id, status, progress, message, error)
        except Exception:
            # Reporting to Codex must never change the already-recorded job result.
            return

    def _sync_worktree_inputs(self, project: Path) -> None:
        """Copy Codex-authored inputs into the legacy renderer's project root."""
        worktree = project / "worktree"
        for filename in ("narration_segments.tsv", "script.md", "brief.md", "scene_plan.md", "image_prompts.md", "license_and_tools_note.txt"):
            source = worktree / filename
            if source.is_file():
                shutil.copy2(source, project / filename)
        for folder in ("images", "audio", "subtitles", "bgm"):
            source_dir = worktree / folder
            target_dir = project / folder
            if not source_dir.is_dir():
                continue
            target_dir.mkdir(exist_ok=True)
            for source in source_dir.iterdir():
                if source.is_file():
                    shutil.copy2(source, target_dir / source.name)

    def _register_artifact(self, project_id: str, job_id: str, project: Path, path: Path) -> None:
        relative = str(path.relative_to(project))
        existing = self.db.one("SELECT id FROM artifacts WHERE project_id=? AND path=? ORDER BY id DESC LIMIT 1", (project_id, relative))
        values = (path.name, path.suffix.lstrip("."), now())
        if existing:
            self.db.execute("UPDATE artifacts SET job_id=?,name=?,kind=?,created_at=? WHERE id=?", (job_id, *values, existing["id"]))
        else:
            self.db.execute("INSERT INTO artifacts(project_id,job_id,name,path,kind,created_at) VALUES(?,?,?,?,?,?)", (project_id, job_id, path.name, relative, path.suffix.lstrip("."), now()))

    def _render(self, job_id: str, project_id: str) -> None:
        project = project_path(self.data_root, project_id)
        with self.render_slot:
            try:
                self._update(job_id, "running", 5, "入力を確認中")
                self._sync_worktree_inputs(project)
                script = self.repo_root / "scripts" / "build_slideshow_video.py"
                if not script.exists():
                    script = project / "worktree" / "scripts" / "build_slideshow_video.py"
                if not script.exists():
                    raise RuntimeError("既存の動画生成スクリプトが見つかりません")
                self._update(job_id, "running", 15, "FFmpegで動画を合成中")
                process = subprocess.Popen([sys.executable, str(script)], cwd=project, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                with self.lock:
                    self.running[job_id] = process
                output, _ = process.communicate()
                with self.lock:
                    self.running.pop(job_id, None)
                if process.returncode != 0:
                    detail = output[-1200:].strip()
                    raise RuntimeError(f"FFmpegによる動画生成に失敗しました: {detail}")

                review_script = self.repo_root / "scripts" / "generate_review_html.py"
                if not review_script.exists():
                    review_script = project / "worktree" / "scripts" / "generate_review_html.py"
                if (project / "narration_segments.tsv").exists() and review_script.exists():
                    self._update(job_id, "running", 90, "レビューHTMLを生成中")
                    review = subprocess.run([sys.executable, str(review_script)], cwd=project, capture_output=True, text=True)
                    if review.returncode != 0:
                        output += f"\n[review warning]\n{review.stdout[-2000:]}\n{review.stderr[-2000:]}"

                video_review_script = self.repo_root / "scripts" / "review_video.py"
                if not video_review_script.exists():
                    video_review_script = project / "worktree" / "scripts" / "review_video.py"
                if video_review_script.exists():
                    self._update(job_id, "running", 95, "動画キャプチャと音声レビューを生成中")
                    video_review = subprocess.run(
                        [sys.executable, str(video_review_script), "--project", str(project)],
                        cwd=project,
                        capture_output=True,
                        text=True,
                    )
                    if video_review.returncode != 0:
                        output += f"\n[video review warning]\n{video_review.stdout[-2000:]}\n{video_review.stderr[-2000:]}"

                self._update(job_id, "succeeded", 100, "動画生成とレビューが完了しました")
                for path in sorted((project / "output").glob("*")) + sorted((project / "review").glob("*")):
                    if path.is_file():
                        self._register_artifact(project_id, job_id, project, path)
                self._add_message(project_id, "動画生成とレビューが完了しました。動画、キャプチャ、レビューHTMLを確認できます。")
                self._notify_completion(project_id, job_id, "succeeded", 100, "動画生成とレビューが完了しました")
                (project / "logs").mkdir(exist_ok=True)
                with (project / "logs" / "render.log").open("a", encoding="utf-8") as log:
                    log.write(f"[{now()}] job={job_id} returncode={process.returncode}\n{output[-4000:]}\n")
            except Exception as exc:
                progress = int(self.get(job_id).get("progress") or 0)
                self._update(job_id, "failed", progress, "動画生成に失敗しました", str(exc))
                self._add_message(project_id, f"動画生成に失敗しました（{progress}%地点）。{exc}")
                self._notify_completion(project_id, job_id, "failed", progress, "動画生成に失敗しました", str(exc))
                (project / "logs").mkdir(exist_ok=True)
                with (project / "logs" / "render.log").open("a", encoding="utf-8") as log:
                    log.write(f"[{now()}] job={job_id} failed={exc}\n")

    def cancel(self, job_id: str) -> dict:
        with self.lock:
            process = self.running.get(job_id)
        if process and process.poll() is None:
            process.terminate()
        self._update(job_id, "cancelled", self.get(job_id).get("progress", 0), "処理を中止しました")
        return self.get(job_id)
