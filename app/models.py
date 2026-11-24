"""Core data objects shared by ingestion, retrieval and the pipeline."""
from __future__ import annotations

from pydantic import BaseModel


class Chunk(BaseModel):
    """A retrievable passage. `id` = "<doc_id>:<section>:<n>", e.g. "A22:3.3:0"."""

    id: str
    doc_id: str
    doc_title: str
    doc_short: str
    doc_status: str
    url: str
    section: str
    section_title: str
    parent_title: str = ""
    page_start: int
    page_end: int
    n: int
    text: str

    @property
    def ref(self) -> str:
        """Human-readable reference, e.g. 'Annex 22 (draft) §3.3 Human-in-the-loop'."""
        numbered = self.section[:1].isdigit() or self.section.split(".")[0] in {"I", "II", "III", "IV", "V"}
        return f"{self.doc_short} §{self.section} {self.section_title}".strip() if numbered else f"{self.doc_short}: {self.section_title}"

    def embedding_text(self) -> str:
        """Text used for indexing: the heading path helps retrieval find the right section."""
        head = " — ".join(x for x in (self.doc_short, self.parent_title, self.section_title) if x)
        return f"{head}. {self.text}"


class SectionText(BaseModel):
    """A full section, returned by the get_section tool."""

    doc_id: str
    doc_short: str
    section: str
    title: str
    text: str
    chunk_ids: list[str]


class ScoredChunk(BaseModel):
    chunk: Chunk
    score: float
    rank_sparse: int | None = None
    rank_dense: int | None = None
