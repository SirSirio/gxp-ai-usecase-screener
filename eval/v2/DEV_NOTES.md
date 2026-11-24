# Dev set v2: notes on the form conversion

`eval/v2/dev_cases.jsonl`: 40 cases, `D001`–`D040`, written as filled-in intake forms (`app/intake_form.py`, form-1.0). `D001`–`D010` come from `eval/devset.jsonl` (D01–D10) and `D011`–`D040` from the former test set `eval/testset.jsonl` (T01–T30). The `origin` field gives the source id. Validated with `scripts/validate_cases.py`: 0 errors.

## How the cases were converted
- **Labels copied unchanged.** `expected`, `key_sources`, `rationale`, `contested_field`, `category` and `label_status` (plus `review_note` for T04 and T11) are copied from the source file by a script, not retyped.
- **Facts spread over the fields.** The task goes in `what`. The review flow goes in `who_checks` and `output_use`, the model description in `ai_type.explain`, and the supplier in `source`. Where the original says nothing (often the supplier, sometimes who checks), the field is left empty or set to `not_sure`, or `who_checks` says "not decided yet".
- **No label-relevant facts added.** The only new content is irrelevant detail that does not change any label (D011: shift pattern and planned date; D039: when the sensors were installed). D003 deliberately leaves `who_checks` empty rather than adding "QP certifies afterwards", which would pull the autonomy reading.
- **The unclear cases stay unclear.** D029 (T19) is `not_sure` in every choice. D035 (T25) has `output_use = not_sure` and `who_checks = "not decided yet"`, so autonomy is still unstated.
- **Out-of-scope cases (8).** The question goes in `what` (and sometimes `title`) and the rest is empty. D019 (T09) also ticks QA and LLM ("Copilot"), and D010 ticks personal data, as real users would.
- **Chaos:** abbreviations (EBR, MBR, CDS, LIMS, DMS, TT, PFS, RL, DCS, BD, CRM), lower case, typos (excipents, assesment, aplicant, bioractors, thru), Danish words (afvigelse, batchjournal), facts in the wrong field, and missing answers.

## Label changes
None.

## Cases with `contradiction` (10)
In each of these, the ticked choice disagrees with the free text. The label follows what the free text says actually happens.

| Case | Origin | Choice ticked | What the free text says | Label kept |
|---|---|---|---|---|
| D008 | D08 | output_use = informs | answers go out directly, nobody in between | acts_autonomously |
| D013 | T03 | gmp_impact = no ("just copying numbers") | writes QC results into LIMS, which flow onto the CoA | critical |
| D014 | T04 | gmp_impact = no ("it's documentation") | specs, SOPs and MBRs are published to the DMS without review | critical |
| D020 | T10 | output_use = person_approves ("operators go through it") | pushed into the LMS, no trainer in between | acts_autonomously |
| D021 | T11 | output_use = person_approves | good syringes go straight to packaging; only flagged ones see a person | acts_autonomously |
| D023 | T13 | gmp_impact = yes ("runs on the GMP floor") | banner only, validated alarms unchanged | non_critical |
| D026 | T16 | ai_type = self_learning (nightly candidate retrain) | a new version goes live only after re-test and QA change approval | static |
| D032 | T22 | ai_type = trained_fixed ("AI-powered per vendor") | checks against limits and rules we configure | unclear (was non_ml; changed at SME review) |
| D034 | T24 | ai_type = trained_fixed | the prediction comes from sampling; two runs give different numbers | probabilistic |
| D038 | T28 | output_use = person_approves ("QA gets it") | the finished report is e-mailed automatically | acts_autonomously |

## Points I am unsure about
- **Held-out data policy.** 30 of the 40 cases are the former held-out test set. Once they are dev data, they must not be used as an independent test again. The v2 test set has to be written separately, without reusing these cases.
- **D034 (T24)** is a soft contradiction. "Trained prediction model" is a natural pick for a user, and the option text does not say "deterministic". The case relies on the explanation text to reach `probabilistic`.
- **D026 (T16)** puts the model-release process in `who_checks` (tagged `wrong_field`). A classifier reading only `output_use = auto_unchecked` might mistake it for a check of individual outputs. The label stays `acts_autonomously`.
- **D021 (T11)** has an inspector review in `who_checks` that is real but covers only the rejected units. The label stays `acts_autonomously` per the earlier review note, and this remains the hardest autonomy case.
- **D016 (T06)** ticks manufacturing and QC lab as areas (the jobs are on the GMP floor), which pulls towards GMP. The label stays `not_gmp`.
- **D022 (T12)** has `who_checks = "n/a, its for look-ups"`. I avoided writing "nobody checks the answers", which could push towards `hitl_required`.

## SME review, 2026-11-22
Export: `eval/v2/reviews/dev_review_2026-11-22.json` (40 of 40 dev cases), applied with `scripts/apply_review.py`.
- **39 approved** → `label_status = sme_approved`.
- **D010 rewritten** (SME request): same request, but every question is now ticked as if it were a proposal (LLM, a person approves, personal data). The task box still asks the tool to do the job itself, so the label stays `out_of_scope`. It tests that filled-in ticks do not turn a request into an assessment. `label_status = revised_after_review` (SME to confirm).
- **D041 added**, sibling of D010: the same task worded as a proposal ("I want to use ChatGPT to…"). That is a real use case, but not GMP → `outside_gmp`. `label_status = draft` (SME to confirm).
- **D040 removed** (SME request): the weather question was too trivial to teach anything; D009 and D010 still cover out-of-scope requests. The id is not reused.
- **D042 added** (SME request), ML sibling of D007: the same routing done by a model trained on past records → static, non-critical → `permitted_risk_based`. Pair with D007: only the type of AI changes. `label_status = draft` (SME to confirm).
- **D032 changed** (SME decision) from `not_ai_annex11` to `needs_more_information` (`model_type = unclear`). Batch-record review by exception is GMP-critical, and every unflagged step is accepted without QA reading it; whether the module is rules or a trained model is known only from a demo and the vendor's spec, so the vendor must document it first. `label_status = sme_rewritten`.
- Dev set after the review: **41 cases** (D001–D042 without D040).
- **D029 changed** (SME decision, error analysis W27) from `needs_more_information` to `out_of_scope`: no use is proposed (every answer "not sure", the text asks the tool for general advice). SME principle: no proposal described, no assessment. `label_status = sme_rewritten`.
- **D038 changed** (2026-11-22, form-1.2): non_critical / hitl_required → critical / not_permitted_critical. The EM trend report is the GMP record QA trends and reviews; AI-written and sent without review, it is a GMP record used as such (CH4D 4.24). Claude's judgment under the new definition of "direct", agreed by the SME. Both outcomes were a "no", so no permissive change.
