#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -e ".[dev]"

if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Update values if you want to index a different folder."
fi

echo "Setup complete."
