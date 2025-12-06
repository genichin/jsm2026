#!/usr/bin/env bash
set -euo pipefail

# Bring up local infra (PostgreSQL + Redis) via Docker Compose
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker is not installed or not in PATH" >&2
  exit 1
fi

cd "$BACKEND_DIR"

echo "[INFO] Starting Docker Compose (PostgreSQL, Redis)..."
docker compose up -d

echo "[INFO] Containers status:"
docker compose ps
