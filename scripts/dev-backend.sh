#!/usr/bin/env bash
set -euo pipefail

# Run Alembic migrations, init DB, and start FastAPI (reload) for local dev
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
VENV="$BACKEND_DIR/.venv"

cd "$BACKEND_DIR"

if [ ! -d "$VENV" ]; then
  echo "[ERROR] .venv not found in $BACKEND_DIR. Create it with: python3.13 -m venv .venv" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

alembic upgrade head

python scripts/init_db.py

echo "[INFO] Starting FastAPI with uvicorn (reload)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
