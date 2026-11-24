"""Source map (app/source_map.py, D24): the table of paragraphs that may back each answer."""
from app import source_map
from app.citations import NOT_COVERED, check_judgment
from app.schema import FIELD_VALUES, Judgment


def J(field, value, cites):
    return Judgment(field=field, value=value, rationale="Rationale for this use case, long enough.", citations=cites)


def test_map_covers_every_answer_except_unclear():
    values = {v for vs in FIELD_VALUES.values() for v in vs if v != "unclear"}
    assert set(source_map.SOURCE_MAP) == values
    assert all(source_map.SOURCE_MAP[v] for v in values)


def test_known_wrong_never_overlaps_the_map():
    for value, ids in source_map.KNOWN_WRONG.items():
        assert value in source_map.SOURCE_MAP
        assert not set(ids) & set(source_map.allowed(value)), value


def test_map_matches_the_corpus(index):
    """Change control: a rebuilt index with other content must send the map back for review."""
    assert index.corpus_version == source_map.CORPUS_VERSION, (
        "corpus changed: re-review app/source_map.py (chunk ids may have moved), then update CORPUS_VERSION")
    assert [cid for cid in source_map.all_ids() if not index.get_chunk(cid)] == []


def test_map_paragraphs_always_given_to_the_model(index):
    from app.pipeline import retrieve

    ids = {p.chunk.id for p in retrieve(index, "A spreadsheet macro sums the monthly canteen bills.", 8)}
    assert set(source_map.all_ids()) <= ids


def test_prompt_names_every_map_paragraph():
    from app.llm.prompts import SYSTEM

    assert "{SOURCES}" not in SYSTEM
    assert all(f"[{cid}]" in SYSTEM for cid in source_map.all_ids())


def test_opposite_meaning_citation_dropped(index):
    """W46 benchmark: 'nobody checks' backed by the Annex 22 §1 sentence that a person should check."""
    allowed = {"A22:1:1", "FDA-CRED:IV.A.3:1"}
    wrong = check_judgment(index, J("autonomy", "acts_autonomously", ["A22:1:1"]), allowed)
    assert not wrong.supported and wrong.note == NOT_COVERED and wrong.proposed_ids == ["A22:1:1"]
    right = check_judgment(index, J("autonomy", "acts_autonomously", ["A22:1:1", "FDA-CRED:IV.A.3:1"]), allowed)
    assert right.supported and [c.chunk_id for c in right.citations] == ["FDA-CRED:IV.A.3:1"]
    assert "sole determinant" in right.citations[0].quote


def test_quote_is_the_sentence_the_map_names(index):
    """The same paragraph backs different answers with different sentences."""
    allowed = {"A22:1:1"}
    noncrit = check_judgment(index, J("gmp_relevance", "non_critical", ["A22:1:1"]), allowed).citations[0].quote
    prob = check_judgment(index, J("model_type", "probabilistic", ["A22:1:1"]), allowed).citations[0].quote
    assert "non-critical GMP applications" in noncrit and "human-in-the-loop" not in noncrit  # map-1.3: definition only
    assert "probabilistic output" in prob and prob != noncrit


def test_review_answers_cite_no_duty_sentences():
    """map-1.3: "a person approves each output" is backed by descriptions, not by duties (those back the outcomes)."""
    assert set(source_map.allowed("recommends")) == {"A22:3.3:0", "A22:10.5:0"}


def test_same_sentence_from_two_paragraphs_is_shown_once(index):
    out = check_judgment(index, J("model_type", "dynamic", ["A22:1:0", "A22:1:1"]), {"A22:1:0", "A22:1:1"})
    assert len(out.citations) == 1


def test_non_critical_ml_outcome_quotes_annex11_and_q9(index):
    from app.citations import cite_section
    from app.rules import VERDICT_LABELS, decide
    from app.schema import Classification

    o = decide(True, Classification(gmp_relevance="non_critical", model_type="static", autonomy="acts_autonomously"))
    trims = {(t[0], t[1]): (t[2], t[3]) for t in o.quote_trim}
    quotes = {d: cite_section(index, d, s, o.quote_hint, *trims.get((d, s), ("", ""))).quote for d, s in o.sources}
    assert quotes["A11"].startswith("As part of a risk management system") and quotes["Q9"].startswith("The level of effort")
    assert VERDICT_LABELS["permitted_risk_based"].endswith("(Annex 11, ICH Q9)")


def test_classification_quotes_define_the_class_not_the_consequence(index):
    """W56 (owner review): a model-type source shows what the type is; "should not be used in critical GMP
    applications" belongs to the outcome's source, not to the classification's."""
    for value, cid in {"generative": "AIA:art-50:0", "dynamic": "A22:1:0", "probabilistic": "A22:1:1"}.items():
        q = check_judgment(index, J("model_type", value, [cid]), {cid}).citations[0].quote
        assert "should not be used" not in q and "not apply" not in q and "not covered" not in q, (value, q)
    gen = check_judgment(index, J("model_type", "generative", ["AIA:art-50:0"]), {"AIA:art-50:0"}).citations[0].quote
    assert gen.startswith("AI systems, including general-purpose AI systems, generating synthetic")


def test_should_not_proceed_quotes_the_sentence_for_the_model_type(index):
    from app.citations import cite_section
    from app.rules import decide
    from app.schema import Classification

    for mt, w in {"generative": "Generative AI", "dynamic": "dynamic models", "probabilistic": "probabilistic output"}.items():
        o = decide(True, Classification(gmp_relevance="critical", model_type=mt, autonomy="recommends"))
        q = cite_section(index, "A22", "1", o.quote_hint).quote
        assert w in q and "should not be used in critical GMP applications" in q, (mt, q)


def test_not_gmp_outcome_rests_on_the_gmp_scope():
    from app.rules import decide
    from app.schema import Classification

    o = decide(True, Classification(gmp_relevance="not_gmp", model_type="generative", autonomy="recommends"))
    assert o.sources[0] == ("A11", "principle") and ("AIA", "annex-III") not in o.sources


def test_offline_baseline_cites_only_map_paragraphs(index, audit):
    from app.assessors.offline import OfflineAssessor
    from app.intake_form import form_to_text, normalize_form
    from app.main import FORM_EXAMPLES
    from app.pipeline import run_assessment

    for example in FORM_EXAMPLES:
        form = normalize_form(example["form"])
        r = run_assessment(form_to_text(form), assessor=OfflineAssessor(), index=index, audit=audit, save=False, form=form)
        for j in r.judgments:
            assert all(c.chunk_id in source_map.allowed(j.value) for c in j.citations)
            assert j.value == "unclear" or j.supported, (example["name"], j.field, j.value)


def test_judge_labels():
    assert source_map.judge("acts_autonomously", "FDA-CRED:IV.A.3:1") == "in_map"
    assert source_map.judge("acts_autonomously", "A22:1:1") == "known_wrong"
    assert source_map.judge("acts_autonomously", "AIA:art-14:2") == "outside_map"


def test_highlight_is_the_right_sentence(index):
    """Some paragraphs hold two examples (one per answer) or several glossary entries (W47 review)."""
    expected = {
        ("not_gmp", "A11:principle:0"): "GMP regulated activities",
        ("static", "A22:glossary:1"): "Static – Frozen model",
        ("acts_with_oversight", "FDA-CRED:IV.A.2:1"): "will not be the sole determinant",
        ("acts_with_oversight", "AIA:art-14:2"): "stop",
        ("acts_autonomously", "FDA-CRED:IV.A.2:1"): "only the AI model will be used",
        ("acts_autonomously", "FDA-CRED:IV.A.3:1"): "sole determinant",
        ("recommends", "A22:10.5:0"): "every output",
    }
    field = {v: f for f, vs in FIELD_VALUES.items() for v in vs}
    for (value, cid), words in expected.items():
        quote = check_judgment(index, J(field[value], value, [cid]), {cid}).citations[0].quote
        assert words in quote, (value, cid, quote)
    glossary = check_judgment(index, J("model_type", "static", ["A22:glossary:1"]), {"A22:glossary:1"}).citations[0].quote
    assert glossary.startswith("Static – Frozen model") and "SHAP" not in glossary


def test_bracketed_ids_from_the_model_are_kept(index):
    """Feature check F10e (W50): Gemini copied the prompt's "[A22:1:1]" form; the citation must still count."""
    j = Judgment.model_validate({"field": "model_type", "value": "generative", "rationale": "An LLM writes the report text.",
                                 "citations": ["[AIA:art-50:0]"]})
    checked = check_judgment(index, j, {"AIA:art-50:0"})
    assert j.citations == ["AIA:art-50:0"] and checked.supported and checked.citations[0].chunk_id == "AIA:art-50:0"


def test_brackets_do_not_make_an_unknown_id_valid(index):
    j = Judgment.model_validate({"field": "model_type", "value": "generative", "rationale": "An LLM writes the report text.",
                                 "citations": ["[A22:99:9]"]})
    assert not check_judgment(index, j, {"A22:1:1"}).citations
