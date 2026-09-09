from __future__ import annotations

import json
import shlex
import subprocess
import threading
from pathlib import Path
from typing import Any

from .codex_policy import command_allowed, file_change_allowed


class CodexAppServer:
    """Local-only JSON-RPC adapter; the app-server is never exposed to HTTP."""

    def __init__(self, command: str, cwd: str, approval_policy: str, sandbox: str):
        self.command = command
        self.cwd = cwd or None
        self.approval_policy = approval_policy
        self.sandbox = sandbox
        self.process: subprocess.Popen[str] | None = None
        self.counter = 0
        self.lock = threading.Lock()
        self.thread_roots: dict[str, Path] = {}

    def _ensure(self) -> None:
        if self.process and self.process.poll() is None:
            return
        args = shlex.split(self.command) + ["app-server", "--listen", "stdio://"]
        self.process = subprocess.Popen(args, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self._send("initialize", {"clientInfo": {"name": "video_editing_agents", "title": "VideoEditingAgents local web", "version": "0.1.0"}})
        self._notify("initialized", {})

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.process = None

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise RuntimeError("Codex App Server is not running")
        self.process.stdin.write(json.dumps({"method": method, "params": params}, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def _send(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("Codex App Server is not running")
        self.counter += 1
        request_id = self.counter
        self.process.stdin.write(json.dumps({"method": method, "id": request_id, "params": params}, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Codex App Server terminated")
            message = json.loads(line)
            if message.get("method", "").startswith("item/") and message.get("id") is not None:
                self._handle_server_request(message)
                continue
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(message["error"].get("message", "Codex App Server error"))
                return message.get("result", {})

    def _handle_server_request(self, message: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            return
        method = message.get("method", "")
        params = message.get("params", {}) or {}
        thread_id = params.get("threadId")
        root = self.thread_roots.get(thread_id, Path.cwd())
        if method == "item/commandExecution/requestApproval":
            allowed, reason = command_allowed(str(params.get("command", "")), params.get("cwd"), root)
            result = {"decision": "accept" if allowed else "decline"}
            if not allowed:
                result["reason"] = reason
        elif method == "item/fileChange/requestApproval":
            allowed, reason = file_change_allowed(params, root)
            result = {"decision": "accept" if allowed else "decline"}
            if not allowed:
                result["reason"] = reason
        else:
            return
        self.process.stdin.write(json.dumps({"id": message.get("id"), "result": result}, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def account(self) -> dict[str, Any]:
        with self.lock:
            self._ensure()
            return self._send("account/read", {})

    def login(self) -> dict[str, Any]:
        with self.lock:
            self._ensure()
            return self._send("account/login/start", {"type": "chatgpt", "useHostedLoginSuccessPage": True, "appBrand": "codex"})

    def start_thread(self, project_root: Path, prompt: str) -> dict[str, Any]:
        with self.lock:
            self._ensure()
            result = self._send("thread/start", {"cwd": str(project_root), "approvalPolicy": self.approval_policy, "sandbox": self.sandbox, "serviceName": "video_editing_agents", "input": [{"type": "text", "text": prompt}]})
            thread_id = result.get("thread", {}).get("id")
            if thread_id:
                self.thread_roots[thread_id] = project_root.resolve()
            return result

    def start_turn(self, thread_id: str, prompt: str) -> dict[str, Any]:
        with self.lock:
            self._ensure()
            return self._send("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": prompt}]})
