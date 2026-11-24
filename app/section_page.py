"""Human-readable view of one regulatory section (the /section page).

The index stores each section as one run of text (PDF line breaks are gone), so paragraphs are rebuilt
at sentence boundaries for readability only; the official PDF stays the reference. When the result page
passes the quoted passage, the sentences it covers are marked so the reader sees what was cited.
"""
from __future__ import annotations

import re

from app.ingest.sources import SOURCES_BY_ID
from app.pipeline import DRAFT_WARNING
from app.retrieval.index import KnowledgeIndex

SENTENCE = re.compile(r"(?<!i\.e\.)(?<!e\.g\.)(?<=[.;])\s+")  # same split as citations.best_quote
PARA_CHARS = 480  # soft paragraph length; a paragraph never breaks inside a sentence
QUOTE_MAX = 1000  # longer ?q= values are ignored
NUMBERED = re.compile(r"^[0-9IVX]+(\.[0-9A-Za-z]+)*$")  # "4.12", "IV.A.3": shown as §; "art-3", "glossary": not
EU_CONSULTATION_DRAFTS = {"A22", "A11D", "CH4D"}  # the documents DRAFT_WARNING names


def _clean_quote(quote: str | None) -> str:
    q = " ".join((quote or "").split()).strip("“”\"' ")
    return q.rstrip("…").strip() if len(q) <= QUOTE_MAX else ""


def _paragraphs(text: str, quote: str) -> tuple[list[list[dict]], bool]:
    """Split text into paragraphs of sentences; mark the sentences that overlap the quote."""
    start = text.find(quote) if quote else -1
    if start < 0 and len(quote) > 80:  # a quote cut mid-word still matches by its opening
        start = text.find(quote[:80])
    span = (start, start + len(quote)) if start >= 0 else None
    paras: list[list[dict]] = []
    current: list[dict] = []
    size, pos = 0, 0
    for sentence in (s for s in SENTENCE.split(text) if s.strip()):
        at = text.find(sentence, pos)
        pos = at + len(sentence) if at >= 0 else pos
        marked = bool(span and at >= 0 and at < span[1] and at + len(sentence) > span[0])
        if current and size + len(sentence) > PARA_CHARS:
            paras.append(current)
            current, size = [], 0
        current.append({"text": sentence, "marked": marked})
        size += len(sentence)
    if current:
        paras.append(current)
    return paras, span is not None


def _label(section: str) -> str:
    return f"§{section}" if NUMBERED.match(section) else ""


def _draft_notice(doc_id: str, status: str) -> str | None:
    if status != "draft":
        return None
    if doc_id in EU_CONSULTATION_DRAFTS:
        return f"Drafts are not yet in force. {DRAFT_WARNING}"
    return "Drafts are not yet in force. This is draft guidance; the final text may differ."


def section_view(index: KnowledgeIndex, doc_id: str, section: str, quote: str | None = None) -> dict | None:
    """Everything the section template needs, or None when the document or section does not exist."""
    source = SOURCES_BY_ID.get(doc_id)
    parts = index.section_parts(doc_id, section)
    if source is None or not parts:
        return None
    q = _clean_quote(quote)
    found = False
    blocks = []
    for i, p in enumerate(parts):
        paras, hit = _paragraphs(p["text"], q) if p["text"] else ([], False)
        if hit and found:  # mark the first occurrence only
            paras = [[{**s, "marked": False} for s in para] for para in paras]
        found = found or hit
        blocks.append({"section": p["section"], "label": _label(p["section"]), "title": p["title"],
                       "paragraphs": paras, "is_head": i == 0})
    chunks = [c for c in index.chunks if c.doc_id == doc_id and (c.section == section or c.section.startswith(section + "."))]
    pages = (min(c.page_start for c in chunks), max(c.page_end for c in chunks)) if chunks else None
    return {
        "source": source,
        "section": section,
        "label": _label(section),
        "title": parts[0]["title"],
        "head": blocks[0],
        "subsections": blocks[1:],
        "pages": pages,
        "draft_notice": _draft_notice(doc_id, source.status),
        "quote_given": bool(q),
        "quote_found": found,
    }
