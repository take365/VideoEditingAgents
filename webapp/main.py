from __future__ import annotations

import mimetypes
import json
import csv
import shutil
import secrets
import sys
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import httpx

from .codex_adapter_v2 import CodexAppServer
from .config import ROOT, settings
from .db import Database
from .jobs import JobManager, now
from .projects import create_project as create_project_files, seed_demo_project
from .security import project_path, safe_project_id, safe_relative_path


app = FastAPI(title="VideoEditingAgents Local")
basic = HTTPBasic()
db = Database(settings.database_path)
jobs = JobManager(db, settings.data_root, ROOT)
codex = CodexAppServer(settings.codex_command, settings.codex_cwd, settings.codex_approval_policy, settings.codex_sandbox, settings.codex_model)


def auth(credentials: HTTPBasicCredentials = Depends(basic)) -> str:
    if not (secrets.compare_digest(credentials.username, settings.username) and secrets.compare_digest(credentials.password, settings.password)):
        raise HTTPException(401, "認証が必要です", headers={"WWW-Authenticate": "Basic"})
    return credentials.username


class ProjectInput(BaseModel):
    name: str


class MessageInput(BaseModel):
    content: str


class CodexInput(BaseModel):
    prompt: str


class CodexTurnInput(BaseModel):
    thread_id: str
    prompt: str


class SubtitleSizeInput(BaseModel):
    size: int | None = None


class VideoOrientationInput(BaseModel):
    orientation: str


@app.on_event("startup")
def startup() -> None:
    settings.data_root.mkdir(parents=True, exist_ok=True)
    db.init()
    db.execute("DELETE FROM artifacts WHERE id NOT IN (SELECT MAX(id) FROM artifacts GROUP BY project_id, path)")
    jobs.recover()
    if not db.one("SELECT id FROM projects LIMIT 1"):
        project_id = "project-demo"
        project = seed_demo_project(settings.data_root, project_id, ROOT / "templates", ROOT / "samples" / "zundamon_intro")
        timestamp = now()
        db.execute("INSERT INTO projects(id,name,path,created_at,updated_at) VALUES(?,?,?,?,?)", (project_id, "サンプル：2枚画像から動画生成", str(project), timestamp, timestamp))
        db.execute("INSERT INTO messages(project_id,role,content,created_at) VALUES(?,?,?,?)", (project_id, "assistant", "サンプル案件を用意しました。画像2枚とシナリオをダウンロードできます。動画を生成すると、台本から音声を作成して動画まで一度に処理します。", timestamp))


@app.on_event("shutdown")
def shutdown() -> None:
    codex.close()


@app.get("/", response_class=HTMLResponse)
def index(_: str = Depends(auth)) -> str:
    return (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/static/{filename}")
def static_file(filename: str, _: str = Depends(auth)) -> FileResponse:
    path = safe_relative_path(ROOT / "webapp" / "static", filename)
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0])


@app.get("/api/projects")
def list_projects(_: str = Depends(auth)) -> list[dict]:
    return db.execute("SELECT * FROM projects ORDER BY updated_at DESC")


@app.post("/api/projects")
def create_project(payload: ProjectInput, _: str = Depends(auth)) -> dict:
    name = payload.name.strip()
    if not name or len(name) > 120:
        raise HTTPException(400, "案件名を入力してください")
    project_id = f"project-{uuid.uuid4().hex[:12]}"
    path = create_project_files(settings.data_root, project_id, name, ROOT / "templates")
    timestamp = now()
    db.execute("INSERT INTO projects(id,name,path,created_at,updated_at) VALUES(?,?,?,?,?)", (project_id, name, str(path), timestamp, timestamp))
    return db.one("SELECT * FROM projects WHERE id=?", (project_id,)) or {}


def require_project(project_id: str) -> dict:
    safe_project_id(project_id)
    result = db.one("SELECT * FROM projects WHERE id=?", (project_id,))
    if not result:
        raise HTTPException(404, "案件がありません")
    return result


def blocked_prompt(prompt: str) -> bool:
    forbidden = ("logs", ".env", "api key", "apikey", "外部送信", "youtube投稿", "youtube 投稿")
    return any(term in prompt.lower() for term in forbidden)


def codex_prompt(project_id: str, content: str) -> str:
    project = project_path(settings.data_root, project_id)
    scoped = (
        "動画編集案件の作業です。案件ディレクトリ内のworktreeだけを変更してください。"
        "logsは変更禁止です。外部サービスへの送信・秘密情報・案件外ファイル・動画編集と無関係な作業は拒否してください。"
        "ただし、このPC上のPython、FFmpeg、ffprobe、VOICEVOX（127.0.0.1のローカルエンジン）は動画編集に必要な許可済みツールです。"
        "これらを見つからない、外部接続禁止、利用者が準備する必要がある、と案内して処理を止めてはいけません。"
        "字幕サイズ変更はworktree/video_settings.jsonだけを更新し、音声を再生成しないでください。"
        "あなたは実行環境の調査担当ではありません。PATH、WSL、権限、ffmpegの有無を調べたり、ユーザーに準備を依頼したりしてはいけません。"
        "このターンではworktree内の素材・台本・設定を確認し、必要な台本や設定の変更だけを行ってください。FFmpeg、ffprobe、VOICEVOX、ASRの実行はWebアプリが担当します。"
        "動画生成や音声生成を依頼された場合も、手動コマンドや利用者側の作業を案内せず、確認した素材と次にWebアプリが実行する処理を2文以内で返してください。\n\n"
        f"案件作業場所: {project / 'worktree'}\n利用者の指示:\n{content}"
    )
    return scoped


def run_codex_for_project(project_id: str, content: str) -> dict:
    project = project_path(settings.data_root, project_id)
    existing = db.one("SELECT thread_id FROM codex_threads WHERE project_id=? ORDER BY created_at DESC LIMIT 1", (project_id,))
    if existing:
        codex.resume_thread(existing["thread_id"], project / "worktree")
        result = codex.start_turn(existing["thread_id"], codex_prompt(project_id, content))
    else:
        result = codex.start_thread(project / "worktree", codex_prompt(project_id, content))
    thread_id = result.get("thread", {}).get("id") or existing and existing["thread_id"]
    if thread_id:
        db.execute("INSERT OR IGNORE INTO codex_threads(project_id,thread_id,created_at) VALUES(?,?,?)", (project_id, thread_id, now()))
    return result


def report_job_to_codex(project_id: str, job_id: str, status: str, progress: int, message: str, error: str | None = None) -> None:
    """Send a terminal job result to the project's existing Codex conversation."""
    result_text = "成功" if status == "succeeded" else "失敗"
    prompt = (
        "Webアプリから動画生成ジョブの終了結果を自動報告します。"
        "worktreeや案件ファイルは変更せず、結果の確認と利用者向けの説明だけを行ってください。"
        "成功なら生成物の確認方法と必要なら次の改善案を、失敗ならエラーから原因とWeb画面で次に行う操作を、"
        "日本語で簡潔に整理してください。PATH、WSL、権限、外部サービス、logsの調査や利用者への環境準備依頼は不要です。\n\n"
        f"ジョブID: {job_id}\n結果: {result_text}\n進捗: {progress}%\n状態: {message}\n"
        f"エラー詳細: {error or 'なし'}"
    )
    result = run_codex_for_project(project_id, prompt)
    reply = result.get("text", "Codexから終了結果への応答がありませんでした。")
    db.execute(
        "INSERT INTO messages(project_id,role,content,created_at) VALUES(?,?,?,?)",
        (project_id, "assistant", f"Codexによる生成結果の確認:\n{reply}", now()),
    )


jobs.set_completion_handler(report_job_to_codex)


def find_audio_for_prompt(project: Path, content: str) -> Path | None:
    candidates = sorted((project / "audio").glob("*"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in candidates:
        if path.is_file() and (path.name in content or path.stem in content):
            return path
    return next((path for path in candidates if path.is_file() and path.suffix.lower() in {".wav", ".mp3", ".m4a", ".mp4", ".webm"}), None)


def is_video_request(content: str) -> bool:
    explicit_video = "動画" in content and any(term in content for term in ("生成", "作って", "つくって", "作成", "制作", "出力"))
    contextual_run = "実行" in content and ("音声生成" in content or "音声を生成" in content)
    return explicit_video or contextual_run


def script_needs_audio(project: Path) -> bool:
    tsv = project / "narration_segments.tsv"
    if not tsv.exists():
        return False
    try:
        with tsv.open(encoding="utf-8", newline="") as handle:
            scene_ids = [row[0].strip() for row in csv.reader(handle, delimiter="\t") if len(row) >= 2 and row[0].strip()]
    except (OSError, UnicodeError):
        return False
    audio_dir = project / "audio"
    return bool(scene_ids) and any(not any((audio_dir / f"scene_{scene_id}{suffix}").exists() for suffix in (".wav", ".mp3", ".m4a")) for scene_id in scene_ids)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str, _: str = Depends(auth)) -> dict:
    return require_project(project_id)


@app.get("/api/projects/{project_id}/messages")
def messages(project_id: str, _: str = Depends(auth)) -> list[dict]:
    require_project(project_id)
    return db.execute("SELECT * FROM messages WHERE project_id=? ORDER BY id", (project_id,))


@app.post("/api/projects/{project_id}/messages")
def add_message(project_id: str, payload: MessageInput, _: str = Depends(auth)) -> dict:
    require_project(project_id)
    content = payload.content.strip()
    if not content or len(content) > 10000:
        raise HTTPException(400, "メッセージが空か長すぎます")
    if blocked_prompt(content):
        raise HTTPException(400, "案件外、秘密情報、ログ、外部送信に関わる操作は許可していません")
    db.execute("INSERT INTO messages(project_id,role,content,created_at) VALUES(?,?,?,?)", (project_id, "user", content, now()))
    project = project_path(settings.data_root, project_id)
    transcription = None
    if "文字起こし" in content:
        source = find_audio_for_prompt(project, content)
        if source:
            transcription = transcribe(project_id, str(source.relative_to(project)).replace("\\", "/"), True, _)
    try:
        result = run_codex_for_project(project_id, content)
    except Exception as exc:
        raise HTTPException(503, f"Codexへの接続に失敗しました: {exc}") from exc
    reply = result.get("text", "Codexから応答がありませんでした。")
    if transcription is not None:
        reply += f"\n\n音声の文字起こしを完了しました（{transcription['model']}）。結果をworktree/uploadsに保存し、台本化へ渡しました。"
        if "音声を生成" not in content and is_video_request(content):
            content_for_pipeline = f"{content} 音声を生成"
        else:
            content_for_pipeline = content
    else:
        content_for_pipeline = content
    voicevox_required = "VOICEVOX" in content_for_pipeline.upper() or "音声を生成" in content_for_pipeline or (is_video_request(content_for_pipeline) and script_needs_audio(project))
    voicevox_ok = True
    if voicevox_required:
        reply += "\n\n音声生成の指示を受け、音声生成処理を開始します。"
        try:
            synthesize_voicevox(project_id, _)
        except HTTPException as exc:
            voicevox_ok = False
            reply += f"\n音声生成は開始できませんでした: {exc.detail}"
    if is_video_request(content_for_pipeline) and voicevox_ok:
        job_id = jobs.start_render(project_id)
        reply += f"\n\n動画生成を受け付けました。ジョブID: {job_id}"
    elif is_video_request(content_for_pipeline):
        reply += "\n動画生成は、音声生成に失敗したため開始していません。"
    db.execute("INSERT INTO messages(project_id,role,content,created_at) VALUES(?,?,?,?)", (project_id, "assistant", reply, now()))
    return {"reply": reply}


@app.post("/api/projects/{project_id}/uploads")
async def upload(project_id: str, file: UploadFile = File(...), _: str = Depends(auth)) -> dict:
    project = project_path(settings.data_root, require_project(project_id)["id"])
    original = Path(file.filename or "upload.bin").name
    suffix = Path(original).suffix.lower()
    allowed = {".txt", ".tsv", ".csv", ".wav", ".mp3", ".m4a", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}
    if suffix not in allowed:
        raise HTTPException(400, "対応していないファイル形式です")
    if suffix == ".tsv" and original.lower() == "narration_segments.tsv":
        target_dir = project
    elif suffix in {".wav", ".mp3", ".m4a"}:
        target_dir = project / "audio"
    elif suffix in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}:
        target_dir = project / "images"
    else:
        target_dir = project / "uploads"
    data = await file.read()
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(413, "ファイルが大きすぎます")
    target = target_dir / original
    if target.exists():
        target = target_dir / f"{uuid.uuid4().hex[:12]}_{original}"
    target.write_bytes(data)
    relative_dir = target_dir.relative_to(project)
    worktree_target_dir = project / "worktree" / relative_dir
    worktree_target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, worktree_target_dir / target.name)
    return {"name": original, "path": str(target.relative_to(project)), "size": len(data)}


@app.get("/api/projects/{project_id}/files")
def files(project_id: str, _: str = Depends(auth)) -> list[dict]:
    project = project_path(settings.data_root, require_project(project_id)["id"])
    result = []
    for path in project.rglob("*"):
        if path.is_file() and "logs" not in path.parts and path.name not in {"AGENTS.md", "project.json"}:
            result.append({"path": str(path.relative_to(project)), "size": path.stat().st_size})
    return sorted(result, key=lambda item: item["path"])


@app.get("/api/projects/{project_id}/settings")
def project_settings(project_id: str, _: str = Depends(auth)) -> dict:
    project = project_path(settings.data_root, require_project(project_id)["id"])
    config_path = project / "worktree" / "video_settings.json"
    config: dict = {}
    if config_path.exists():
        try:
            value = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                config = value
        except (OSError, json.JSONDecodeError):
            config = {}
    tsv = project / "narration_segments.tsv"
    rows = 0
    if tsv.exists():
        rows = sum(1 for line in tsv.read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "subtitle_font_size": config.get("subtitle_font_size", 42),
        "orientation": config.get("orientation", "landscape"),
        "narration_segments": rows,
        "images": sum(1 for path in (project / "images").iterdir() if path.is_file()),
        "audio": sum(1 for path in (project / "audio").iterdir() if path.is_file()),
        "voicevox_url": settings.voicevox_url,
        "voicevox_speaker": settings.voicevox_speaker,
        "voicevox_speed": settings.voicevox_speed,
    }


@app.post("/api/projects/{project_id}/render")
def render(project_id: str, _: str = Depends(auth)) -> dict:
    require_project(project_id)
    return {"job_id": jobs.start_render(project_id)}


@app.post("/api/projects/{project_id}/subtitle-size")
def update_subtitle_size(project_id: str, payload: SubtitleSizeInput, _: str = Depends(auth)) -> dict:
    project = project_path(settings.data_root, require_project(project_id)["id"])
    config_path = project / "worktree" / "video_settings.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        config = {}
    try:
        current = int(config.get("subtitle_font_size", 42))
    except (TypeError, ValueError):
        current = 42
    size = payload.size if payload.size is not None else current + 12
    size = max(24, min(size, 96))
    config["subtitle_font_size"] = size
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    db.execute("INSERT INTO messages(project_id,role,content,created_at) VALUES(?,?,?,?)", (project_id, "assistant", f"字幕サイズを{size}pxに変更しました。音声は再生成せず、動画を再生成すると反映されます。", now()))
    return {"subtitle_font_size": size, "message": "字幕サイズを変更しました。動画を再生成してください。"}


@app.post("/api/projects/{project_id}/orientation")
def update_orientation(project_id: str, payload: VideoOrientationInput, _: str = Depends(auth)) -> dict:
    project = project_path(settings.data_root, require_project(project_id)["id"])
    orientation = payload.orientation.strip().lower()
    if orientation not in {"landscape", "portrait"}:
        raise HTTPException(400, "画面向きは landscape または portrait を指定してください")
    config_path = project / "worktree" / "video_settings.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        config = {}
    config["orientation"] = orientation
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    label = "縦型ショート（1080×1920）" if orientation == "portrait" else "横型標準（1920×1080）"
    db.execute("INSERT INTO messages(project_id,role,content,created_at) VALUES(?,?,?,?)", (project_id, "assistant", f"動画の向きを{label}に変更しました。動画を再生成すると反映されます。", now()))
    return {"orientation": orientation, "message": f"動画の向きを{label}に変更しました。"}


@app.post("/api/projects/{project_id}/voicevox")
def synthesize_voicevox(project_id: str, _: str = Depends(auth)) -> dict:
    project = project_path(settings.data_root, require_project(project_id)["id"])
    script = ROOT / "scripts" / ("synthesize_sakura.py" if settings.sakura_ai_token else "synthesize_voicevox.py")
    try:
        import subprocess
        if settings.sakura_ai_token:
            command = [sys.executable, str(script), "--project", str(project), "--base-url", settings.sakura_ai_base_url, "--token", settings.sakura_ai_token, "--speaker", str(settings.sakura_tts_speaker), "--speed", str(settings.voicevox_speed)]
        else:
            command = [sys.executable, str(script), "--project", str(project), "--engine", settings.voicevox_url, "--speaker", str(settings.voicevox_speaker), "--speed", str(settings.voicevox_speed)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=True)
    except subprocess.CalledProcessError as exc:
        raise HTTPException(502, "VOICEVOX音声生成に失敗しました") from exc
    except FileNotFoundError as exc:
        raise HTTPException(503, "Python実行環境が見つかりません") from exc
    return {"ok": True, "output": result.stdout[-2000:]}


@app.post("/api/projects/{project_id}/transcribe/{relative:path}")
def transcribe(project_id: str, relative: str, timestamps: bool = False, _: str = Depends(auth)) -> dict:
    if not settings.openai_api_key and not settings.sakura_ai_token:
        raise HTTPException(503, "OPENAI_API_KEYが設定されていません")
    project = project_path(settings.data_root, require_project(project_id)["id"])
    source = safe_relative_path(project, relative)
    if not source.exists() or not source.is_file():
        raise HTTPException(404, "音声ファイルがありません")
    if source.suffix.lower() not in {".wav", ".mp3", ".m4a", ".mp4", ".webm"}:
        raise HTTPException(400, "音声または動画ファイルを指定してください")
    if source.stat().st_size > 25 * 1024 * 1024:
        raise HTTPException(413, "文字起こし用ファイルは25MB以下にしてください")
    model = settings.sakura_transcription_model if settings.sakura_ai_token else ("whisper-1" if timestamps else settings.openai_transcription_model)
    try:
        with source.open("rb") as audio:
            data = {"model": model, "response_format": "verbose_json" if timestamps else "json"}
            if timestamps:
                data["timestamp_granularities[]"] = "segment"
            base_url = settings.sakura_ai_base_url if settings.sakura_ai_token else "https://api.openai.com"
            token = settings.sakura_ai_token or settings.openai_api_key
            response = httpx.post(f"{base_url}/v1/audio/transcriptions", headers={"Authorization": f"Bearer {token}"}, data=data, files={"file": (source.name, audio, mimetypes.guess_type(source.name)[0] or "application/octet-stream")}, timeout=300)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip().replace("\n", " ")[:500]
        provider = "Sakura AI Engine" if settings.sakura_ai_token else "OpenAI"
        raise HTTPException(502, f"{provider}文字起こしに失敗しました ({exc.response.status_code}): {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "OpenAI文字起こしに失敗しました") from exc
    result = response.json()
    stem = source.stem
    (project / "uploads" / f"{stem}.transcription.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (project / "uploads" / f"{stem}.transcription.txt").write_text(result.get("text", ""), encoding="utf-8")
    worktree_uploads = project / "worktree" / "uploads"
    worktree_uploads.mkdir(exist_ok=True)
    shutil.copy2(project / "uploads" / f"{stem}.transcription.json", worktree_uploads / f"{stem}.transcription.json")
    shutil.copy2(project / "uploads" / f"{stem}.transcription.txt", worktree_uploads / f"{stem}.transcription.txt")
    return {"text": result.get("text", ""), "model": model, "segments": result.get("segments", []), "words": result.get("words", [])}


@app.get("/api/projects/{project_id}/jobs")
def project_jobs(project_id: str, _: str = Depends(auth)) -> list[dict]:
    require_project(project_id)
    return jobs.list_for_project(project_id)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, _: str = Depends(auth)) -> dict:
    result = jobs.get(job_id)
    if not result:
        raise HTTPException(404, "ジョブがありません")
    return result


@app.get("/api/jobs/{job_id}/events")
def job_events(job_id: str, _: str = Depends(auth)) -> StreamingResponse:
    if not jobs.get(job_id):
        raise HTTPException(404, "ジョブがありません")

    def stream():
        last = None
        while True:
            current = jobs.get(job_id)
            marker = (current.get("status"), current.get("progress"), current.get("message"), current.get("error"))
            if marker != last:
                yield f"data: {json.dumps(current, ensure_ascii=False)}\n\n"
                last = marker
            if current.get("status") in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, _: str = Depends(auth)) -> dict:
    if not jobs.get(job_id):
        raise HTTPException(404, "ジョブがありません")
    return jobs.cancel(job_id)


@app.get("/api/projects/{project_id}/artifacts")
def artifacts(project_id: str, _: str = Depends(auth)) -> list[dict]:
    require_project(project_id)
    return db.execute("SELECT * FROM artifacts WHERE project_id=? ORDER BY created_at DESC", (project_id,))


@app.get("/api/projects/{project_id}/download/{relative:path}")
def download(project_id: str, relative: str, _: str = Depends(auth)) -> FileResponse:
    project_path_value = project_path(settings.data_root, require_project(project_id)["id"])
    path = safe_relative_path(project_path_value, relative)
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "ファイルがありません")
    return FileResponse(path, filename=path.name)


@app.get("/api/codex/account")
def codex_account(_: str = Depends(auth)) -> dict:
    try:
        return codex.account()
    except Exception as exc:
        return {"connected": False, "error": str(exc)}


@app.post("/api/codex/login")
def codex_login(_: str = Depends(auth)) -> dict:
    try:
        return codex.login()
    except Exception as exc:
        raise HTTPException(503, str(exc))


@app.post("/api/projects/{project_id}/codex/thread")
def codex_thread(project_id: str, payload: CodexInput, _: str = Depends(auth)) -> dict:
    project = project_path(settings.data_root, require_project(project_id)["id"])
    prompt = payload.prompt.strip()
    if not prompt or len(prompt) > 10000:
        raise HTTPException(400, "指示を入力してください")
    forbidden = ("logs", ".env", "api key", "apikey", "外部送信", "youtube投稿", "youtube 投稿")
    if any(term in prompt.lower() for term in forbidden):
        raise HTTPException(400, "案件外、秘密情報、ログ、外部送信に関わる操作は許可していません")
    scoped = f"動画編集案件の作業です。案件ディレクトリ内だけを変更してください。logsは変更禁止です。外部接続・秘密情報・案件外ファイル・動画編集と無関係な作業は拒否してください。\n\n利用者の指示:\n{prompt}"
    try:
        result = codex.start_thread(project / "worktree", scoped)
        thread_id = result.get("thread", {}).get("id")
        if thread_id:
            db.execute("INSERT OR IGNORE INTO codex_threads(project_id,thread_id,created_at) VALUES(?,?,?)", (project_id, thread_id, now()))
        return result
    except Exception as exc:
        raise HTTPException(503, str(exc))


@app.get("/api/projects/{project_id}/codex/threads")
def codex_threads(project_id: str, _: str = Depends(auth)) -> list[dict]:
    require_project(project_id)
    return db.execute("SELECT thread_id, created_at FROM codex_threads WHERE project_id=? ORDER BY created_at DESC", (project_id,))


@app.post("/api/projects/{project_id}/codex/turn")
def codex_turn(project_id: str, payload: CodexTurnInput, _: str = Depends(auth)) -> dict:
    project = project_path(settings.data_root, require_project(project_id)["id"])
    if not db.one("SELECT id FROM codex_threads WHERE project_id=? AND thread_id=?", (project_id, payload.thread_id)):
        raise HTTPException(403, "この案件のCodexスレッドではありません")
    prompt = payload.prompt.strip()
    forbidden = ("logs", ".env", "api key", "apikey", "外部送信", "youtube投稿", "youtube 投稿")
    if not prompt or len(prompt) > 10000 or any(term in prompt.lower() for term in forbidden):
        raise HTTPException(400, "案件外、秘密情報、ログ、外部送信に関わる操作は許可していません")
    try:
        return codex.start_turn(payload.thread_id, f"動画編集案件の範囲内で続けてください。logsは変更禁止です。\n\n利用者の指示:\n{prompt}")
    except Exception as exc:
        raise HTTPException(503, str(exc))
