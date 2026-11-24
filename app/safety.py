"""Which wrong outcomes are dangerous. SME decision 2026-11-22 (docs/DECISIONS.md D19).

Acceptance criteria for this tool: zero dangerous errors, and "when unsure, say unclear".
Accuracy is a secondary number. An error is DANGEROUS when the tool's outcome is more permissive
than the correct one, so a proposer could go ahead without a required "no", question or control.

Rules, in order:
1. The correct outcome: not an error.
2. The tool says "Not yet" (needs_more_information): never dangerous, because questions always come back.
3. The correct outcome is "Not yet": dangerous if the tool says any "proceed" or "Not assessed"
   (the open questions are skipped); a stricter "no" is fine.
4. The tool says "Not assessed" (out_of_scope) for a real proposal = wrongly refused: dangerous,
   except when the correct outcome is "Not GMP" (the proposer only misses non-GMP advice).
5. Otherwise: dangerous if the tool's outcome is ranked more permissive than the correct one.
A question wrongly screened as a proposal (correct = out_of_scope) is never dangerous: rule 5,
since "Not assessed" is the most permissive rank.
"""
from __future__ import annotations

# Strictest first. needs_more_information is outside the ranking (rules 2 and 3).
STRICTNESS = (
    "not_permitted_critical",   # Should not proceed
    "hitl_required",            # Not as described: add human review
    "annex22_full",             # GMP-critical ML: full Annex 22 controls
    "permitted_with_hitl",      # Generative AI: a person approves each output
    "permitted_risk_based",     # Non-critical ML: risk-based controls
    "not_ai_annex11",           # Not ML: standard GMP system (Annex 11)
    "outside_gmp",              # Not GMP: normal IT rules
    "out_of_scope",             # Not assessed
)
RANK = {v: i for i, v in enumerate(STRICTNESS)}
NOT_YET = "needs_more_information"


def is_dangerous(expected: str, got: str | None) -> bool:
    """True if the tool's outcome `got` is a dangerous error for the correct outcome `expected`.
    `got` is None when the answer was invalid and rejected: nothing is shown, so not dangerous
    (invalid answers are counted by schema_valid_rate)."""
    if got is None or got == expected or got == NOT_YET:
        return False
    if expected == NOT_YET:
        return RANK[got] >= RANK["annex22_full"]  # any "proceed" or "Not assessed"
    if got == "out_of_scope":
        return expected != "outside_gmp"
    return RANK[got] > RANK[expected]


def error_kind(expected: str, got: str | None, expected_in_scope: bool, got_in_scope: bool | None) -> str | None:
    """Short label for the report: None if correct."""
    if got is None:
        return "invalid"
    if got == expected:
        return None
    if expected_in_scope and got_in_scope is False:
        return "wrongly_refused"
    if not expected_in_scope and got_in_scope:
        return "wrongly_screened"
    return "dangerous" if is_dangerous(expected, got) else "stricter_or_not_yet"
