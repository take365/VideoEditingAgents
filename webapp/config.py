from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("APP_HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", os.getenv("APP_PORT", "8787")))
    username: str = os.getenv("APP_USERNAME", "admin")
    password: str = os.getenv("APP_PASSWORD", "change-me")
    data_root: Path = Path(os.getenv("DATA_ROOT", str(ROOT / "workspaces"))).resolve()
    database_path: Path = Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "video_agents.sqlite3"))).resolve()
    voicevox_url: str = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021").rstrip("/")
    voicevox_speaker: int = int(os.getenv("VOICEVOX_SPEAKER", "3"))
    voicevox_speed: float = float(os.getenv("VOICEVOX_SPEED", "1.05"))
    sakura_ai_token: str = os.getenv("SAKURA_AI_TOKEN", "")
    sakura_ai_base_url: str = os.getenv("SAKURA_AI_BASE_URL", "https://api.ai.sakura.ad.jp").rstrip("/")
    sakura_tts_speaker: int = int(os.getenv("SAKURA_TTS_SPEAKER", "3"))
    sakura_tts_model: str = os.getenv("SAKURA_TTS_MODEL", "")
    sakura_transcription_model: str = os.getenv("SAKURA_TRANSCRIPTION_MODEL", "whisper-large-v3-turbo")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_transcription_model: str = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-transcribe")
    codex_command: str = os.getenv("CODEX_COMMAND", "codex")
    codex_cwd: str = os.getenv("CODEX_CWD", "")
    codex_approval_policy: str = os.getenv("CODEX_APPROVAL_POLICY", "on-request")
    codex_sandbox: str = os.getenv("CODEX_SANDBOX", "workspace-write")
    codex_model: str = os.getenv("CODEX_MODEL", "gpt-5.6-luna")


settings = Settings()
