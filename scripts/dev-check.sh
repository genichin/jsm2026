#!/usr/bin/env bash
set -euo pipefail

# Run frontend checks: type-check, lint, test
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

cd "$FRONTEND_DIR"

echo "[INFO] Type check..."
npm run type-check

echo "[INFO] Lint..."
npm run lint

echo "[INFO] Tests..."
npm test
