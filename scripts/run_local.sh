#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Run scripts/setup.sh first."
  exit 1
fi

source .venv/bin/activate
python -c "from langchain_documents_mcp_server.config import get_settings; s = get_settings(); msg = f'Config validation passed. Transport: {s.mcp_transport}'; print(f'{msg}. Endpoint: {s.streamable_http_url}' if s.mcp_transport == 'streamable-http' else msg)"
python -m langchain_documents_mcp_server.main
