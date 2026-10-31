#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if ! command -v uv >/dev/null 2>&1; then
  echo '请先安装 uv：https://docs.astral.sh/uv/getting-started/installation/'
  exit 1
fi
if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
fi
echo '心语 · 本地地址 http://127.0.0.1:8000（Ctrl+C 停止）'
exec uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000
