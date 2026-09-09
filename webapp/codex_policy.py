from __future__ import annotations

import re
from pathlib import Path


NETWORK_COMMANDS = re.compile(r"\b(curl|wget|ssh|scp|sftp|ftp|nc|netcat|telnet|nslookup|dig|git\s+(clone|fetch|pull|push)|Invoke-WebRequest|Start-BitsTransfer)\b", re.I)
SECRET_TERMS = re.compile(r"(^|[\\/ .])((\.env)|(credentials?)|(secrets?))(($|[\\/ .]))", re.I)
LOG_TERMS = re.compile(r"(^|[\\/ .])logs?([\\/ .]|$)", re.I)
ESCAPE_TERMS = re.compile(r"(^|[\s'\"])(\.\.(?:[\\/]|$)|~(?:[\\/]|$)|\$(?:HOME|USERPROFILE|APPDATA)\b|%USERPROFILE%|/proc(?:/|$)|/sys(?:/|$))", re.I)


def _inside(root: Path, value: Path) -> bool:
    root, value = root.resolve(), value.resolve()
    return value == root or root in value.parents


def command_allowed(command: str, cwd: str | None, worktree: Path) -> tuple[bool, str]:
    if not command.strip():
        return False, "コマンド内容を確認できない操作は許可していません"
    if NETWORK_COMMANDS.search(command):
        return False, "外部接続を伴うコマンドは許可していません"
    if SECRET_TERMS.search(command) or LOG_TERMS.search(command):
        return False, "秘密情報またはlogsへの操作は許可していません"
    if ESCAPE_TERMS.search(command):
        return False, "案件専用worktree外へ抜けるパス指定は許可していません"
    if cwd and not _inside(worktree, Path(cwd)):
        return False, "案件専用worktree外のコマンドは許可していません"
    absolute_paths = re.findall(r"(?:^|\s)(/[A-Za-z0-9_.-][^\s'\"]*)", command)
    if any(not _inside(worktree, Path(path)) for path in absolute_paths):
        return False, "案件専用worktree外のパスは許可していません"
    return True, ""


def file_change_allowed(payload: dict, worktree: Path) -> tuple[bool, str]:
    raw = str(payload)
    if SECRET_TERMS.search(raw) or LOG_TERMS.search(raw):
        return False, "秘密情報またはlogsの変更は許可していません"
    paths: list[str] = []
    changes = payload.get("changes", []) if isinstance(payload, dict) else []
    for change in changes:
        if isinstance(change, dict):
            for key in ("path", "file", "filename"):
                if change.get(key):
                    paths.append(str(change[key]))
        elif isinstance(change, str):
            paths.append(change)
    for value in paths:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = worktree / candidate
        if not _inside(worktree, candidate):
            return False, "案件専用worktree外のファイル変更は許可していません"
    if not paths:
        return False, "変更対象を確認できないファイル操作は許可していません"
    return True, ""
