#!/usr/bin/env bash
set -euo pipefail

# Install deps if needed and start Next.js dev server
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

cd "$FRONTEND_DIR"

if [ ! -d node_modules ]; then
  echo "[INFO] node_modules not found. Installing dependencies..."
  npm install
fi

echo "[INFO] Starting Next.js dev server..."
exec npm run dev
