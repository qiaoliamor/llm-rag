#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
uv run --frozen python scripts/configure_memory_db.py
docker compose up -d --wait db
echo 'PostgreSQL + pgvector 已就绪，运行 ./scripts/start.sh 启动网页。'
