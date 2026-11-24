# Test set notes

Files: `eval/testset.jsonl` (30 held-out cases, T01–T30) and `eval/devset.jsonl` (10 dev cases, D01–D10). All labels are `label_status: draft` until the process SME reviews them.

## Distribution

| Verdict | Test | Dev |
|---|---|---|
| out_of_scope | 6 | 2 |
| outside_gmp | 3 | 1 |
| not_permitted_critical | 4 | 1 |
| needs_more_information | 2 | 1 |
| not_ai_annex11 | 2 | 1 |
| annex22_full | 4 | 1 |
| hitl_required | 3 | 1 |
| permitted_with_hitl | 3 | 1 |
| permitted_risk_based | 3 | 1 |
| **Total** | **30** | **10** |

| Category | Test | Dev |
|---|---|---|
| clear | 12 | 4 |
| borderline | 12 | 4 |
| out_of_scope | 6 | 2 |

Model types in the test set: static 7, generative 11, dynamic 2, probabilistic 1, non_ml 2, unclear 1 (in-scope cases only).

## How the cases were written

- Labels follow `docs/LABELING_GUIDE.md`. The four fields were labelled first and the verdict was then derived from the §6 rule table in priority order (out_of_scope, outside_gmp, not_permitted_critical, needs_more_information, not_ai_annex11, annex22_full, hitl_required, needs_more_information for unclear autonomy, permitted_with_hitl, permitted_risk_based). A script re-derives every verdict and checks enums, ids, keys and source ids.
- Every in-scope case cites 1–3 passages from `data/raw/` that a correct answer must rely on. Out-of-scope cases cite nothing.
- The descriptions read like intake requests from business or manufacturing staff: plain language, vendor and product names ("Copilot", "the vendor's camera machine"), and some irrelevant detail. They mostly avoid the label vocabulary. One deliberate trap: T07 contains the word "critical" as a deviation class.
- Paired cases: T04/T05 are the same document-drafting task (specs, SOPs, MBRs from client tech transfer packages), modelled on FDA warning letter 320-26-58. In T04 there is no quality-unit review; in T05 QA reviews. T07/T18 both use an LLM on deviations, one proposing classification and hold and one only summarising. T16 (controlled retraining) contrasts with T08 (online learning).
- Dev cases cover the same verdicts but not the same scenarios as the test set.

## Borderline cases (test set)

| Id | Contested field | Label chosen | Alternative | Why this label |
|---|---|---|---|---|
| T04 | gmp_relevance | non_critical → hitl_required | critical → not_permitted_critical (specs and MBRs drive quality) | The task is document drafting. Guide §2 says criticality is about the task, not about the review, and FDA-WL 'ai-use' requires QU review rather than banning AI drafting. The missing review goes into autonomy. |
| T07 | gmp_relevance | critical → not_permitted_critical | non_critical → permitted_with_hitl (QA decides) | Classifying deviation criticality and proposing batch hold is a guide §2 critical example. A22 §1 does not let a human in the loop rescue a critical LLM use. |
| T11 | gmp_relevance (autonomy secondary) | critical, acts_with_oversight → annex22_full | non_critical "pre-sort aid" | Accepted syringes are never seen by a person, so the model makes the accept decision. Autonomy could also be acts_autonomously; the verdict is the same either way. |
| T13 | gmp_relevance | non_critical → permitted_risk_based | critical (monitoring the GMP process) | Banner only. The validated alarms are unchanged and there is no control action and no GMP record. |
| T16 | model_type | static → annex22_full | dynamic → not_permitted_critical | Candidates are retrained nightly, but the deployed model is frozen and replaced only through re-test plus QA change control (A22 §10.1, glossary "static"). Nothing adapts automatically during use. |
| T18 | gmp_relevance | non_critical → permitted_with_hitl | critical (feeds an investigation record) | No classification or decision. The investigator and QA still own root cause, impact and classification. |
| T20 | gmp_relevance | non_critical → permitted_risk_based | not_gmp → outside_gmp | Material planning for GMP materials falls under supply chain control (Q9 II.9; FDA-DP area 3), but it is only planning support. |
| T22 | model_type | non_ml → not_ai_annex11 | static (marketed "AI") → annex22_full, or unclear → needs_more_information | The vendor spec describes configured limits and rules, which is explicit programming (A22 §1). |
| T24 | model_type | probabilistic → not_permitted_critical | static → annex22_full | Same input, different output is the A22 §1 definition of a probabilistic model. |
| T25 | autonomy | unclear → needs_more_information | recommends (assume doc review) or acts_autonomously | The request does not say whether translations are reviewed, and that decides the verdict. |
| T26 | gmp_relevance | not_gmp → outside_gmp | non_critical → permitted_with_hitl | Submission writing is regulatory affairs, not manufacturing (A22 §1 scope). FDA-CRED §II excludes drafting a regulatory submission. |
| T28 | gmp_relevance | non_critical → hitl_required | critical (official trend report = GMP record) → not_permitted_critical | Treated as trending information supporting QA review (guide §2), issued with no review. |

Dev borderline cases: D04 (model_type unclear, vendor black box), D05 (gmp_relevance, tech transfer drafting), D07 (model_type, "smart triage" rules), D08 (gmp_relevance, client portal chatbot).

## Labels most worth SME review

- **T26** (regulatory submission drafting = not_gmp). The guide lists no regulatory-affairs example in either `not_gmp` or `non_critical`.
- **T28** and **T04** (whether an AI-issued GMP document or report is "a GMP record used as such", which would make it critical).
- **T20** (whether supply-chain planning is GMP context or not).
- **T09** (out_of_scope). The request names a real AI use (Copilot in QA) but asks for a compliance sign-off. It is labelled out_of_scope per guide §1. A tool that refuses the sign-off but offers to screen the use is behaving correctly.
- **T11** autonomy (acts_with_oversight vs acts_autonomously). This does not change the verdict.

## Label change log
| Date | Case | Change | Reason | By |
|---|---|---|---|---|
| 2026-11-21 | T04 | gmp_relevance non_critical → critical; verdict hitl_required → not_permitted_critical | AI-written specifications/SOPs/MBRs issued without review are GMP records used as such (guide §2, v1.1). High confidence. | Independent review, applied by developer |
| 2026-11-21 | T11 | autonomy acts_with_oversight → acts_autonomously; contested field → autonomy | No human review or sampling described. Verdict unchanged. | Independent review, applied by developer |

### Open for SME decision (not changed)
| Case | Current | Reviewer suggestion | Reviewer confidence |
|---|---|---|---|
| T28 | non_critical / hitl_required | critical / not_permitted_critical (unreviewed trend report issued as the official GMP report) | Medium |
| T23 | autonomy acts_with_oversight | acts_autonomously, for consistency with T11 | Medium |
| T26 | not_gmp / outside_gmp | non_critical / permitted_with_hitl (LLM fed confidential client validation data for a BLA) | Low-medium |
| T20, T09, T16 | — | keep | — |
