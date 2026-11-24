# Test set v2: notes

`eval/v2/test_cases.jsonl` holds 70 held-out test cases (T001–T070). Each one is a filled-in intake form (`app/intake_form.py`, form-1.0). The cases were written independently of the classifier and prompts, following draft Annex 22 §6 (test data independence). The only files under `app/` that were read are `app/intake_form.py` and, through the validator, the rules layer. All labels are `label_status: draft`. They need an SME check before they count as verified (A22 §5.3).

Validation: `.venv/Scripts/python scripts/validate_cases.py eval/v2/test_cases.jsonl` gives 70 cases and 0 errors.

## Distribution

### Verdict × category

| Verdict | clear | borderline | out_of_scope | Total |
|---|---|---|---|---|
| out_of_scope | – | – | 10 | 10 |
| outside_gmp | 5 | 2 | – | 7 |
| not_permitted_critical | 4 | 6 | – | 10 |
| needs_more_information | 3 | 4 | – | 7 |
| not_ai_annex11 | 3 | 3 | – | 6 |
| annex22_full | 4 | 4 | – | 8 |
| hitl_required | 0 | 7 | – | 7 |
| permitted_with_hitl | 3 | 5 | – | 8 |
| permitted_risk_based | 3 | 4 | – | 7 |
| **Total** | **25** | **35** | **10** | **70** |

### Chaos tags (cases carrying the tag)

| Tag | n | | Tag | n |
|---|---|---|---|---|
| abbreviation | 45 | | irrelevant_detail | 7 |
| product_name | 30 | | not_sure_everywhere | 3 |
| caps_or_lowercase | 20 | | rambling | 3 |
| missing_answers | 13 | | typo | 3 |
| contradiction | 10 | | no_punctuation | 3 |
| vague | 9 | | two_use_cases | 3 |
| very_short | 9 | | very_long | 2 |
| danish_words | 8 | | wrong_field | 2 |

49 of 70 cases carry two or more tags. `abbreviation` is tagged generously, for any domain abbreviation a classifier has to resolve (CDS, EM, MBR, CAPA, SUB, IPC and so on).

### Scenario spread (form `areas`, multi-select)

qa 24 · manufacturing 23 · qc_lab 12 · business 8 · msat 8 · supply_chain 7 · engineering 5 · regulatory 2. Suppliers: cloud service 31, vendor-installed 14, in-house 12, not sure 3 (out-of-scope forms are mostly blank). Products named include ChatGPT, Copilot / Copilot Studio (misspelt "copliot" in T039), Gemini, Claude, Azure OpenAI and GPT-4o, plus vendor "AI features" and in-house models.

## How the cases were written

1. **Sources first.** I read the labelling guide (§2–§6 and the priority order of the rules), the form, the validator, draft Annex 22 in full, the FDA warning letter 320-26-58 (AI section), draft Chapter 4 §4.23–4.25, the draft Annex 11 section list, and AI Act Art. 4, 50 and Annex III. I read the old dev and test sets only to avoid repeating their scenarios (camera vial inspection, GPT result extraction, RL bioreactor, colony counter, CDS peak integration, client-portal chatbot and so on are not reused).
2. **Verdict quota first, then scenarios.** Each verdict has at least 5 cases. They are spread over upstream (seed train, bioreactor feed), downstream (pooling, PCC capture, resin), fill-finish (CCI, label OCR, line clearance, gowning, label text), QC (MFI, OOS, audit trail, HPLC columns, stability code, CDS upgrade), micro/EM (excursions, isolate trending, EMS alarms), QA (release, change control, CAPA, deviations, KPIs, self-inspection, eDMS), MSAT/validation, engineering (calibration, utilities, SU bag testing), supply chain (supplier ASL, warehouse, purchasing), RA, training, and business (finance, HR, legal, sales, marketing, IT).
3. **Forms filled the way busy people fill them.** Many answers are short, lower-case or full of jargon. Some fields are blank. Some forms ramble about budget, demos or a colleague's opinion. 10 forms contradict themselves: a choice says one thing and the free text another (T009, T012, T017, T020, T025, T029, T036, T043, T051, T056). In those cases the free text that describes the real flow decides the label. 3 forms mix two use cases (T040, T046, T055), and only the main subject is labelled. 2 forms put the process description in "who checks" (T034, T067).
4. **Labelling rules applied.**
   - Criticality follows the task, not the review (guide §2). So a proposed QP conclusion (T001), a change classification (T021), an OOS invalidation (T060) and an audit-trail pre-filter (T061) are critical even with a human sign-off.
   - Missing information that would change the outcome becomes `unclear` (T004, T014, T023, T031, T040, T048, T054).
   - Missing information that would not change the outcome is labelled, with the reason given. T050: outside_gmp has priority over an unclear model. T057: autonomy does not matter for non_critical + static.
5. **Self-assessment bias is built in.** Several proposers tick "no GMP impact" because a person signs (T001, T021, T060, T061), or tick a model type the vendor's marketing suggests (T020, T043). The expected labels follow the description, not the tick.

## Borderline cases

| Id | Scenario | Verdict | Contested field | Alternative reading → outcome |
|---|---|---|---|---|
| T001 | Gemini release summary with YES/NO for QP | not_permitted_critical | gmp_relevance | fact collation only → permitted_with_hitl |
| T005 | Copilot KPI narrative for management review, unreviewed | hitl_required | gmp_relevance | office report → outside_gmp |
| T012 | ML sets calibration due dates in CMMS | annex22_full | gmp_relevance | maintenance planning → permitted_risk_based |
| T014 | Bioreactor feed "AI", vendor info conflicting | needs_more_information | model_type | static → annex22_full / dynamic → not_permitted_critical |
| T015 | EMS "AI smart alarm" that is configured rules | not_ai_annex11 | model_type | vendor_unknown → needs_more_information |
| T016 | Claude for root-cause brainstorming | permitted_with_hitl | gmp_relevance | input to deviation outcome → not_permitted_critical |
| T017 | Weekly TT status mail auto-sent to client | hitl_required | autonomy | tick "person approves" → permitted_with_hitl |
| T020 | CPV Nelson-rule script ticked "trained model" | not_ai_annex11 | model_type | static → annex22_full |
| T021 | LLM proposes change classification and notification | not_permitted_critical | gmp_relevance | reviewed draft → permitted_with_hitl |
| T022 | Copilot reviews MSAs (quality agreement excluded) | outside_gmp | gmp_relevance | outsourcing context → permitted_with_hitl |
| T023 | ChatGPT complaint response letters, review unknown | needs_more_information | autonomy | handler obviously sends → permitted_with_hitl |
| T026 | Fine-tuned BERT proposes deviation class | annex22_full | model_type | "language model" = generative → not_permitted_critical |
| T027 | Gemini regulatory-intelligence newsletter | permitted_with_hitl | gmp_relevance | public news → outside_gmp |
| T029 | LLM writes eDMS metadata automatically | hitl_required | gmp_relevance | GMP-record integrity → not_permitted_critical |
| T031 | Copilot "analyse process data", use undefined | needs_more_information | gmp_relevance | exploratory support → permitted_with_hitl |
| T032 | Label OCR "AI", vendor says fixed per version | annex22_full | model_type | details unknown → needs_more_information |
| T034 | Stochastic cell counter for seed-train IPC | not_permitted_critical | model_type | measurement uncertainty, static → annex22_full |
| T035 | Operator performance score from MES data | outside_gmp | gmp_relevance | training/coaching → permitted_risk_based |
| T036 | Claude drafts PQ reports, ticked "auto" | permitted_with_hitl | autonomy | tick → hitl_required |
| T038 | Gemini grades aseptic theory test, pass/fail to LMS | not_permitted_critical | gmp_relevance | training support → hitl_required |
| T041 | Copilot Studio auto-answers Ask QA mailbox | hitl_required | autonomy | requester decides (informs) → permitted_with_hitl |
| T042 | Gowning camera locks grade B door | annex22_full | gmp_relevance | extra aid → permitted_risk_based |
| T043 | "AI" dispensing booth that is configured rules | not_ai_annex11 | model_type | tick static → annex22_full |
| T044 | EM isolate clustering dashboard | permitted_risk_based | gmp_relevance | drives investigations → annex22_full |
| T046 | Tier-1 meeting notes auto-posted (+ logbook idea) | hitl_required | gmp_relevance | office notes → outside_gmp |
| T047 | Gemini writes R code for shelf-life, then validated | permitted_with_hitl | gmp_relevance | code computes GMP result → not_permitted_critical |
| T048 | LLM agent chases suppliers, review undecided | needs_more_information | autonomy | admin → outside_gmp |
| T052 | Bayesian NN for resin purchasing | permitted_risk_based | model_type | static (same outcome) |
| T055 | AI-avatar GMP training videos (+ canteen bot) | permitted_with_hitl | gmp_relevance | label the canteen bot → outside_gmp |
| T056 | Agent submits client audit questionnaires | hitl_required | autonomy | tick "Head of QA approves" → permitted_with_hitl |
| T057 | Static harvest-timing model, use undefined | permitted_risk_based | autonomy | treat unknown autonomy as gap → needs_more_information |
| T059 | Self-optimising lyo cycle | not_permitted_critical | model_type | vendor release = static → annex22_full |
| T061 | LLM pre-filters CDS audit trail for reviewer | not_permitted_critical | gmp_relevance | summary aid → permitted_with_hitl |
| T065 | LLM "GMP tip of the week" on floor screens | hitl_required | gmp_relevance | internal comms → outside_gmp |
| T067 | Vision model updates WMS stock and locations | permitted_risk_based | gmp_relevance | traceability records → annex22_full |

Contested fields: gmp_relevance 19, model_type 9, autonomy 7. Out-of-scope cases T011, T028, T068 and T070 also set `contested_field: in_scope`, because each one mentions a real AI use but asks for legal advice, a compliance statement or the task itself.

## Labels I am least sure about

1. **T042 (gowning camera → annex22_full).** Whether a camera that replaces the mirror self-check is a "critical" contamination control or an extra aid is a QA judgment call. If SMEs call it non_critical, the outcome becomes permitted_risk_based.
2. **T012 (calibration intervals → annex22_full).** The model sets intervals directly, which led me to critical. A site that sees calibration-interval setting as a QRM planning activity reviewed by metrology could reasonably say non_critical.
3. **T047 (LLM-written R code → permitted_with_hitl).** It rests on "the LLM output is code that gets validated, not a GMP result". The guide has no example for code generation, so this needs an SME decision and possibly a line in the guide.
4. **T041 (Ask QA auto-replies → hitl_required).** Is a bot answering a human requester "informs" or "acts autonomously"? I chose autonomous because it replies as the QA function and QA never sees the answer. The same logic would apply to other answer bots, so the guide should state it.
5. **T034 (stochastic cell counter → not_permitted_critical).** It applies A22 §1's "probabilistic output" literally to an analytical instrument whose variation the vendor calls within ±3%. An SME may see this as ordinary measurement uncertainty (static → annex22_full).
6. **T065, T046 and T005 (non_critical vs not_gmp for floor screens, meeting notes and the KPI narrative).** The line between "GMP context, non-critical" and "office productivity" is the weakest boundary in the guide. All three are labelled non_critical, so a classifier that says outside_gmp will be scored wrong.
7. **T038 (LLM grading of aseptic theory tests → critical).** This depends on treating the pass/fail as a GMP record used as such. If it is non_critical, the outcome is hitl_required. Both outcomes are "not acceptable as described", so the user-facing risk is small.
8. **T057 (unknown autonomy, non_critical static → permitted_risk_based).** This is correct by the rule table (§6), but it tests a subtle rule. A classifier that returns needs_more_information is arguably being sensibly cautious.
9. **T067 (warehouse vision → non_critical).** Automatically written bin locations are close to GMP traceability data. The case rests on material status staying with QA.

## Suggested follow-ups (not done here)

- An SME review of the 35 borderline labels. After that, set `label_status` to verified per case.
- Add examples to the labelling guide for code generation (T047), answer bots replying on behalf of a function (T041), and "GMP context vs office productivity" (T005, T046, T065).
