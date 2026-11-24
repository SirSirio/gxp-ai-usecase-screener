#!/usr/bin/env bash
# Azure App Service (Linux) startup command:  bash startup.sh
# Builds the corpus on first start (public documents only), then serves the app.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f data/index/manifest.json ]; then
  echo "[startup] downloading sources and building index (first start, ~3 min)"
  python scripts/download_sources.py || echo "[startup] WARNING: hash check failed; see log"
  python -m app.ingest.build_index
fi

exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WEB_CONCURRENCY:-1}" \
  --bind "0.0.0.0:${PORT:-8000}" \
  --timeout 180
