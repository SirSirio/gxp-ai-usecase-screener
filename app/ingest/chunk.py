"""Split sections into retrievable chunks without crossing section boundaries.

A chunk never mixes two sections, so its id always names exactly one citable section.
Long sections are split on sentence boundaries with one sentence of overlap.
"""
from __future__ import annotations

import re

from app.ingest.parse import Section
from app.ingest.sources import Source
from app.models import Chunk

MAX_CHARS = 1100
SENTENCE_END = re.compile(r"(?<=[.;:])\s+(?=[A-Z(\"“•●\d])")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_END.split(text) if s.strip()]


def pack(sentences: list[str], max_chars: int = MAX_CHARS) -> list[str]:
    """Greedy packing of sentences into windows of at most max_chars, with 1-sentence overlap."""
    windows: list[str] = []
    cur: list[str] = []
    for sent in sentences:
        if cur and len(" ".join(cur + [sent])) > max_chars:
            windows.append(" ".join(cur))
            cur = [cur[-1]] if len(cur[-1]) < max_chars // 3 else []
        cur.append(sent)
    if cur:
        windows.append(" ".join(cur))
    return windows


def chunk_sections(src: Source, sections: list[Section]) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen: dict[str, int] = {}
    for sec in sections:
        text = sec.text
        if not text:
            continue  # heading-only sections ("2. Principles") are reachable via their children
        sec_id = sec.section
        if sec_id in seen:  # defensive: never produce duplicate ids
            seen[sec_id] += 1
            sec_id = f"{sec_id}~{seen[sec_id]}"
        else:
            seen[sec_id] = 0
        windows = [text] if len(text) <= MAX_CHARS else pack(split_sentences(text))
        for n, window in enumerate(windows):
            chunks.append(
                Chunk(
                    id=f"{src.doc_id}:{sec_id}:{n}",
                    doc_id=src.doc_id,
                    doc_title=src.title,
                    doc_short=src.short,
                    doc_status=src.status,
                    url=src.url,
                    section=sec_id,
                    section_title=sec.title,
                    parent_title=sec.parent_title,
                    page_start=sec.page_start,
                    page_end=sec.page_end,
                    n=n,
                    text=window,
                )
            )
    return chunks
