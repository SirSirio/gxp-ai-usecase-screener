# GxP AI Use-Case Assistant: container image for Azure Container Apps (decision D27, docs/DEPLOYMENT.md).
# Everything the app needs at run time is built into the image: the 9 public regulatory documents (downloaded and
# hash-checked), the search index and the embedding model. The container starts without any download.
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    WEB_CONCURRENCY=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts
# The 9 public source documents are part of the repo (W66): no downloads at build time (publisher sites block cloud
# runners, and the FDA warning letter is a web page whose layout changes). download_sources.py skips files that exist
# and only checks their SHA-256 hashes.
COPY data/raw ./data/raw

# Corpus and index at build time. A hash mismatch fails the build on purpose: the source map is pinned to one corpus
# version (app/source_map.py CORPUS_VERSION), so a changed publisher file must be re-reviewed before it is used.
RUN python scripts/download_sources.py \
 && python -m app.ingest.build_index \
 && python -c "from app.retrieval.index import get_index; from app.source_map import CORPUS_VERSION; v = get_index().corpus_version; assert v == CORPUS_VERSION, f'corpus {v} != {CORPUS_VERSION}'; print('corpus', v)"

COPY startup.sh .

# Run as a non-root user; the app writes its (demo-only) audit log and results under data/.
RUN useradd --create-home --uid 10001 appuser && mkdir -p data/audit data/results data/usage && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s --start-period=60s CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8000'))"
CMD ["bash", "startup.sh"]
