from app.citations import NOT_COVERED, check_judgment
from app.controls import CONTROLS
from app.rules import RULES
from app.schema import Judgment


def J(value, cites, field="model_type"):
    return Judgment(field=field, value=value, rationale="The tool is a large language model that drafts text.", citations=cites)


def test_supported_citation_kept(index):
    cid = "AIA:art-50:0"  # map-1.2: generative AI rests on the AI Act's description of content-generating systems
    out = check_judgment(index, J("generative", [cid]), allowed_ids={cid})
    assert out.supported and out.citations[0].chunk_id == cid
    assert "generating synthetic" in out.citations[0].quote


def test_fabricated_id_dropped(index):
    out = check_judgment(index, J("generative", ["A22:99:0"]), allowed_ids={"A22:99:0"})
    assert not out.supported and out.note == NOT_COVERED


def test_not_retrieved_id_dropped(index):
    cid = index.section_chunks("A22", "1")[0].id
    out = check_judgment(index, J("generative", [cid]), allowed_ids=set())
    assert not out.supported


def test_irrelevant_passage_dropped(index):
    cid = index.section_chunks("A11D", "11.5")[0].id  # password rules
    out = check_judgment(index, J("generative", [cid]), allowed_ids={cid})
    assert not out.supported


def test_every_control_and_rule_reference_exists(index):
    """A control can only cite sections that really exist in the corpus."""
    refs = {r for c in CONTROLS.values() for r in c.refs} | {r for rule in RULES for r in rule.sources}
    missing = [r for r in refs if not index.section_chunks(*r) and not index.get_section(*r)]
    assert not missing, missing


def test_quote_does_not_stop_at_abbreviation(index):
    from app.citations import best_quote

    q = best_quote(index.get_chunk("A22:1:1"), "non-critical GMP applications personnel responsible human-in-the-loop")
    assert "i.e. a human-in-the-loop" in q


def test_refs_readable(index):
    assert index.get_chunk("A22:1:1").ref == "Annex 22 (draft) §1 Scope"
    assert index.get_chunk("FDA-WL:ai-use:0").ref.startswith("FDA warning letter 320-26-58: Inappropriate use")


def test_unclear_judgment_needs_no_source(index):
    """'unclear' claims nothing, so it must not be flagged as unsupported on the result page (W21)."""
    from app.citations import NO_SOURCE_NEEDED, check_judgment
    from app.schema import Judgment

    j = check_judgment(index, Judgment(field="autonomy", value="unclear", rationale="The form does not say who checks it.", citations=[]), set())
    assert j.supported and j.citations == [] and j.note == NO_SOURCE_NEEDED
