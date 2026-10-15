#!/usr/bin/env bash
# ULI Platform - Linux/macOS launcher.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
  echo "[ERROR] Virtual environment missing. Run scripts/setup.sh first."
  exit 1
fi

export ULI_CORE_HOST="${ULI_CORE_HOST:-127.0.0.1}"
export ULI_CORE_PORT="${ULI_CORE_PORT:-8787}"
export ULI_CORE_URL="http://127.0.0.1:${ULI_CORE_PORT}"
export ULI_ENV="${ULI_ENV:-production}"

echo "Starting ULI Core on ${ULI_CORE_URL}"
echo "UI:  ${ULI_CORE_URL}/ui/"
echo "API: ${ULI_CORE_URL}/docs"
exec .venv/bin/python scripts/run.py --seed --seed-static "$@"
