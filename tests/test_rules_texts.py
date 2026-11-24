"""Rule texts shown to the user (feature check W50)."""
import pytest

from app.rules import FINAL_ROUND_LABEL, decide
from app.schema import Classification


@pytest.mark.parametrize("gmp,model,names,not_names", [
    ("unclear", "generative", "GMP-critical", "kind of model"),
    ("non_critical", "unclear", "kind of model", "GMP-critical"),
])
def test_r3_names_only_what_is_unclear(gmp, model, names, not_names):
    o = decide(True, Classification(gmp_relevance=gmp, model_type=model, autonomy="recommends"))
    assert o.rule_id == "R3-unclear" and names in o.explanation and not_names not in o.explanation


def test_r3_names_both_when_both_are_unclear():
    o = decide(True, Classification(gmp_relevance="unclear", model_type="unclear", autonomy="unclear"))
    assert "GMP-critical" in o.explanation and "kind of model" in o.explanation


def test_final_round_label_says_what_to_do():
    assert "new proposal" in FINAL_ROUND_LABEL and FINAL_ROUND_LABEL.startswith("Pending clarification")
