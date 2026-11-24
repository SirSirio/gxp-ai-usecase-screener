"""Dense retrieval must not switch itself off silently.

KnowledgeIndex falls back to keyword-only search if the embedding model cannot load. That keeps
the app running, but it quietly lowers quality. This test makes the fallback visible.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_dense_retrieval_active(index):
    assert index.faiss is not None and index.embedder is not None, "dense retrieval disabled: check onnxruntime import"


def test_embeddings_load_even_if_pdf_library_loads_first():
    """The order that used to break on Windows: PyMuPDF first, then the embedding runtime."""
    code = "import app, pymupdf, onnxruntime; print('ok')"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert out.stdout.strip() == "ok", out.stderr[-500:]
