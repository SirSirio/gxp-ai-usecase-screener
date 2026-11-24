"""The "How it works" page: it renders, it is linked, and its decision tree says exactly what the rules say.

The tree on the page is written out by hand (app/how_it_works.py) and embedded as JSON. Here it is walked for
every combination of classes and each leaf is compared with app.rules.decide(): verdict, rule, label, tone and
source tags. A change to the rules that the page does not follow fails this test.
"""
import itertools
import json
import re

import pytest
from markupsafe import escape
from fastapi.testclient import TestClient

from app.rules import RULES, VERDICT_LABELS, decide
from app.schema import Classification, FIELD_VALUES

PAGES = ("/", "/submit", "/sources", "/how-it-works")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    from app import config

    tmp = tmp_path_factory.mktemp("hiw")
    config.use_settings(config.Settings(provider="offline", audit_dir=tmp / "audit", results_dir=tmp / "results"))
    from app.main import app

    yield TestClient(app)
    config.use_settings(None)


@pytest.fixture(scope="module")
def page(client):
    r = client.get("/how-it-works")
    assert r.status_code == 200
    return r.text


@pytest.fixture(scope="module")
def tree(page):
    m = re.search(r'<script type="application/json" id="hiw-data">(.*?)</script>', page, re.S)
    assert m, "tree data missing from the page"
    return json.loads(m.group(1))


def walk(tree: dict, in_scope: bool, c: Classification | None) -> dict:
    """Follow the page's tree for one case and return the leaf it ends in."""
    values = {"in_scope": "yes" if in_scope else "no", **(c.model_dump() if c else {})}
    at, seen = tree["root"], []
    while at in tree["nodes"]:
        node = tree["nodes"][at]
        branch = [b for b in node["branches"] if values[node["field"]] in b["values"]]
        assert len(branch) == 1, f"{at}: {values[node['field']]!r} must be on exactly one branch"
        seen.append(at)
        at = branch[0]["to"]
    assert at in tree["leaves"], f"path {seen} ends nowhere ({at})"
    return tree["leaves"][at]


def test_page_renders_with_flow_tree_and_principle(page):
    assert "<h1>How it works</h1>" in page
    assert "The AI maps inputs and cites sources." in page and "The outcome is set by deterministic rules." in page
    assert 'data-tree' in page and 'data-stepper' in page and "The decision tree as text" in page
    assert '/static/how_it_works.js' in page


def test_nav_link_on_every_page_and_marked_current_on_its_own(client):
    for path in PAGES:
        html = client.get(path).text
        assert '<a href="/how-it-works"' in html, path
    assert '<a href="/how-it-works" aria-current="page">How it works</a>' in client.get("/how-it-works").text
    assert '<a href="/how-it-works" aria-current="page">' not in client.get("/").text


def test_landing_page_links_to_it(client):
    assert 'class="link" href="/how-it-works"' in client.get("/").text


def test_every_combination_of_classes_reaches_the_rules_outcome(tree):
    from app.main import _verdict_tone

    rules = {r.id: r for r in RULES}
    combos = list(itertools.product(*(FIELD_VALUES[f] for f in ("gmp_relevance", "model_type", "autonomy"))))
    assert len(combos) == 4 * 6 * 5
    cases = [(False, None)] + [(True, Classification(gmp_relevance=g, model_type=m, autonomy=a)) for g, m, a in combos]
    for in_scope, c in cases:
        expected, leaf = decide(in_scope, c), walk(tree, in_scope, c)
        assert (leaf["verdict"], leaf["rule"]) == (expected.verdict, expected.rule_id), c
        assert leaf["label"] == VERDICT_LABELS[expected.verdict]
        assert leaf["tone"] == _verdict_tone(expected.verdict)
        sources = rules[expected.rule_id].sources if expected.rule_id in rules else expected.sources
        assert len(leaf["tags"]) == len(sources)


def test_each_question_splits_its_classes_exactly_once(tree):
    for node in tree["nodes"].values():
        values = [v for b in node["branches"] for v in b["values"]]
        allowed = ("yes", "no") if node["field"] == "in_scope" else FIELD_VALUES[node["field"]]
        assert sorted(values) == sorted(allowed), node["id"]
        assert [tree["chips"][cid]["value"] for cid in node["chips"]] == values  # stepper order = tree order


def test_every_leaf_is_reachable_and_rendered_with_its_verdict(tree, page):
    reached = {walk(tree, True, Classification(gmp_relevance=g, model_type=m, autonomy=a))["id"]
               for g, m, a in itertools.product(*(FIELD_VALUES[f] for f in ("gmp_relevance", "model_type", "autonomy")))}
    reached.add(walk(tree, False, None)["id"])
    assert reached == set(tree["leaves"])
    for lid, leaf in tree["leaves"].items():
        assert f'data-leaf="{lid}" data-verdict="{leaf["verdict"]}" data-rule="{leaf["rule"]}"' in page
        assert str(escape(leaf["label"])) in page  # full label in the (i) and in the text version


def test_chip_paths_lead_where_the_branches_say(tree):
    for cid, chip in tree["chips"].items():
        assert chip["path"][-1] == cid
        for earlier, later in zip(chip["path"], chip["path"][1:]):
            assert tree["chips"][earlier]["to"] == tree["chips"][later]["node"], cid


def test_example_paths_end_at_the_outcome_of_their_classification(tree):
    from app.how_it_works import PRESETS

    assert [p["chip"] for p in tree["presets"]] == [p["chip"] for p in PRESETS]
    for p in PRESETS:
        expected = decide(True, Classification(**p["cls"])).verdict
        assert tree["leaves"][tree["chips"][p["chip"]]["to"]]["verdict"] == expected, p["name"]
        assert tree["chips"][p["chip"]]["value"] in p["cls"].values()


def test_flow_counts_come_from_the_code(page):
    from app.ingest.sources import SOURCES
    from app.intake_form import MAX_ROUNDS, QUESTIONS

    assert f"{len(QUESTIONS)} questions" in page
    assert f"{len(SOURCES)} public documents" in page
    assert f"{len(RULES)} fixed rules" in page
    assert f"Up to {MAX_ROUNDS} rounds" in page


def test_no_em_or_en_dashes_in_the_page_copy(page):
    text = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    assert "—" not in text and "–" not in text
