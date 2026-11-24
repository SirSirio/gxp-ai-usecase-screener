"""Invalid assessor output must be rejected, never shown."""
import pytest
from pydantic import ValidationError

from app.schema import ModelAssessment


def valid(**over):
    base = {
        "in_scope": True,
        "title": "LLM drafts SOPs",
        "classification": {"gmp_relevance": "non_critical", "model_type": "generative", "autonomy": "recommends"},
        "judgments": [
            {"field": "gmp_relevance", "value": "non_critical", "rationale": "Drafts go through document control.", "citations": ["A22:1:0"]},
            {"field": "model_type", "value": "generative", "rationale": "It is a large language model.", "citations": ["A22:1:1"]},
            {"field": "autonomy", "value": "recommends", "rationale": "QA approves every SOP.", "citations": ["A22:10.5:0"]},
        ],
    }
    base.update(over)
    return base


def test_valid_passes():
    assert ModelAssessment.model_validate(valid()).classification.model_type == "generative"


@pytest.mark.parametrize("mutate", [
    lambda d: d["classification"].update(model_type="llm"),  # not an allowed enum value
    lambda d: d["judgments"][1].update(value="static"),  # contradicts classification
    lambda d: d["judgments"].pop(),  # missing a field
    lambda d: d.update(verdict="annex22_full"),  # the model may not decide verdicts
    lambda d: d.update(classification=None),  # in scope without classification
    lambda d: d["judgments"][0].update(rationale="ok"),  # too short to be an explanation
    lambda d: d.update(in_scope=False),  # out of scope but still classifies
])
def test_invalid_rejected(mutate):
    d = valid()
    mutate(d)
    with pytest.raises(ValidationError):
        ModelAssessment.model_validate(d)


def test_out_of_scope_shape():
    m = ModelAssessment.model_validate({"in_scope": False, "title": "Poem", "out_of_scope_reason": "Unrelated."})
    assert m.classification is None
