"""Explore the knowledge base from the command line (a learning aid).

  .venv\\Scripts\\python scripts\\explore.py raw A22 3          raw PDF text of page 3, as the computer sees it
  .venv\\Scripts\\python scripts\\explore.py sections A22       all sections the parser found in a document
  .venv\\Scripts\\python scripts\\explore.py section A22 3.3    one section, cleaned
  .venv\\Scripts\\python scripts\\explore.py chunks A22 1       the chunks (pieces) that section was cut into
  .venv\\Scripts\\python scripts\\explore.py search "ChatGPT drafts our SOPs"   what retrieval finds, and why
  .venv\\Scripts\\python scripts\\explore.py classify "Static ML scores fermentation runs"   the keyword baseline's reading

Documents: A22 A11 A11D CH4D Q9 AIA FDA-CRED FDA-DP FDA-WL
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.ingest.parse import parse_source  # noqa: E402
from app.ingest.sources import SOURCES_BY_ID  # noqa: E402


def raw(doc: str, page: str) -> None:
    import pymupdf

    src = SOURCES_BY_ID[doc]
    path = get_settings().raw_dir / src.filename
    if path.suffix != ".pdf":
        print(path.read_text(encoding="utf-8")[:3000])
        return
    with pymupdf.open(path) as d:
        print(d[int(page) - 1].get_text())


def sections(doc: str) -> None:
    for s in parse_source(SOURCES_BY_ID[doc], get_settings().raw_dir):
        print(f"§{s.section:10s} {s.title[:60]:60s} p.{s.page_start}  ({len(s.text)} chars)")


def section(doc: str, sec: str) -> None:
    for s in parse_source(SOURCES_BY_ID[doc], get_settings().raw_dir):
        if s.section == sec:
            print(f"§{s.section} {s.title}  (parent: {s.parent_title or '-'}, page {s.page_start})\n")
            print(s.text)
            return
    print("section not found; run: explore.py sections", doc)


def chunks(doc: str, sec: str) -> None:
    from app.retrieval.index import get_index

    for c in get_index().section_chunks(doc, sec):
        print(f"--- {c.id}  ({len(c.text)} chars)\n{c.text}\n")


def search(query: str) -> None:
    from app.retrieval.index import get_index

    print(f"Query: {query}\n")
    print(f"{'rank':4s} {'chunk id':22s} {'keyword rank':12s} {'meaning rank':12s} section")
    for i, r in enumerate(get_index().search(query, k=8), 1):
        print(f"{i:<4d} {r.chunk.id:22s} {str(r.rank_sparse or '-'):12s} {str(r.rank_dense or '-'):12s} {r.chunk.section_title[:45]}")
    print("\nkeyword rank = position in the TF-IDF list, meaning rank = position in the embedding list ('-' = not in its top 50)")


def classify(text: str) -> None:
    from app.assessors.offline import classify as cls, expand_abbreviations

    print("Text as matched:", expand_abbreviations(text), "\n")
    in_scope, reason, c, cues = cls(text)
    if not in_scope:
        print("Out of scope:", reason)
        return
    for field, value in c.items():
        print(f"{field:15s} {value:20s} keywords found: {cues.get(field) or 'none'}")


COMMANDS = {"raw": raw, "sections": sections, "section": section, "chunks": chunks, "search": search, "classify": classify}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](*sys.argv[2:])
