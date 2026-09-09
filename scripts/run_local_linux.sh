#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -r requirements-web.txt
if [[ ! -f .env ]]; then cp .env.example .env; echo ".env を作成しました。APP_PASSWORD を設定して再実行してください。"; exit 0; fi
exec uvicorn webapp.main:app --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8787}"
