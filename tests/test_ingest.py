"""Parsing keeps the documents' own section ids, so citations always point to real sections."""
from app.ingest.chunk import chunk_sections
from app.ingest.parse import _plausible_next, join_lines, parse_source
from app.ingest.sources import SOURCES, SOURCES_BY_ID


def test_plausible_next():
    assert _plausible_next((2, 1), (2,))
    assert _plausible_next((3,), (2, 4))
    assert _plausible_next((2, 5), (2, 4))
    assert not _plausible_next((30,), (2, 4))  # "30 June 2011"
    assert not _plausible_next((2, 4), (2, 4))


def test_join_lines_hyphenation():
    assert join_lines(["pharmaceuti-", "cal quality"]) == "pharmaceutical quality"
    assert join_lines(["a risk-", "based approach"]) == "a risk-based approach"


def test_annex22_sections(raw_dir):
    secs = {s.section: s for s in parse_source(SOURCES_BY_ID["A22"], raw_dir)}
    for sid in ["1", "2.1", "3.3", "4.3", "5.6", "6.5", "7.4", "8.2", "9.2", "10.5", "glossary"]:
        assert sid in secs, sid
    assert "should not be used in critical GMP applications" in secs["1"].text
    assert secs["3.3"].title == "Human-in-the-loop"
    assert secs["10.5"].title == "Human review"


def test_other_documents(raw_dir):
    q9 = [s.section for s in parse_source(SOURCES_BY_ID["Q9"], raw_dir)]
    assert "4.3" in q9 and "II.1" in q9
    assert not any(s.isdigit() and int(s) > 8 for s in q9), "reference list must not become sections"
    dp = [s.section for s in parse_source(SOURCES_BY_ID["FDA-DP"], raw_dir)]
    assert [f"area-{i}" for i in range(1, 6)] == [s for s in dp if s.startswith("area-")]
    wl = {s.section: s for s in parse_source(SOURCES_BY_ID["FDA-WL"], raw_dir)}
    assert "reviewed and cleared" in wl["ai-use"].text
    aia = [s.section for s in parse_source(SOURCES_BY_ID["AIA"], raw_dir)]
    assert aia == [f"art-{n}" for n in SOURCES_BY_ID["AIA"].articles] + ["annex-III"]
    ch4 = {s.section: s for s in parse_source(SOURCES_BY_ID["CH4D"], raw_dir)}
    assert "artificial intelligence" in ch4["4.24"].text


def test_chunk_ids_unique_and_within_one_section(raw_dir):
    ids = set()
    for src in SOURCES:
        if not (raw_dir / src.filename).exists():
            continue
        secs = parse_source(src, raw_dir)
        for c in chunk_sections(src, secs):
            assert c.id not in ids
            ids.add(c.id)
            assert c.id.startswith(f"{src.doc_id}:{c.section}:")
            assert len(c.text) <= 1600
