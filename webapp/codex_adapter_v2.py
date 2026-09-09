from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

from codex_cli_bin import bundled_codex_path
from openai_codex import ApprovalMode, Codex, CodexConfig, Sandbox


class CodexAppServer:
    """Drive the official Codex Python SDK without exposing app-server over HTTP."""

    def __init__(self, command: str, cwd: str, approval_policy: str, sandbox: str, model: str):
        self.command = command
        self.cwd = cwd or None
        self.approval_mode = ApprovalMode.deny_all if approval_policy == "deny_all" else ApprovalMode.auto_review
        self.sandbox = {
            "read-only": Sandbox.read_only,
            "workspace-write": Sandbox.workspace_write,
            "full-access": Sandbox.full_access,
        }.get(sandbox, Sandbox.workspace_write)
        self.model = model
        self.client: Codex | None = None
        self.active_threads: dict[str, Any] = {}
        self.lock = threading.RLock()

    def _ensure(self) -> Codex:
        if self.client is not None:
            return self.client
        config = CodexConfig(
            codex_bin=str(bundled_codex_path()),
            cwd=self.cwd,
            client_name="video_editing_agents",
            client_title="VideoEditingAgents",
            client_version="0.1.0",
        )
        self.client = Codex(config)
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            self.client.close()
            self.client = None
            raise RuntimeError("OPENAI_API_KEYが設定されていません")
        self.client.login_api_key(api_key)
        return self.client

    def close(self) -> None:
        with self.lock:
            if self.client is not None:
                self.client.close()
            self.client = None
            self.active_threads.clear()

    def _thread_options(self, project_root: Path) -> dict[str, Any]:
        return {
            "cwd": str(project_root),
            "model": self.model,
            "approval_mode": self.approval_mode,
            "sandbox": self.sandbox,
            "service_name": "video_editing_agents",
        }

    @staticmethod
    def _result(thread: Any, result: Any) -> dict[str, Any]:
        status = getattr(result.status, "value", result.status)
        return {
            "thread": {"id": thread.id},
            "turn": {"id": result.id, "status": status},
            "text": result.final_response or "",
            "events": [],
        }

    @staticmethod
    def _dump(value: Any) -> dict[str, Any]:
        return value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)

    def account(self) -> dict[str, Any]:
        with self.lock:
            return self._dump(self._ensure().account())

    def login(self) -> dict[str, Any]:
        with self.lock:
            return self._dump(self._ensure().account())

    def start_thread(self, project_root: Path, prompt: str) -> dict[str, Any]:
        with self.lock:
            thread = self._ensure().thread_start(**self._thread_options(project_root))
            self.active_threads[thread.id] = thread
            if not prompt:
                return {"thread": {"id": thread.id}}
            result = thread.run(
                prompt,
                model=self.model,
                approval_mode=self.approval_mode,
                sandbox=self.sandbox,
            )
            return self._result(thread, result)

    def resume_thread(self, thread_id: str, project_root: Path) -> dict[str, Any]:
        with self.lock:
            # service_name is accepted by thread_start, but not by thread_resume.
            options = self._thread_options(project_root)
            options.pop("service_name", None)
            thread = self._ensure().thread_resume(thread_id, **options)
            self.active_threads[thread_id] = thread
            return {"thread": {"id": thread.id}}

    def start_turn(self, thread_id: str, prompt: str) -> dict[str, Any]:
        with self.lock:
            thread = self.active_threads.get(thread_id)
            if thread is None:
                thread = self._ensure().thread_resume(thread_id)
                self.active_threads[thread_id] = thread
            result = thread.run(
                prompt,
                model=self.model,
                approval_mode=self.approval_mode,
                sandbox=self.sandbox,
            )
            return self._result(thread, result)
