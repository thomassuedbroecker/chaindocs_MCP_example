#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing .venv. Run scripts/setup.sh first."
  exit 1
fi

VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

"$VENV_PYTHON" -m coverage erase
"$VENV_PYTHON" -m coverage run -m pytest -q
"$VENV_PYTHON" -m coverage report -m
"$VENV_PYTHON" -m coverage xml -o coverage.xml
"$VENV_PYTHON" -m coverage html -d htmlcov
