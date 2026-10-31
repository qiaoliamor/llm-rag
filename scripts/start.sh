#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if ! command -v uv >/dev/null 2>&1; then
  echo '请先安装 uv：https://docs.astral.sh/uv/getting-started/installation/'
  exit 1
fi
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo 'React 前端需要 Node.js 22.12+ 和 npm：https://nodejs.org/'
  exit 1
fi
node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (major < 22 || (major === 22 && minor < 12)) { console.error("需要 Node.js 22.12+"); process.exit(1); }'
if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
fi
if [ ! -f frontend/node_modules/.package-lock.json ] || [ frontend/package-lock.json -nt frontend/node_modules/.package-lock.json ]; then
  npm ci --prefix frontend
fi
npm run build --prefix frontend
echo '心语 · 本地地址 http://127.0.0.1:8000（Ctrl+C 停止）'
exec uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000
