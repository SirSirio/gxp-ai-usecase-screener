# Validation note: GxP AI Use-Case Assistant

*Validation thinking applied to the tool itself. Reference frame: EU GMP draft Annex 22 (July 2025), Annex 11, ICH Q9(R1), FDA warning letter 320-26-58. Portfolio context: public documents only, synthetic cases, not a validated system in a regulated company. State as of 2026-11-22, commit `0f9f242` (prompt-1.3, rules-1.3).*

**1. Intended use and its limits** *(Annex 22 §3.1)*
First-pass screening of *proposed* AI use cases. The proposer fills in a structured intake form (9 questions in `form-1.0`, the version the test set was run on; 10 in the current `form-1.2`). The tool classifies GMP relevance, model type and autonomy; cites the passages behind each judgment; derives the outcome and the required controls from fixed rules; asks questions where information is missing; and drafts an intake record for QA. **Users:** proposers, the people who build AI tools, QA reviewers. **Not intended for:** legal advice, final compliance decisions, assessing a deployed system's validation status, or company-internal documents. **Not a proposal, no assessment:** requests to the tool itself and descriptions with no concrete use are answered "Not assessed". A hidden quick mode (one free-text box) exists; it is less accurate and not covered by this note's form results.

**2. Risk level** *(ICH Q9(R1) §4.3; Annex 22 §2.3)*
Low. The tool informs a human decision: every output is a draft for QA review, and nothing is executed automatically. **Main failure mode: a dangerous error**, i.e. an outcome more permissive than the correct one, so a proposer could go ahead without a required "no", question or control. Mitigations:
- the outcome comes from a deterministic rules layer, never from the model;
- **safety guards** after the rules (`app/guards.py`) can only turn an outcome into "Not yet": G1, a review step that is not described cannot be assumed; G2, the proposer's ticks can only make the outcome stricter, and a contradiction in the permissive direction becomes a question;
- every judgment shows its source passage; unsupported claims are dropped;
- invalid model output is rejected and logged, never shown.

By its own rules the tool classifies itself as *non-critical, generative, a person approves each output*.

**3. Evaluation data** *(Annex 22 §4–§7)*
- **Cases as filled-in forms**, with realistic mess (typos, abbreviations, Danish words, product names, wrong field, contradictions between ticks and text). **Dev: 41 cases. Test: 70 held-out cases**, 35 borderline, every outcome at least 6 times.
- **Independence** (§6): test cases written by a separate AI agent from the label guide and the sources. Prompt and rules were tuned on dev only. The test set was run **once**, on a frozen, committed version, and only aggregates were looked at. Test labels were pre-reviewed by a fresh agent that knew nothing of the tuning and reported counts only to the developer.
- **Label quality** (§5.3): **all 70 test labels are SME-verified**: 67 approved (20 marked borderline), 3 rewritten by SME decision (`eval/v2/reviews/`). Dev: 36 approved and 2 rewritten by the SME; 3 cases were written at the SME's request (one rewrite, two new siblings) and still await the SME's confirmation; 1 trivial case was removed. The SME's principles are recorded in `docs/LABELING_GUIDE.md` and `eval/v2/DEV_NOTES.md`.
- **Generated test data** (§5.6): Annex 22 says AI-generated test data is "not recommended and any use hereof should be fully justified". Justification: no company data may be used, and no public set of labelled AI intake cases exists. Mitigation: SME verification of every label, independent pre-review, and a baseline to compare against.

**4. Acceptance criteria and results** *(Annex 22 §4.2; SME decision D19)*
The tool is judged first on **zero dangerous errors** and **"when unsure, say unclear"**; accuracy is secondary. The rule for "dangerous" was decided by the SME case by case (guide §6c, `app/safety.py`, tested in `tests/test_safety.py`): "Not yet" is never dangerous because questions come back; skipping a needed "Not yet" is; refusing a real proposal is, unless it is outside GMP; a stricter answer is not.

| Held-out test set (70) | Criterion | Gemini 3.5 Flash-Lite, prompt-1.3 + guards | Keyword baseline (checklist) |
|---|---|---|---|
| **Dangerous errors** | **0** | **0 ✓** | 13 ✗ |
| of which on GMP-critical cases | 0 | 0 ✓ | 9 ✗ |
| Real proposals wrongly refused | 0 | 0 ✓ | 2 ✗ |
| Valid answers shown | 100 % | 100 % ✓ | 100 % ✓ |
| Verdict accuracy (secondary) | – | 87 % (clear 92 %, borderline 80 %) | 59 % |
| Out-of-scope refusal precision / recall | – | 100 % / 100 % | – / 36 % |
| Primary source retrieved | ≥ 90 % | 100 % ✓ | – |
| Citations kept after the check | – | 98.5 % | 100 % |

- All 9 remaining errors are on the safe side ("stricter or Not yet").
- **Statistical caution:** 0 dangerous errors in 70 cases still allows a true rate of up to about 4 % (rule of three).
- **Consistency:** two full dev runs gave the same final outcome in 40 of 41 cases. Asking the model twice and comparing showed no gain (D21), so it is not built.
- **Contradiction cases** (ticks contradict the description), dev: Gemini 8/10 correct before the guards, the checklist baseline 1/10. This is the main reason for the LLM over a checklist.
- **No-decrease principle** (§4.3): the process it replaces is ad-hoc email triage with no measured accuracy. Before production, measure a sample of human first-pass triage on the same set.

**How the result was reached (dev only):** prompt 1.2 → 1.3 (one call per case, structured form fields, three prompt fixes); error analysis by cause for each dangerous dev error (model, prompt, input or label); two labels corrected by the SME; then the two guards instead of stronger prompt wording, because an instruction the model already ignored once is not a reliable control. Dev after the guards: 0 dangerous errors live, accuracy 88 %. Full record: `docs/WORKLOG.md` W21–W31, decisions D18–D21.

**4b. Changes after the test run (not yet re-tested on the test set)**
The test result above is for form-1.0, prompt-1.3, rules-1.3. Since then: follow-up rounds after "Not yet" (max 3); contradictions explained to the proposer (rules-1.4, outcomes unchanged); form-1.2 from a review of every question against the regulatory texts (D22: a "not GMP" answer, "directly" covers unchecked items and GMP records, a probabilistic option, a new question on replaced checks); prompt-1.5. A dev run on form-1.2 found one dangerous error (D038: a proposer's "a person approves" tick believed although "who checks" only says the report is received). Guard G1b (rules-1.5, D23) now treats receiving as no check; the next dev run had 0 dangerous errors (accuracy 83 %), and G1b caught one case live (D020). Citations (W46, D24): the support check passed almost every paragraph (14 wrong citations of 116 kept on dev); a source map (map-1.1, reviewed against the whole corpus and confirmed by the SME) now decides which paragraphs may back each answer, and prompt-1.6 names them. Dev: citations in the map 96 %, known-wrong citations 14 → 1, 0 dangerous errors. Later (W48–W60): a total deadline per LLM request; the feature check before the freeze (32 checks, all fail/flag items fixed); prompt-1.7 decides frozen vs self-learning by the version in use (D25); every classification source now defines its class and every outcome source states the consequence, checked by an independent reviewer agent (D26, map-1.3, rules-1.10, prompt-1.9); plain-language page texts (the classifier's inputs unchanged). The system was **frozen on 2026-11-24 (tag `v1.0-freeze`)** for a new held-out test run; under change control (section 8) that run is reported as a re-use of the test set, and answers lost to provider errors are re-run on the same frozen version and counted.

**5. Known limits** (not measurable without real users)
- The same people wrote the cases and the rules, so shared blind spots appear in both. An independent reviewer or real proposals would test this.
- Synthetic inputs imitate real mess but cannot cover it.
- The provider can update the model; the exact model version is logged with every answer, and a change counts as a change to the system (section 8).
- The guards add "Not yet" answers; the share of "Not yet" must stay low enough for the tool to be useful. Planned: a follow-up step where the proposer answers the questions and resubmits (max 2–3 rounds).

**6. Human review step** *(Annex 22 §3.3, §10.5)*
Every result is a draft (`draft_for_qa_review`). QA confirms or corrects the classification and outcome and owns the decision. Corrections should be recorded and fed back as new cases. How often QA overrides the tool should be monitored (not yet implemented).

**7. Audit trail** *(Annex 11 §9; draft Annex 11 §12)*
Every request is logged: the form answers, the input text and its hash, retrieved chunk ids, raw model output, validation errors, outcome, rule id (including guard ids G1/G2), cited chunks, and the provider, model, prompt, rules, corpus and app versions. The log is append-only and hash-chained (tampering is detected, tested). Rejected outputs are logged too. Evaluation runs log to a separate file. Production gap: user identity (needs a login) and write-once storage.

**8. Change control** *(Annex 22 §10.1–§10.2; draft Annex 11 §3.1)*

| Change | Control |
|---|---|
| Prompt | Bump `PROMPT_VERSION`, re-run dev; any new test run is reported as a re-use of the test set |
| Model or provider | Same; a model version change counts as a change even when the prompt is unchanged |
| Rules, guards or controls | Code review against the label guide; tests per rule and guard; labels re-checked if definitions change |
| Corpus (new or updated document) | Hash check fails → re-parse, check section tests, rebuild index (new `corpus_version`); the source map is pinned to the corpus, so a test fails until the map is re-reviewed against the new paragraphs and confirmed by the SME (new `source_map_version`); re-run evals |
| Source map (which paragraphs back each answer, D24) | Review against the paragraph texts; SME confirmation; tests per answer; re-run dev and compare the citation metrics |
| Final Annex 22 published | Treat as a corpus change, a source-map change **and** a rules change; re-label affected cases |
| A dangerous error found later | Record it as a test failure with root cause; fix; add the case to dev as a regression case; fresh cases for new evidence |

Configuration control: everything is in git, and every result records the versions it was produced with.

**Data use by the LLM provider.** Only public regulatory texts and the proposer's answers are sent. For users in the EEA, Google applies its paid-tier data terms (no use for product improvement) also to the free tier. The answers must not contain confidential information (to be stated on the form in a production version); in a company, a paid or company-tenant service would be used.

**9. Open items before any real use**
Identity and durable audit storage · monitoring of QA overrides and of the "Not yet" share · an independent second reviewer for labels · periodic review when the final Annex 22, Annex 11 and Chapter 4 are published.

*Lessons from FDA warning letter 320-26-58 built into the design:* the tool never presents AI output as final; it requires quality-unit review of AI-drafted GMP content as a control (QU_REVIEW); and it does not rely on the model to identify regulatory requirements: they come from cited source text and fixed rules.
