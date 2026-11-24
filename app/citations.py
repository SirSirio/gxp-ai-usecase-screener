"""Citation check: every claim shown to the user must rest on a real, retrieved passage.

For each judgment:
1. drop cited ids that were never retrieved or fetched (the model cannot cite what it was not shown);
2. drop cited ids that the source map does not list for this answer (app/source_map.py). Until map-1.0
   a similarity threshold decided this step; it kept every cited paragraph in the W46 benchmark,
   including 14 that said the opposite of the answer (docs/DECISIONS.md D24);
3. if none survive, the judgment is marked unsupported and the answer says "Not covered by the sources."
The similarity score is still computed and shown as `support`, for information only.
"""
from __future__ import annotations

import re

from app import source_map
from app.models import Chunk
from app.retrieval.index import KnowledgeIndex, content_words
from app.schema import Citation, CheckedJudgment, Judgment

NOT_COVERED = "Not covered by the sources."
NO_SOURCE_NEEDED = "Not enough information in the proposal to classify this; see the questions."

LABELS = {
    "critical": "GMP-critical", "non_critical": "GMP, non-critical", "not_gmp": "Not GMP", "unclear": "Unclear",
    "static": "Static ML model", "dynamic": "Dynamic / adaptive model", "generative": "Generative AI / LLM",
    "probabilistic": "Probabilistic ML model", "non_ml": "Not ML (programmed logic)",
    "informs": "AI informs, human decides", "recommends": "AI recommends, human approves each output",
    "acts_with_oversight": "AI acts, human oversees", "acts_autonomously": "AI acts autonomously",
}

# What each classification value means in the sources' own words. Used as the claim text, so the
# support check compares the regulatory meaning (not the user's wording) with the cited passage.
VALUE_CLAIMS = {
    "critical": "AI models used in critical GMP applications with direct impact on patient safety, product quality or data integrity",
    "non_critical": "non-critical GMP applications which do not have direct impact on patient safety, product quality or data integrity",
    "not_gmp": "the annex applies to computerised systems used in the manufacturing of medicinal products and active substances",
    "unclear": "the annex applies where AI models are used in critical applications with direct impact on patient safety, product quality or data integrity",
    "static": "static models that do not adapt their performance during use and give deterministic output",
    "dynamic": "dynamic models which continuously and automatically learn and adapt performance during use",
    "generative": "AI systems generating synthetic audio, image, video or text content, Generative AI and Large Language Models",
    "probabilistic": "models with a probabilistic output which might not provide identical outputs for identical inputs",
    "non_ml": "machine learning models which obtained their functionality through training with data rather than being explicitly programmed",
    "informs": "a model used to give an input to a decision made by a human operator, human-in-the-loop",
    "recommends": "a model used to give an input to a decision made by a human operator, human review of every output",
    "acts_with_oversight": "model influence: the contribution of the AI model relative to other evidence in the decision, human oversight",
    "acts_autonomously": "model influence: the AI model output alone determines the decision without human review",
}


def claim_text(field: str, value: str, rationale: str) -> str:
    return f"{VALUE_CLAIMS.get(value, value)}. {rationale}"


SENTENCE_SPLIT = re.compile(r"(?<!i\.e\.)(?<!e\.g\.)(?:(?<=[.;?])|(?<=[.?]”))\s+")


def best_quote(chunk: Chunk, claim: str, max_chars: int = 320, start: str = "", end: str = "") -> str:
    """The sentence of the chunk that shares most words with the claim.

    `start` / `end`: exact text the quote must begin / stop at, applied to the whole sentence before it is
    shortened (source map QUOTE_START / QUOTE_END). `end` is used where a sentence first defines a class and
    then states a consequence: a classification source shows the definition only (W56).
    """
    sentences = [s.strip() for s in SENTENCE_SPLIT.split(chunk.text) if len(s.strip()) > 20] or [chunk.text]
    words = content_words(claim)
    pool = [s for s in sentences if (not start or start in s) and (not end or end in s)] or sentences
    best = max(pool, key=lambda s: len(words & content_words(s)))
    if start and start in best:
        best = best[best.index(start):]
    if end and end in best:
        cut = best.index(end) + len(end)
        best = best[:cut] + ("…" if best[cut:].strip(" .") else "")
    return best if len(best) <= max_chars else best[: max_chars - 1].rsplit(" ", 1)[0] + "…"


def lexical_support(claim: str, chunk: Chunk) -> float:
    words = content_words(claim)
    if not words:
        return 0.0
    return len(words & content_words(chunk.text + " " + chunk.section_title)) / len(words)


def make_citation(chunk: Chunk, claim: str, support: float, start: str = "", end: str = "") -> Citation:
    return Citation(
        chunk_id=chunk.id, doc_id=chunk.doc_id, ref=chunk.ref, doc_status=chunk.doc_status, url=chunk.url,
        page=chunk.page_start, quote=best_quote(chunk, claim, start=start, end=end), support=round(support, 3),
    )


def check_judgment(index: KnowledgeIndex, j: Judgment, allowed_ids: set[str]) -> CheckedJudgment:
    claim = claim_text(j.field, j.value, j.rationale)
    mapped = source_map.allowed(j.value)
    candidates = [cid for cid in dict.fromkeys(j.citations) if cid in allowed_ids and cid in mapped and index.get_chunk(cid)]
    dense = index.similarity(VALUE_CLAIMS.get(j.value, claim), candidates)
    kept: list[Citation] = []
    for cid in candidates:
        chunk = index.get_chunk(cid)
        lex = lexical_support(VALUE_CLAIMS.get(j.value, claim), chunk)
        # the quote is the sentence the map entry names, not whichever sentence shares most words
        cit = make_citation(chunk, source_map.describe(j.value, cid) or claim, max(dense[cid], lex),
                            start=source_map.quote_start(j.value, cid), end=source_map.quote_end(j.value, cid))
        if any(k.quote == cit.quote for k in kept):  # two paragraphs of one class can show the same sentence (W57)
            continue
        kept.append(cit)
    dropped = len(j.citations) - len(kept)
    note = None
    if j.value == "unclear" and not kept:
        # "unclear" claims nothing about the use case, so it needs no source: showing it as
        # "Unsupported" was misleading (WORKLOG W21, D029). The open questions say what is missing.
        return CheckedJudgment(
            field=j.field, value=j.value, label=LABELS.get(j.value, j.value), rationale=j.rationale,
            supported=True, citations=[], citations_proposed=len(j.citations), proposed_ids=list(j.citations),
            note=NO_SOURCE_NEEDED,
        )
    if not kept:
        note = NOT_COVERED
    elif dropped:
        note = f"{dropped} citation(s) dropped by the citation check."
    return CheckedJudgment(
        field=j.field, value=j.value, label=LABELS.get(j.value, j.value), rationale=j.rationale,
        supported=bool(kept), citations=kept, citations_proposed=len(j.citations), proposed_ids=list(j.citations),
        note=note,
    )


def cite_section(index: KnowledgeIndex, doc_id: str, section: str, claim: str, start: str = "", end: str = "") -> Citation | None:
    """Resolve a fixed (doc, section) reference from the rules or controls to its best chunk."""
    chunks = index.section_chunks(doc_id, section)
    if not chunks:
        sec = index.get_section(doc_id, section)  # heading-only section: use its first child
        chunks = [index.get_chunk(cid) for cid in (sec.chunk_ids[:3] if sec else [])]
        chunks = [c for c in chunks if c]
    if not chunks:
        return None
    pool = [c for c in chunks if start in c.text] if start else chunks
    best = max(pool or chunks, key=lambda c: lexical_support(claim, c))
    return make_citation(best, claim, lexical_support(claim, best), start=start, end=end)
