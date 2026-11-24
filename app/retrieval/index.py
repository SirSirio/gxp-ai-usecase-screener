"""Hybrid retrieval over the chunked corpus.

Two retrievers, fused with reciprocal rank fusion (RRF):
- sparse: TF-IDF over words and word pairs. Strong on exact regulatory terms ("Annex 11", "audit trail").
- dense: bge-small embeddings in a FAISS inner-product index. Strong on paraphrase
  ("ChatGPT drafts our SOPs" finds "Generative AI and Large Language Models").
RRF only uses ranks, so the two very different score scales never have to be calibrated.
"""
from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import linear_kernel

from app.config import Settings, get_settings
from app.models import Chunk, ScoredChunk, SectionText

RRF_K = 60
CANDIDATES = 50
WORD = re.compile(r"[a-z][a-z\-]{2,}")
STOP = {
    "the", "and", "for", "that", "with", "this", "from", "are", "should", "which", "such", "where", "been",
    "into", "their", "than", "also", "any", "all", "can", "may", "not", "use", "used", "its", "our", "has",
    "have", "will", "would", "these", "those", "there", "when", "what", "how", "who", "whether", "being",
}


def content_words(text: str) -> set[str]:
    return {w.strip("-") for w in WORD.findall(text.lower()) if w not in STOP}


class KnowledgeIndex:
    def __init__(self, index_dir: Path, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.dir = index_dir
        self.manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        self.chunks: list[Chunk] = [
            Chunk.model_validate_json(line)
            for line in (index_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.by_id = {c.id: c for c in self.chunks}
        self.sections: list[dict] = json.loads((index_dir / "sections.json").read_text(encoding="utf-8"))
        with open(index_dir / "tfidf.pkl", "rb") as f:  # built locally by build_index, trusted
            self.vectorizer, self.tfidf = pickle.load(f)
        self.faiss = None
        self.embedder = None
        dense_path = index_dir / "dense.faiss"
        if self.manifest.get("embedding_model") and dense_path.exists():
            try:
                import faiss

                from app.retrieval.embedder import get_embedder

                self.faiss = faiss.read_index(str(dense_path))
                self.embedder = get_embedder(self.manifest["embedding_model"], str(self.settings.model_cache))
            except Exception as exc:  # degrade to sparse-only rather than fail
                print(f"[index] dense retrieval disabled: {exc}")

    @property
    def corpus_version(self) -> str:
        return self.manifest["corpus_version"]

    @property
    def doc_ids(self) -> list[str]:
        return sorted({c.doc_id for c in self.chunks})

    # ---------- retrieval ----------
    def _sparse_ranks(self, query: str, allowed: np.ndarray | None) -> list[int]:
        scores = linear_kernel(self.vectorizer.transform([query]), self.tfidf).ravel()
        if allowed is not None:
            scores = np.where(allowed, scores, -1)
        order = np.argsort(-scores)[:CANDIDATES]
        return [int(i) for i in order if scores[i] > 0]

    def _dense_ranks(self, query: str, allowed: np.ndarray | None) -> list[int]:
        if self.faiss is None or self.embedder is None:
            return []
        q = self.embedder.queries([query])
        _, idx = self.faiss.search(q, CANDIDATES * 2 if allowed is not None else CANDIDATES)
        out = [int(i) for i in idx[0] if i >= 0 and (allowed is None or allowed[i])]
        return out[:CANDIDATES]

    def search(self, query: str, k: int | None = None, docs: list[str] | None = None) -> list[ScoredChunk]:
        k = k or self.settings.top_k
        allowed = None
        if docs:
            allowed = np.array([c.doc_id in docs for c in self.chunks])
        sparse = self._sparse_ranks(query, allowed)
        dense = self._dense_ranks(query, allowed)
        fused: dict[int, float] = {}
        for rank, i in enumerate(sparse):
            fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, i in enumerate(dense):
            fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        sparse_rank = {i: r + 1 for r, i in enumerate(sparse)}
        dense_rank = {i: r + 1 for r, i in enumerate(dense)}
        best = sorted(fused, key=lambda i: -fused[i])[:k]
        return [
            ScoredChunk(chunk=self.chunks[i], score=round(fused[i], 5), rank_sparse=sparse_rank.get(i), rank_dense=dense_rank.get(i))
            for i in best
        ]

    # ---------- lookups (used by get_section, controls and the citation check) ----------
    def get_chunk(self, chunk_id: str) -> Chunk | None:
        return self.by_id.get(chunk_id)

    def section_chunks(self, doc_id: str, section: str) -> list[Chunk]:
        return [c for c in self.chunks if c.doc_id == doc_id and c.section == section]

    def section_parts(self, doc_id: str, section: str) -> list[dict]:
        """A section and its subsections, in document order (each: doc_id, section, title, text)."""
        return [s for s in self.sections if s["doc_id"] == doc_id and (s["section"] == section or s["section"].startswith(section + "."))]

    def get_section(self, doc_id: str, section: str, max_chars: int = 6000) -> SectionText | None:
        """Full text of a section including its subsections (e.g. "10" returns 10.1 to 10.5)."""
        parts = self.section_parts(doc_id, section)
        if not parts:
            return None
        head = parts[0]
        text = "\n\n".join(f"§{p['section']} {p['title']}: {p['text']}".strip() for p in parts if p["text"] or p["title"])
        ids = [c.id for c in self.chunks if c.doc_id == doc_id and (c.section == section or c.section.startswith(section + "."))]
        return SectionText(
            doc_id=doc_id,
            doc_short=self.chunks[[c.doc_id for c in self.chunks].index(doc_id)].doc_short,
            section=section,
            title=head["title"],
            text=text[:max_chars],
            chunk_ids=ids,
        )

    def similarity(self, text: str, chunk_ids: list[str]) -> dict[str, float]:
        """Dense cosine similarity between a claim and chunks (0 when dense retrieval is off)."""
        if self.embedder is None or not chunk_ids:
            return {cid: 0.0 for cid in chunk_ids}
        q = self.embedder.queries([text])[0]
        p = self.embedder.passages([self.by_id[c].embedding_text() for c in chunk_ids])
        return {cid: float(v) for cid, v in zip(chunk_ids, p @ q)}


_INDEX: KnowledgeIndex | None = None


def get_index() -> KnowledgeIndex:
    global _INDEX
    if _INDEX is None:
        s = get_settings()
        _INDEX = KnowledgeIndex(s.index_dir, s)
    return _INDEX
