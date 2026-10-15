#!/usr/bin/env bash
# ULI Platform - Linux/macOS setup.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== ULI Platform setup ==="
command -v python3 >/dev/null || { echo "Python 3.11+ required"; exit 1; }
command -v node >/dev/null || { echo "Node.js 18+ required"; exit 1; }

if [ ! -d .venv ]; then
  echo "[1/4] Creating virtual environment..."
  python3 -m venv .venv
else
  echo "[1/4] Reusing existing .venv"
fi

echo "[2/4] Installing Python dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "[3/4] Installing frontend dependencies..."
(cd frontend && [ -d node_modules ] || npm install --no-audit --no-fund)

echo "[4/4] Building frontend..."
(cd frontend && npm run build)

echo
echo "Setup complete. Start the platform with: scripts/run.sh"
