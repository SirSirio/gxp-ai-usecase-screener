"""The intake form definition: validation and the text the classifier receives."""
import pytest

from app.intake_form import QUESTIONS, FormError, form_to_text, normalize_form


def test_normalize_fills_unanswered_questions():
    f = normalize_form({"what": "  A chatbot drafts cleaning SOPs.\r\nQA approves.  "})
    assert set(f) == {q["id"] for q in QUESTIONS}
    assert f["what"] == "A chatbot drafts cleaning SOPs.\nQA approves."
    assert f["title"] == "" and f["areas"] == [] and f["gmp_impact"] == {"choice": None, "explain": ""}


def test_normalize_orders_multi_choice_like_the_definition():
    f = normalize_form({"what": "x" * 20, "areas": ["qa", "manufacturing", "qa"]})
    assert f["areas"] == ["manufacturing", "qa"]


@pytest.mark.parametrize("bad", [
    {"areas": ["moon_base"]},
    {"ai_type": {"choice": "crystal_ball", "explain": ""}},
    {"ai_type": "llm"},
    {"ai_type": {"choice": "llm", "explain": "", "extra": 1}},
    {"unknown_question": "x"},
    {"title": 42},
    {"what": "too short"},
])
def test_normalize_rejects_invalid_answers(bad):
    with pytest.raises(FormError):
        normalize_form({"what": "x" * 20} | bad)


def test_form_to_text_skips_unanswered_questions():
    from app.intake_form import option_label

    f = normalize_form({"what": "A chatbot drafts cleaning SOPs; QA approves each one.",
                        "output_use": {"choice": "person_approves", "explain": "QA signs in the eDMS."}})
    text = form_to_text(f)
    assert text.startswith("What should the AI do?\nA chatbot drafts")
    assert option_label("output_use", "person_approves") + ". QA signs in the eDMS." in text
    assert "What kind of AI is it?" not in text  # unanswered single choice: no empty label
