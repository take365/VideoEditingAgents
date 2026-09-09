from __future__ import annotations

import re
from pathlib import Path


SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
FORBIDDEN_PARTS = {"logs", ".git", ".env", "secrets", "credentials"}


def safe_project_id(value: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise ValueError("invalid project id")
    return value


def project_path(data_root: Path, project_id: str) -> Path:
    safe_project_id(project_id)
    root = data_root.resolve()
    candidate = (root / project_id).resolve()
    if candidate.parent != root:
        raise ValueError("project path escaped data root")
    return candidate


def safe_relative_path(project_root: Path, relative: str) -> Path:
    candidate = (project_root / relative).resolve()
    root = project_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path escaped project root")
    parts = {part.lower() for part in candidate.relative_to(root).parts}
    if parts & FORBIDDEN_PARTS:
        raise ValueError("path is outside the editable video workspace")
    if candidate.name.lower() in {"agents.md", "policy.md"}:
        raise ValueError("policy files are protected")
    return candidate
