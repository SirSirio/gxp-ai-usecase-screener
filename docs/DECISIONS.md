# Decisions

One entry per design choice: what was chosen, what else was possible, and why. Newest last.

---

### D1. The rules layer decides; the model only classifies and explains
- **Chosen:** a deterministic rule table (`app/rules.py`, R0–R9) turns the classification into the verdict and the required controls.
- **Alternatives:** let the LLM write the verdict; let the LLM pick controls.
- **Why:** a verdict like "not permitted" must be reproducible, testable and reviewable line by line by QA. A model can misread a use case, but it cannot override a rule. Each verdict carries a rule id, which is shown to the user and written to the audit log. When the final Annex 22 text is published, updating the table is a reviewed code change, with a test per rule, instead of a prompt tweak.

### D2. Criticality is about the task, not about human review
- **Chosen:** `gmp_relevance` describes the task the AI does. Human review is a separate field (`autonomy`).
- **Why:** draft Annex 22 §1 excludes generative and dynamic models from critical GMP applications outright. It does not say "unless a human checks". §3.3 and §10.5 discuss human-in-the-loop for *static* models in critical use, so oversight and criticality are separate axes in the text itself. Merging them would let "an LLM classifies deviations, QA confirms" slip through as acceptable. The rule test `critical + generative + recommends → not_permitted_critical` pins this.

### D3. Section-aware parsing, with each document's own section ids
- **Chosen:** a parser per document type (numbered / explicit headings / articles). It drops EC line numbers, re-attaches numbers printed on their own line, and accepts a number as a new section only if it can follow the current one.
- **Alternatives:** fixed-size chunks by page or character count (the default in most RAG tutorials).
- **Why:** a citation like "Annex 22 §3.3 Human-in-the-loop" is something a QA reviewer can open and check; "page 3, characters 1200–2300" is not. Chunks never cross a section boundary, so every chunk id names exactly one section. The plausibility rule stops dates ("30 June 2011") and wrapped numbers becoming headings. Tests pin the section lists.

### D4. Hybrid retrieval (TF-IDF + dense) fused with reciprocal rank fusion
- **Chosen:** TF-IDF on words and word pairs, plus `BAAI/bge-small-en-v1.5` embeddings in FAISS, combined with RRF (k = 60).
- **Alternatives:** dense only; sparse only; a cross-encoder re-ranker; Azure AI Search.
- **Why:** regulatory text mixes exact terms ("Annex 11", "audit trail") that sparse retrieval matches well with paraphrase ("ChatGPT drafts our SOPs" → "Generative AI and Large Language Models") that dense retrieval matches well. RRF uses only ranks, so the two score scales never need calibrating. The embedding model runs locally on CPU: no key, no cost, no data leaving the machine. At 582 chunks a flat FAISS index is exact and instant; Azure AI Search would only be needed at a much larger scale.

### D5. Fixed "framework queries" alongside the user's text
- **Chosen:** every request also runs seven fixed queries (Annex 22 scope, generative AI, dynamic models, human-in-the-loop, quality-unit review, CSV / risk, AI Act).
- **Why:** proposers write in business language, and the passages that decide a case (Annex 22 §1) rarely match that wording. The queries are generic, not tuned to individual cases.
- **Measured (ablation, offline assessor):**

  | | primary source retrieved | all key sources retrieved |
  |---|---|---|
  | dev, without → with | 0.875 → 1.00 | 0.44 → 0.56 |
  | test, without → with | 0.75 → 0.79 | 0.51 → 0.59 |

  The "without" numbers already include sections the offline assessor fetched with `get_section`, so the gain from the queries alone is modest. Retrieval of secondary sources (≈ 0.6) is the weakest metric and the next thing to improve, e.g. with a cross-encoder re-ranker or a query rewritten by the LLM. The verdict accuracy of the keyword baseline does not change, because it does not read passages; for an LLM, retrieval matters directly.

### D6. Citation check with two signals
- **Chosen:** a cited chunk is kept only if (a) it was actually retrieved or fetched in this request, and (b) it supports the claim, by dense similarity ≥ 0.55 or word overlap ≥ 0.30, measured against the regulatory meaning of the classified value. If nothing survives, the judgment is marked "Not covered by the sources."
- **Limitation, stated honestly:** the check verifies that the passage is *about* the asserted category. It does not verify every word of the model's free-text rationale. An LLM-as-judge check on rationales would be the next step (it costs a model call per judgment).

### D7. Schema-forced output, validated with Pydantic, rejected if invalid
- **Chosen:** one Pydantic model (`ModelAssessment`) generates the JSON schema sent to the provider *and* validates the reply. Extra fields are forbidden (the model cannot slip in a "verdict"), enum values must match the label guide, and judgments must agree with the classification. Invalid output gets one retry; after that it is logged as `assessment_rejected` and never shown.
- **Why:** "the model usually returns valid JSON" is not good enough for a GxP tool. Schema-valid rate is a reported metric.

### D8. Provider-neutral `ChatClient`; plain HTTPS instead of vendor SDKs
- **Chosen:** a small interface (`chat(messages, tools, json_schema)`) with Gemini and Azure OpenAI implementations over `httpx`, plus a scripted `FakeChatClient` for tests.
- **Why:** the spec requires swapping providers. Corporate Microsoft shops will want Azure OpenAI / AI Foundry, and a personal demo is cheapest on Gemini. Two-phase calls (tools first, then a schema-forced answer without tools) work on both, because some APIs reject function calling and JSON mode in the same request. **Not yet run against live endpoints** (no key in the build environment).

### D9. Offline keyword baseline as a first-class assessor
- **Chosen:** a deterministic keyword classifier behind the same interface as the LLM.
- **Why:** (1) the whole pipeline, UI and evaluation run without any key; (2) it gives the LLM a floor to beat. If an LLM cannot beat keywords on the held-out set, it is not worth its cost and risk.

### D10. Test-set independence (Annex 22 §6 applied to the tool itself)
- **Chosen:** an independent agent wrote the 30-case test set and a 10-case dev set from the label guide and the sources, without seeing the code. The developer tunes only on the dev set; the test-set run prints aggregates only.
- **Evidence it matters:** the keyword baseline scored **0.90 verdict accuracy on dev but 0.60 on the held-out test set** (0.57 after the label corrections in D16). That gap is what overfitting looks like, and it would have been invisible without a held-out set.
- **Limit:** labels are drafts by one agent. They must be reviewed by a process SME before the test set counts as validation evidence (Annex 22 §5.3 asks for independently verified labels).

### D11. Hash-chained audit trail
- **Chosen:** append-only JSON Lines where each record stores the previous record's SHA-256. `verify()` recomputes the chain.
- **Why:** it records what was asked (user identity needs a login: production gap), which passages were retrieved, which prompt/model/rules/corpus versions answered, and the raw model output. Editing or deleting a single line is detectable (tested); rewriting the whole file or cutting records off its end is not, without an external anchor or write-once storage. This is ALCOA+ applied to the tool's own records. In production the log would go to write-once storage.

### D12. Versions everywhere
- **Chosen:** `corpus_version` (hash of all chunks), `prompt_version`, `rules_version`, `app_version` and the git commit are written into every result, audit record and evaluation run. Source PDFs are pinned by SHA-256 in `scripts/download_sources.py`.
- **Why:** change control. Any answer can be traced to the exact inputs that produced it, and a changed source file is detected rather than silently absorbed.

### D13. Simplified adaptiveness × autonomy grid
- **Chosen:** 2 adaptiveness levels (locked / adaptive) × 4 autonomy levels, defined in `docs/LABELING_GUIDE.md`.
- **Why:** the ISPE GAMP AI Guide is paywalled and not in the corpus. Rather than quote it from memory, the tool shows a grid "inspired by" its concept and says the levels are this project's own.

### D14. Public documents only, raw files not committed
- **Chosen:** sources are downloaded by script and hash-checked; `data/raw/` is git-ignored. fda.gov needs browser-like request headers.
- **Why:** reproducibility without redistributing the documents, and a strict line that no company data enters the tool.

### D15. AI Act: selected articles only
- **Chosen:** Articles 1–6, 9–15, 26 and 50.
- **Why:** the full Act (144 pages, mostly recitals and governance) would dominate retrieval for a manufacturing-focused tool. The selection covers scope, definitions, AI literacy, prohibited practices, high-risk classification and requirements, deployer duties and transparency.

### D16. Independent review of rules, controls and labels (rules-1.1, prompt-1.1)
- **What:** a separate reviewer agent, briefed as a GxP/CSV reviewer, checked the rule table, the controls and the labels against the source texts. It found no wrong rule. It confirmed the reading behind R2: a human in the loop does not make generative AI acceptable in critical use, because the Annex 22 §1 human-in-the-loop allowance is given for non-critical use only.
- **Changes applied** (each claim checked against the source text first):
  - Guide: `critical` now includes output that *provides input to* a GMP decision. AI-written GMP documents issued without review count as GMP records used as such. Test labels T04 and T11 were corrected; three borderline labels are left for the SME (`eval/TESTSET_NOTES.md`).
  - Wording: "qualified person" → "personnel with adequate qualification and training" (in EU GMP, "Qualified Person" means the QP). Verdict labels say "acceptable / not acceptable under draft Annex 22 §1" rather than "permitted", because the draft says "should not". R2 notes it is a reading of the EU draft, since FDA scales risk by model influence. R6 no longer overstates the warning letter.
  - Controls: new DATA_INTEGRITY (draft Annex 11 §2.4, §4.5; Chapter 4 §4.24), SECURITY (§15.1) and PERIODIC_REVIEW (§14.1). SUPPLIER now covers hosted-model version releases (§7.5) and is added to more verdicts. QU_REVIEW is no longer required for look-up assistants that produce no GMP content. DYNAMIC_LIFECYCLE no longer cites FDA guidance whose scope excludes internal planning tools. AI_ACT now cites Art. 26 and the newly ingested **Annex III** (high-risk list, e.g. recruitment).
- **Effect on the baseline:** test verdict accuracy fell from 0.60 to 0.57, because the corrected T04 is a case keywords cannot get right. The baseline was deliberately not re-tuned.
- **Independence note:** the reviewer read the test set, and its report named some test cases. Label review is part of label verification (Annex 22 §5.3), not tuning. The offline classifier was not changed after the review.

### D17. Abbreviation expansion and per-rule quote hints (user feedback)
- **Trigger:** a user typed "Static ML to score fermentation …" and got "More information needed": the keyword baseline did not know "static" or the bare abbreviation "ML". The shown quote was also the wrong sentence of Annex 22 §1 (the generative-AI sentence instead of the scope sentence).
- **Abbreviations:** the offline classifier now appends the full form of known abbreviations before matching (ML, DL, LLM, GenAI, RPA, SPC, IPC, RTRT, PAT, MBR, EBR, OOS, CQA, CPP …). Matching is case-sensitive, so "ML" is machine learning but "mL" (millilitre) is not. "static" and "deep learning" were added as static-model cues.
- **Quote hints:** each rule names the words of the exact source sentence it rests on (`Rule.quote_hint`). The quote shown is the sentence that best matches the hint, not the one that happens to share words with the explanation. A test pins the quote for four rules.
- **Effect on the evaluation:** none on either set (dev 0.90, test 0.57). The remaining baseline errors are about understanding sentences, not about vocabulary, which is what an LLM should fix.

### D18. Outcome labels as plain answers (SME decision, rules-1.2)
- **Trigger:** the SME, reading the review page, could not tell whether "Not an ML model: Annex 11 controls apply" was a yes or a no. The tool is for the proposer, the builder and the decision-maker, so every outcome must say whether the idea can go ahead, and under which rule.
- **Decision:** all nine labels follow one pattern, **what it is: what to do (which rule)**, e.g. "Not ML: proceed as a standard GMP system (Annex 11)". The table is in `docs/LABELING_GUIDE.md` §6b. Logic unchanged; only the text changed, so the version moved to rules-1.2 for the audit trail.
- **"Proceed" is not "approved":** it means the proposal is ready for QA review with the listed controls.
- **Wording follows the draft:** D16 chose "not acceptable" because draft Annex 22 says "should not". A first version said "Cannot proceed: not allowed…", which reads stronger than the draft; at the SME's request it became "Should not proceed: not for GMP-critical use (Annex 22 §1)".

### D19. Acceptance criteria: zero dangerous errors; accuracy is secondary (SME decision)
- **Trigger:** "83%… isn't it too low?" With 41 cases the honest range is about 71–94%, and a percentage treats a harmless error the same as one that lets a risky use through.
- **Decision:** the tool is judged first on **zero dangerous errors** and **"when unsure, say unclear"**. A dangerous error is an outcome more permissive than the correct one. The SME decided each boundary case: "Not yet" is never dangerous (questions come back); skipping "Not yet" with a "proceed" is dangerous; wrongly refusing a real proposal is dangerous unless it is Not GMP; screening a question by mistake is harmless. Table in `docs/LABELING_GUIDE.md` §6c, code in `eval/safety.py`, tests in `tests/test_safety.py`.
- **Separate decisions, one call:** "is this a proposal to screen?" and "which outcome?" are counted separately (`wrongly_refused`, `wrongly_screened`), but Gemini still makes both in one answer, so there is no extra API cost.
- **Held-out data:** for the test set the report shows counts only, never which cases were dangerous.

### D20. Safety guards in the rules layer instead of stronger prompt wording (SME decisions, rules-1.3)
- **Trigger:** the error analysis of the two remaining dangerous dev errors. D035: the prompt already said "if information is missing, use unclear" and the model still assumed a review step. D032: the prompt said "the description wins over the ticks", which is too absolute when the description is only a vendor claim.
- **Decision:** deterministic guards after the rules (`app/guards.py`), not more prompt text. A prompt instruction that was ignored once is a gamble; a rule works whatever the model does. G1: no assumed review step. G2: ticks can only make the outcome stricter; a disagreement that would make it more permissive becomes "Not yet" with the contradiction as the question. Guards only ever return "Not yet" (an exhaustive test checks this) and do not run when the model judged the text out of scope ("no proposal, no assessment").
- **Found while testing:** G1 first also turned a clear "Should not proceed" (a GMP-critical LLM) into "Not yet". Not dangerous, but it lost a clear answer; G1 now fires only where the review step changes the outcome.
- **Simulated on the saved dev answers (no API):** dangerous errors 2 → 0 (D032, D035 fixed); accuracy unchanged (35/41), because D016 and D023, where the ticks contradicted a correct reading, became a harmless "Not yet". The official number comes with the next live run.

### D21. No "ask twice" for now (SME decision)
- **Evidence:** two full dev runs agreed on the final outcome in 40/41 cases; simulating ask-twice (A: disagree → Not yet; B: stricter wins) gave no gain over a single run (35/41, 0 dangerous either way), at double the API cost.
- **Decision:** not built. Revisit only if the test run or real use shows dangerous errors that come from inconsistent answers. The comparison method (two runs, compared offline) stays available as a consistency check.

### D22. Form questions reviewed against the regulatory texts (SME decisions, form-1.2)
- **Trigger:** the SME's live test (W35) showed that a self-assessment question can mean one thing to the proposer and another to the regulation. A subagent read the parsed texts and reviewed every question, quoting doc and section for each point (read-only; test cases not read).
- **Confirmed:** "direct vs indirect" is draft Annex 22 §1's own wording; human confirmation does not make a use indirect (§3.3, §10.5 describe human review inside critical use); the FDA's "model influence" (FDA-CRED IV.A.3) is the same test: what the decision rests on.
- **Decided (SME):**
  - A, the GMP question: a third answer "No, not used for GMP work" (without it, non-GMP ideas were forced into "indirectly" and guard G2 looped); "Yes, directly" also covers deciding which items people do not check (A22 §3.2, A11D 8.1) and filling in a GMP record (CH4D 4.24).
  - B, clearer wording (all accepted): the task asks what else people use besides the AI output (A22 §3.1, FDA-CRED IV.A.1-2); "who checks" asks for role, every output or not, against what, where recorded; "receiving or reading the output is not a check"; AI type options in A22's words, with "self-learning" meaning new versions go live without a test-and-release step, and a new option for probabilistic models (A22 §1 names them, the form could not express them); business area, personal data and cloud supplier hints.
  - C, one new question: "Does the AI replace or reduce a check or step that people do today?" (Annex 11 Principle: no decrease in quality when a system replaces a manual operation; A22 §4.3). The SME wants the form short: the second proposed question (how the model can change in use) was dropped; the new self-learning wording covers most of it.
- **Not adopted (for now):** changing the guide's "provides input to a GMP decision" to "provides the evidence a GMP decision rests on" (the prompt now uses the latter wording; the guide keeps both readings until the SME decides).
- **Effect on evaluation:** the 111 cases keep their labels; the new question is added as unanswered (it did not exist when they were written). The classifier sees new option labels, so a new dev run is needed; the test result (W31) stays a form-1.0 result.

### D23. Receiving the output is not a check (SME decision, rules-1.5)
- **Trigger:** dev case D038 (W39): "a trained person checks and approves each output" ticked, but "who checks" only says "QA and the area owners receive it"; Gemini believed the tick and gave a more permissive outcome. G1 only covered forms where nothing was ticked.
- **Decision (SME):** "receiving does not really count as a check, should be more explicit. I think a question should be asked." Guard G1b: a ticked "person approves" with a "who checks" that is empty or only describes getting the output becomes "Not yet: who checks each output, against what, and where is it recorded?". This enforces the form's own rule (D22: "receiving or reading the output is not a check").
- **Alternatives:** trust the tick (the D038 gap); stronger prompt wording (rejected for the same reason as D20: an instruction the model ignored once is not a control).
- **Trade-off:** a keyword match. A real check written without a check word ("the operators go through it") gets a needless question, which is never dangerous. An empty "who checks" also gets the question (proposed by Claude, confirmed by the SME on 2026-11-23); in the first live run this caught D020.

### D24. Source map for citations instead of a similarity threshold (SME decision, map-1.1, prompt-1.6)
- **Trigger:** second-opinion review and benchmark (WORKLOG W46). The old check kept every cited paragraph whose meaning score was at least 0.55 or whose word score was at least 30 %. Two independent judges found 14 of 116 shown citations wrong, all kept; most backed "nobody checks the output" with a sentence saying a person should check.
- **Decision:** a fixed table (`app/source_map.py`) lists, for each answer, the paragraphs that define it. Only those are shown as its source; the prompt names them and they are always among the passages. The judgments claim definitions, and a definition lives in a few known paragraphs, so the same source each time is consistency, not a flaw. All other paragraphs are still used for search, the verdict and the controls.
- **Alternatives:** require both scores (catches 13 of 14 but drops 16 good ones, thresholds still unvalidated); a higher meaning threshold (drops 28 good ones); an NLI model or an LLM judge on every request (cost, latency, and it needs its own validation); fall back to the map's paragraph when the model's citations are all wrong (rejected by the SME: the right source should come from the model, so the prompt was fixed instead); show outside-map citations as "related, not verified" (later, needs its own check).
- **How it fails:** a correct answer whose citation is outside the map shows "Not covered by the sources", visibly, and is counted in the evaluation (`judgments_with_source_rate`); the verdict is unaffected. Today's failure was silent: a wrong paragraph shown as proof.
- **Change control:** the map is pinned to a corpus version (a test fails on a rebuilt corpus), versioned (`source_map_version` in every result) and confirmed by the SME, like the rules.
- **Review and result (W47):** an independent review against all 591 paragraphs changed five entries (map-1.1, confirmed by the SME). Gemini dev run: model citations in the map 72 % → 96 %, known-wrong citations 14 → 1, judgments showing a source 78 % → 97 %, 0 dangerous errors.

### D25. Fix only the too-strict error that passes the overfitting test (SME decision, prompt-1.7)
- **Trigger:** three too-strict dev errors (D026, D036, D042); a blind reviewer agent agreed with all three labels.
- **Decision (SME: "just low risk, high value"):** change only the static/dynamic definition: what counts is the version in use (A22 §1 "continuously and automatically learn and adapt performance during use"; glossary "frozen"; §10.1 change control). It is the regulation's own wording, it was already in form-1.2, and the error it fixes was the costliest kind ("Should not proceed" on a legitimate project). Guarded by a strict sibling (D043).
- **Not changed:** the GMP scope boundary (D036: genuinely ambiguous, too strict costs little) and the "GMP record" definition (D042: narrow, and loosening it risks the four "Should not proceed" record cases). Both documented as grey zones.
- **Test applied:** "would a GMP expert write this definition without having seen the case?"

### D26. Sources: definition for the class, consequence for the outcome (owner decision, map-1.2/1.3, rules-1.9/1.10)
- **Trigger:** the owner saw "the document does not apply to Generative AI…" quoted as the source for "Model type: Generative AI".
- **Decision (owner):** every classification source must define or describe its class; the outcome source states what the regulation does with that combination; the model can only cite from the approved list. Applied to the source map and the outcome sources, then checked by an independent reviewer agent (W56, W57). Generative AI rests on EU AI Act Art. 50 because Annex 22 never defines it; "Non-critical ML" is relabelled "(Annex 11, ICH Q9)" because Annex 22 is silent on non-critical frozen models.
- **Alternatives not taken:** shortening the Annex 22 exclusion sentence (still reads as an exclusion); quoting the A22 §1 "principles may be considered" phrase for non-critical frozen ML (it belongs to the human-in-the-loop sentence for non-frozen models and LLMs); honesty notes for classes no text defines, and extra optional sources (owner: not now).

### D27. Deployment on Azure Container Apps, free tier (owner decision)
- **Context:** the spec asks for an Azure deployment; the owner wants no cost and not to use the DTU student account (its credits serve another purpose).
- **Decision:** Azure Container Apps, consumption plan, scale to zero (minimum replicas 0), image on the GitHub container registry, a budget alert at €1, on a personal Azure free account; region North Europe (owner's choice, closest to Denmark). Public-demo settings: lower daily Gemini cap, a confidentiality notice on the form, demo-only audit log; a separate Gemini key for the demo is recommended.
- **Why:** free up to 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests a month, with no charge when scaled to zero; a demo uses a small fraction (about 1,200 visits a month fit). A containerised app on Azure also matches the target environment. Checked on Microsoft's pricing and billing pages on 2026-11-24 (WORKLOG W61).
- **Alternatives:** App Service Free (F1): free but 60 CPU minutes a day and 1 GB memory, close to what the embedding model and index need; the app stops until midnight UTC when a quota is hit; a trial tier. App Service B1 (the earlier plan, about €12/month): not free. Azure for Students: no card needed, but the owner's student credits are reserved. Hugging Face Spaces: free and no card, kept as the fallback.
- **Risks:** a cost only if the app stops scaling to zero or a free amount changes (budget alert); the account must move to pay-as-you-go after 30 days to keep the always-free services; cold start of 10-30 s after idle.
