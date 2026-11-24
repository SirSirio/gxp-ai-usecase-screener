import pytest

from app.audit import AuditLog
from app.config import get_settings


@pytest.fixture(scope="session")
def index():
    s = get_settings()
    if not (s.index_dir / "manifest.json").exists():
        pytest.skip("index not built: run python -m app.ingest.build_index")
    from app.retrieval.index import get_index

    return get_index()


@pytest.fixture
def audit(tmp_path):
    return AuditLog(tmp_path / "audit.jsonl")


@pytest.fixture(scope="session")
def raw_dir():
    s = get_settings()
    if not (s.raw_dir / "annex22_draft_2025.pdf").exists():
        pytest.skip("source documents missing: run scripts/download_sources.py")
    return s.raw_dir
