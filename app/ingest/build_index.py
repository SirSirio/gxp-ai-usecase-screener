"""Build the retrieval index: parse → chunk → TF-IDF + dense embeddings → data/index/.

Run: .venv/Scripts/python -m app.ingest.build_index

The corpus version is a hash of every chunk. It is written into every audit record and every
evaluation result, so any answer can be traced to the exact corpus it was produced from.
"""
from __future__ import annotations

import hashlib
import json
import pickle
from datetime import datetime, timezone

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.config import get_settings
from app.ingest.chunk import chunk_sections
from app.ingest.parse import parse_source
from app.ingest.sources import SOURCES


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def build(embeddings: str | None = None) -> dict:
    s = get_settings()
    embeddings = embeddings or s.embeddings
    s.index_dir.mkdir(parents=True, exist_ok=True)

    chunks, sections, files, missing = [], [], {}, []
    for src in SOURCES:
        path = s.raw_dir / src.filename
        if not path.exists():
            missing.append(src.doc_id)
            print(f"[build] MISSING {src.doc_id}: {path.name} (run scripts/download_sources.py)")
            continue
        secs = parse_source(src, s.raw_dir)
        doc_chunks = chunk_sections(src, secs)
        chunks.extend(doc_chunks)
        sections.extend({"doc_id": src.doc_id, "section": x.section, "title": x.title, "text": x.text} for x in secs)
        files[src.doc_id] = {"file": src.filename, "sha256": sha256_file(path)}
        print(f"[build] {src.doc_id:9s} {len(secs):4d} sections {len(doc_chunks):4d} chunks")

    corpus_hash = hashlib.sha256("".join(c.id + c.text for c in chunks).encode()).hexdigest()[:12]

    (s.index_dir / "chunks.jsonl").write_text("\n".join(c.model_dump_json() for c in chunks) + "\n", encoding="utf-8")
    (s.index_dir / "sections.json").write_text(json.dumps(sections, ensure_ascii=False, indent=0), encoding="utf-8")

    texts = [c.embedding_text() for c in chunks]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english", min_df=1)
    tfidf = vectorizer.fit_transform(texts)
    with open(s.index_dir / "tfidf.pkl", "wb") as f:
        pickle.dump((vectorizer, tfidf), f)

    embedding_model = None
    dense = s.index_dir / "dense.faiss"
    if embeddings == "fastembed":
        import faiss

        from app.retrieval.embedder import get_embedder

        emb = get_embedder(s.embedding_model, str(s.model_cache))
        vecs = emb.passages(texts)
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs.astype(np.float32))
        faiss.write_index(index, str(dense))
        embedding_model = s.embedding_model
        print(f"[build] dense: {vecs.shape[0]} x {vecs.shape[1]} ({embedding_model})")
    elif dense.exists():
        dense.unlink()

    manifest = {
        "corpus_version": corpus_hash,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_chunks": len(chunks),
        "n_sections": len(sections),
        "embedding_model": embedding_model,
        "sources": files,
        "missing": missing,
    }
    (s.index_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[build] corpus_version={corpus_hash} chunks={len(chunks)}")
    return manifest


if __name__ == "__main__":
    build()
