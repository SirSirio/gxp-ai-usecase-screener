"""Source map: which paragraphs may be shown as the source of each classification answer.

Why: the three judgments (GMP relevance, model type, autonomy) claim *definitions*, and each
definition lives in a few known paragraphs. A similarity score cannot tell "says this" from "is
about the same topic": in the W46 benchmark the old check kept all 116 cited paragraphs, including
14 that said the opposite (e.g. the Annex 22 §1 human-in-the-loop sentence cited for "nobody
checks the output"). The map is a fixed, reviewable table, like the rules (docs/DECISIONS.md D24).

Used three times:
1. the prompt tells the model which paragraph defines each answer (app/llm/prompts.py);
2. the pipeline always gives the model these paragraphs (app/pipeline.py: retrieve);
3. the citation check keeps only cited paragraphs that are in the map for that answer
   (app/citations.py), and the evaluation scores the model's citations against it.

Change control: the ids are chunk ids of one corpus version (CORPUS_VERSION). A rebuilt index with
different content fails tests/test_source_map.py, so the map is re-reviewed before it is used again.
"unclear" has no entry: it claims nothing, so it needs no source.
"""
from __future__ import annotations

SOURCE_MAP_VERSION = "map-1.3"
CORPUS_VERSION = "e97079b5633b"
# map-1.0: draft from the W46 benchmark. map-1.1: five changes from an independent review against all 591
# paragraphs (WORKLOG W47), accepted by the SME: "not GMP" rests on the Annex 11 GMP boundary, "static" on the
# Annex 22 glossary definition, the two "acts" answers lose the bare "model influence" definition and
# "acts with oversight" gains AI Act Art. 14, and the §10.5 description keeps its condition.
# map-1.2 (owner review, WORKLOG W56): a classification source must define its class, not state a consequence:
# "generative" rests on the AI Act's description of systems generating content (Art. 50), not on the Annex 22
# sentence that excludes generative AI from its scope; "dynamic" and "probabilistic" quote only the defining
# part of their Annex 22 sentences (QUOTE_END). Consequences stay with the outcome sources (app/rules.py).
# map-1.3 (independent review of map-1.2, owner decision, W57): non_critical, informs and recommends quote only
# their defining part; recommends no longer lists duty sentences (FDA warning letter, A22 §1 "should always be
# responsible"), which are consequences and back the outcomes instead; the glossary definition is the main
# source for static; a sentence shown by two paragraphs of one class appears once (app/citations.py).
STATUS = "confirmed by the SME, 2026-11-24"

# value -> ((chunk id, what the paragraph says that backs the answer), ...); the first entry is the main one.
# No EU GMP text defines the two "acts" answers; their sources are FDA examples and the AI Act (stated openly).
SOURCE_MAP: dict[str, tuple[tuple[str, str], ...]] = {
    # gmp_relevance
    "critical": (("A22:1:0", "Annex 22 §1: AI models used in critical applications with direct impact on patient safety, product quality or data integrity"),),
    "non_critical": (("A22:1:1", "Annex 22 §1: non-critical GMP applications, which do not have direct impact on patient safety, product quality or data integrity"),),
    "not_gmp": (("A11:principle:0", "Annex 11 Principle: the annex applies to all forms of computerised systems used as part of GMP regulated activities"),
                ("A11D:1:0", "Annex 11 (draft) §1: applies to all types of computerised systems used in the manufacturing of medicinal products and active substances"),
                ("FDA-CRED:II:0", "FDA credibility guidance §II: uses for operational efficiencies, e.g. internal workflows, that do not impact patient safety or drug quality are outside its scope")),
    # model_type
    "static": (("A22:glossary:1", "Annex 22 glossary: Static – Frozen model: a model where all parameters have been finally set, not allowing further adaption to new data"),
               ("A22:1:0", "Annex 22 §1: static models, i.e. models that do not adapt their performance during use")),
    "dynamic": (("A22:1:0", "Annex 22 §1: dynamic models which continuously and automatically learn and adapt performance during use"),
                ("A22:1:1", "Annex 22 §1: dynamic models which continuously and automatically learn and adapt performance during use")),
    "generative": (("AIA:art-50:0", "EU AI Act Art. 50: AI systems, including general-purpose AI systems, generating synthetic audio, image, video or text content"),),
    "probabilistic": (("A22:1:1", "Annex 22 §1: models with a probabilistic output, which might not give identical outputs for identical inputs"),),
    "non_ml": (("A22:1:0", "Annex 22 §1: machine learning models obtained their functionality through training with data, rather than being explicitly programmed"),),
    # autonomy
    "informs": (("A22:3.3:0", "Annex 22 §3.3: a model gives an input to a decision made by a human operator (human-in-the-loop)"),),
    "recommends": (("A22:3.3:0", "Annex 22 §3.3: a model gives an input to a decision made by a human operator (human-in-the-loop)"),
                   ("A22:10.5:0", "Annex 22 §10.5: depending on the criticality and the level of testing, this may imply a consistent review of every output from the model")),
    "acts_with_oversight": (("FDA-CRED:IV.A.2:1", "FDA credibility guidance §IV.A.2 (manufacturing example): with independent verification on a sample, the AI-based model will not be the sole determinant for the release of product"),
                            ("FDA-CRED:IV.A.3:4", "FDA credibility guidance §IV.A.3 (manufacturing example): measuring fill volume through release testing reduces the AI model influence"),
                            ("AIA:art-14:2", "EU AI Act Art. 14 (high-risk AI): a person can override or reverse the output, or interrupt the system through a stop button")),
    "acts_autonomously": (("FDA-CRED:IV.A.3:1", "FDA credibility guidance §IV.A.3 (clinical example): model influence is high because the AI model will be the sole determinant"),
                          ("FDA-CRED:IV.A.2:1", "FDA credibility guidance §IV.A.2 (clinical example): only the AI model will be used to determine whether the participant is considered low risk")),
}

# Where a quote must start, for paragraphs that hold several entries (a glossary) and would otherwise
# show the end of the previous one. (value, chunk id) -> exact text.
QUOTE_START: dict[tuple[str, str], str] = {
    ("static", "A22:glossary:1"): "Static – Frozen model",
    ("generative", "AIA:art-50:0"): "AI systems, including general-purpose AI systems, generating",
}

# Where a quote must stop: the defining part of a sentence that goes on to state a consequence (map-1.2).
QUOTE_END: dict[tuple[str, str], str] = {
    ("dynamic", "A22:1:0"): "continuously and automatically learn and adapt performance during use",
    ("dynamic", "A22:1:1"): "continuously and automatically learn and adapt performance during use",
    ("probabilistic", "A22:1:1"): "might not provide identical outputs",
    ("generative", "AIA:art-50:0"): "generating synthetic audio, image, video or text content",
    ("non_critical", "A22:1:1"): "do not have direct impact on patient safety, product quality or data integrity",
    ("informs", "A22:3.3:0"): "made by a human operator (human-in-the-loop)",
    ("recommends", "A22:3.3:0"): "made by a human operator (human-in-the-loop)",
}

# Paragraphs found cited, or proposed, for an answer they do NOT support (the answer key's "bad" lines:
# W46 benchmark, W47 review). Not needed by the app, which drops anything outside the map; used by the
# evaluation to tell a known-wrong citation from one that is merely unknown.
KNOWN_WRONG: dict[str, tuple[str, ...]] = {
    "acts_autonomously": ("A22:1:1", "A22:1:0", "A22:10.5:0", "FDA-CRED:IV.A.3:0", "FDA-CRED:IV.B:1"),
    "acts_with_oversight": ("A22:1:1", "FDA-CRED:IV.A.3:0"),
    "probabilistic": ("A22:1:0",),
}


def allowed(value: str) -> tuple[str, ...]:
    """Chunk ids that may be shown as the source of this answer (empty for "unclear")."""
    return tuple(cid for cid, _ in SOURCE_MAP.get(value, ()))


def describe(value: str, chunk_id: str) -> str:
    """What the paragraph says that backs this answer ("" if it is not in the map for it)."""
    return next((what for cid, what in SOURCE_MAP.get(value, ()) if cid == chunk_id), "")


def quote_start(value: str, chunk_id: str) -> str:
    """Exact text the quote must start at ("" if the best sentence is fine as it is)."""
    return QUOTE_START.get((value, chunk_id), "")


def quote_end(value: str, chunk_id: str) -> str:
    """Exact text the quote must stop at ("" if the whole sentence is shown)."""
    return QUOTE_END.get((value, chunk_id), "")


def all_ids() -> tuple[str, ...]:
    """Every paragraph in the map, in a fixed order (they are always given to the model)."""
    return tuple(dict.fromkeys(cid for entries in SOURCE_MAP.values() for cid, _ in entries))


def judge(value: str, chunk_id: str) -> str:
    """Score one citation for the evaluation: "in_map", "known_wrong" or "outside_map"."""
    if chunk_id in allowed(value):
        return "in_map"
    return "known_wrong" if chunk_id in KNOWN_WRONG.get(value, ()) else "outside_map"
