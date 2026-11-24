# Labeling guide

How each classification field is defined. The assistant, the rules layer, the test set and the evaluation all use these definitions. If a definition changes, the test-set labels must be re-checked.

Status: **draft definitions, to be reviewed by Sirio (process SME role).** Revised once after the independent review (see changelog at the end).

## 1. `in_scope`

`true` when the input describes a proposed (or existing) use of AI or automation in a company context that someone wants screened.

`false` when the input is:
- a general knowledge question ("What is Annex 22?", "Who wrote GAMP?")
- a request for legal advice or a final compliance verdict ("Are we compliant?", "Can we be sued?")
- unrelated to AI or automation ("Write me a poem", "What is the weather")

## 2. `gmp_relevance`

Based on draft Annex 22 §1: a critical application is one with *direct impact on patient safety, product quality or data integrity*.
**Direct vs indirect (SME decision 2026-11-22, form-1.1):** the line is *what the GMP decision is based on*. Direct: the decision rests on the AI output (it decides, is the basis of the decision, becomes a GMP record or sets the process), even if a person confirms it. Indirect: the output gives ideas or information and people decide on their own evidence through the normal GMP process (e.g. improvement ideas that go through investigation and change control). The form's GMP question uses this wording.

| Value | Meaning | Typical examples |
|---|---|---|
| `critical` | The AI output performs, decides or provides input to a GMP decision, a GMP record used as such, or a process control, with direct impact on patient safety, product quality or data integrity. | Visual inspection accept/reject; batch release or disposition; in-process control or real-time release; predicting a CQA used for release; classifying deviation criticality that drives disposition; writing QC results; **AI-written specifications, SOPs or batch records issued without review (the AI output is the GMP record)** |
| `non_critical` | GMP context, but the AI output is not itself a GMP decision, GMP record or control. It supports people who then work through the normal GMP process. | First drafts of SOPs or training material that a person reviews and approves under document control (the approved document, not the AI draft, is the record); searching or summarising guidance; trending dashboards for information; planning or scheduling support |
| `not_gmp` | Not part of GMP-regulated activities. | HR, finance, marketing, sales, IT helpdesk, generic office productivity, commercial forecasting |
| `unclear` | The description does not say enough to decide. | "Use AI on our batch data" |

Criticality is about the **task**, not about whether a human checks the output. Human review is captured in `autonomy`. Draft Annex 22 keeps the two separate: a human in the loop does not make a critical generative use acceptable.

## 3. `model_type`

| Value | Meaning |
|---|---|
| `static` | Trained ML model whose parameters are frozen in use and whose output is deterministic (same input gives the same output). Classical ML, computer vision CNNs, soft sensors, anomaly detection with a fixed model. Also a model that is retrained (even automatically) when a new version only goes live after re-test and approval under change control: what counts is the version in use (A22 §1, glossary; §10.1). |
| `dynamic` | The version in use changes by itself: the model keeps learning or adapting automatically during use (online learning, reinforcement learning in operation), or retrained versions go live without a test-and-release step (A22 §1: "continuously and automatically learn and adapt performance during use"). |
| `generative` | Generative AI or LLM: chat assistants, copilots, LLM summarisation or drafting, LLM-based agents, image generation. |
| `probabilistic` | Non-generative ML whose output can differ for identical inputs (stochastic inference). Rare. |
| `non_ml` | Explicitly programmed logic called "AI": fixed rules, scripts, RPA, statistical process control limits, Excel macros. |
| `unclear` | Not enough information. |

## 4. `autonomy`

| Value | Meaning | `human_in_the_loop` (derived) |
|---|---|---|
| `informs` | The AI provides information; a human performs the task and decides. | yes |
| `recommends` | The AI proposes a specific output or decision; a qualified human reviews and approves each output before it takes effect. | yes |
| `acts_with_oversight` | The AI output takes effect automatically; humans monitor, sample or can intervene (human-on-the-loop). | no |
| `acts_autonomously` | The AI output takes effect with no human review of individual outputs. | no |
| `unclear` | Not stated. | unclear |

## 5. Adaptiveness × autonomy grid

A simplified grid inspired by the ISPE GAMP AI concept of adaptiveness and autonomy. The GAMP AI Guide itself is paywalled and **not** in the corpus, so these levels are this project's own operationalisation.

- Adaptiveness: `locked` (static, generative, probabilistic and non_ml models in use) or `adaptive` (dynamic).
- Autonomy: the four levels above.

## 6. Verdict (decided by the rules layer, never by the model)

| Verdict | Rule |
|---|---|
| `out_of_scope` | `in_scope = false` |
| `outside_gmp` | `gmp_relevance = not_gmp` |
| `not_permitted_critical` | `critical` and model is `generative`, `dynamic` or `probabilistic` (draft Annex 22 §1) |
| `needs_more_information` | `gmp_relevance` or `model_type` unclear (or autonomy unclear where it changes the outcome) |
| `not_ai_annex11` | `model_type = non_ml` in a GMP context: Annex 11 applies, Annex 22 does not |
| `annex22_full` | `critical` + `static`: permitted with the full Annex 22 controls |
| `hitl_required` | `non_critical` + `generative` + no human in the loop: not acceptable as described (Annex 22 §1, FDA warning letter 320-26-58) |
| `permitted_with_hitl` | `non_critical` + `generative` + human in the loop |
| `permitted_risk_based` | `non_critical` + `static`, `dynamic` or `probabilistic`: risk-based controls, Annex 22 principles may be applied |

## 6b. Outcome codes and the labels users see
The code is used in data, tests and evaluation reports; the label is what the user sees.
Labels follow one pattern (SME decision 2026-11-22): **what it is: what to do (which rule)**, so the proposer, the builder and the decision-maker all get a plain answer. "Proceed" means "ready for QA review", never "approved". Annex 22 is still a draft; the result page marks draft sources.

| Code | Label shown | Plain answer |
|---|---|---|
| `out_of_scope` | Not assessed: outside this tool's scope | Not assessed |
| `outside_gmp` | Not GMP: proceed under normal IT rules (no Annex 22) | Yes, from a GMP view |
| `not_permitted_critical` | Should not proceed: not for GMP-critical use (Annex 22 §1) | No |
| `needs_more_information` | Pending clarification: update any missing or conflicting details below | Pending clarification (internal shorthand in older docs: "Not yet") |
| `not_ai_annex11` | Not ML: proceed as a standard GMP system (Annex 11) | Yes, not an AI case |
| `annex22_full` | GMP-critical ML: proceed with full controls (Annex 22) | Yes, with conditions |
| `hitl_required` | Not as described: add human review of each output (Annex 22 §1) | No as described |
| `permitted_with_hitl` | Generative AI: proceed if a person approves each output (Annex 22) | Yes, with conditions |
| `permitted_risk_based` | Non-critical ML: proceed with risk-based controls (Annex 11, ICH Q9) | Yes, with conditions |

## 7. Test-case categories

- `clear`: one reading only.
- `borderline`: reasonable people could disagree on one field. The note says which field, and why the label was chosen.
- `out_of_scope`: should be refused.

## Changelog
- **v1.1 (2026-11-21), after the independent review:** the `critical` definition now covers AI output that *provides input to* a GMP decision (it said "performs or decides", which contradicted the task-not-review principle). It also states explicitly that AI-written GMP documents issued without review are GMP records used as such. Test labels T04 and T11 were corrected to match (see `eval/TESTSET_NOTES.md`).

## 6c. Dangerous errors (acceptance criteria, SME decision 2026-11-22)
The tool is judged first on **zero dangerous errors** and on **"when unsure, say unclear"**; accuracy is secondary. An error is dangerous when the tool's outcome is **more permissive** than the correct one. Code: `eval/safety.py`; reported in every evaluation as `dangerous_errors`.

Outcomes from strict to permissive: Should not proceed → Not as described (add human review) → GMP-critical ML, full Annex 22 controls → Generative AI, a person approves each output → Non-critical ML, risk-based controls → Not ML, Annex 11 → Not GMP, normal IT rules → Not assessed. "Not yet" is outside the ranking.

| Correct outcome | Tool says | Dangerous? |
|---|---|---|
| anything | the same | no error |
| anything | Not yet | no (questions always come back) |
| anything | a stricter outcome | no (extra work, not unsafe) |
| Not yet | any "proceed", or Not assessed | **yes** (the open questions are skipped) |
| a real proposal | Not assessed (wrongly refused) | **yes**, except when the correct outcome is Not GMP |
| Not assessed (a question to the tool) | an outcome (wrongly screened) | no |
| anything else | a more permissive outcome | **yes** |

## 6d. Safety guards (after the rules, form input only; SME decision 2026-11-22)
Two deterministic checks in `app/guards.py` can turn an outcome into **"Not yet"**, never into anything else:
- **G1 review not stated:** "what happens with the output" is "Not sure" or blank and "who checks" describes no check, so a human-in-the-loop class cannot be assumed, wherever that changes the outcome. A review step written only in another field still gets the question (accepted: never dangerous).
- **G2 ticks stricter:** the outcome is worked out again with the proposer's ticks. Ticks may only make the outcome stricter: if the model's reading would be a dangerous error against the tick outcome (§6c), the answer is "Not yet" with the contradiction as the question. If the model's reading is stricter, it stands.
Labels in the evaluation sets are the correct outcome for the case; when a form contains such a contradiction, the label is "Not yet" only if the contradiction cannot be settled from the text.

