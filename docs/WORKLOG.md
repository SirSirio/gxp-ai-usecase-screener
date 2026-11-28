# Work log

A structured record of what was done, why, and with what result. Newest entry last.
Each entry: **Goal** · **What was done** · **Why** · **Result and evidence** · **Commit** · **Follow-ups**.
Design reasoning lives in [DECISIONS.md](DECISIONS.md); this log is the chronological "what happened".
Commit ids and tags mentioned here (e.g. `v1.0-freeze`) refer to the development history, which is kept privately; the public repository holds release snapshots (W63).

---

## W1 · 2026-11-21 · Scoping and source documents
- **Goal:** turn the spec (`Project1_GxP_AI_UseCase_Assistant.md`) into a build plan and collect the knowledge base.
- **What was done:** read the spec and the project notes. Downloaded 9 public documents: EU GMP draft Annex 22, Annex 11 (2011 and 2025 draft), draft Chapter 4, ICH Q9(R1), EU AI Act, two FDA AI texts and FDA warning letter 320-26-58. fda.gov blocked plain downloads, so browser-like request headers were used.
- **Why:** everything else depends on having the exact source texts.
- **Result and evidence:** all 9 files in `data/raw/`, SHA-256 hashes pinned in `scripts/download_sources.py`.
- **Follow-ups:** none.

## W2 · 2026-11-21 · Core build (steps 1, 2, 4, 5 of the plan)
- **Goal:** a working pipeline from use-case text to a cited, rule-based outcome, without an API key.
- **What was done:**
  - section-aware parser and chunker;
  - hybrid retrieval (TF-IDF + local embeddings, RRF);
  - Pydantic schema; rules layer R0–R9; controls catalogue; citation check;
  - `get_section` tool; hash-chained audit log;
  - offline keyword classifier; LLM classifier behind a provider-neutral interface;
  - FastAPI web app.
- **Why:** the spec's architecture. The offline classifier lets everything run and be tested before an API key exists.
- **Result and evidence:** 62 tests passing; an end-to-end run takes about 200 ms per request.
- **Commit:** `77f4b17`.
- **Follow-ups:** LLM providers untested live (no key yet).

## W3 · 2026-11-21 · Test set and evaluation harness (step 3)
- **Goal:** measure the tool instead of guessing.
- **What was done:** a separate AI agent wrote 30 held-out test cases and 10 dev cases from the label guide, without seeing the code. Wrote `eval/run_eval.py` (accuracy per field and outcome, refusal, source recall, citation keep rate); results are stored per version in `eval/results/`.
- **Why:** test-data independence (the Annex 22 §6 idea, applied to the tool itself).
- **Result and evidence:** keyword baseline 0.90 on dev, 0.60 on test. The gap shows overfitting to the dev cases.
- **Commit:** `c3b40f3`.

## W4 · 2026-11-21 · Browser check and UI fixes
- **Goal:** confirm the real web page works, not just the test client.
- **What was done:** drove the app in a browser (Playwright) and took screenshots.
- **Result and evidence:** found and fixed a title cut mid-word, quotes stopping at "i.e.", unreadable references ("§ai-use") and a missing favicon. Also found invisible backspace characters in a regex, introduced by a scripted edit.
- **Commit:** `fd26d5c`.

## W5 · 2026-11-21 · Azure deployment preparation (step 7, not run)
- **What was done:** `startup.sh`, `docs/DEPLOYMENT.md` (Azure CLI steps, budget alert first), `.gitattributes` forcing LF so the startup script runs on Linux.
- **Commits:** `bd0fa6f`, `f7a9e78`.
- **Follow-ups:** needs an Azure subscription.

## W6 · 2026-11-21 · Documentation
- **What was done:** README (business problem first), ARCHITECTURE, DECISIONS (D1–D15), WALKTHROUGH (learning guide), VALIDATION_NOTE, LABELING_GUIDE. An ablation measured the effect of the fixed "framework queries" (primary source retrieved: dev 0.875 → 1.00, test 0.75 → 0.79), and the docs were corrected to match.
- **Commit:** `67c535a`.

## W7 · 2026-11-21 · Independent review of rules, controls and labels
- **Goal:** a second opinion that isn't anchored on the developer's reading.
- **What was done:** a separate AI reviewer agent, briefed as a GxP/CSV reviewer, checked everything against the source texts. Each finding was verified against the source before being applied.
- **Result and evidence:** no wrong rule. Two test labels corrected (T04, T11), three left for the SME. New controls added (data integrity, security, periodic review, supplier oversight for hosted models); AI Act Annex III ingested; wording softened ("acceptable / not acceptable under draft Annex 22"). Rules 1.1, prompt 1.1. Baseline test score 0.57 after the label corrections.
- **Commit:** `9c61d18` (details: DECISIONS D16).

## W8 · 2026-11-21 · Reader review of README and validation note
- **What was done:** a separate agent read the docs as a technical reviewer and as a QA specialist.
- **Result and evidence:** all numbers correct. Fixed overclaims ("validated", AI review presented as human review, LLM/Azure status not stated, "first warning letter"). Added the error direction: of 13 wrong outcomes, 10 err on the safe side and 3 are too lenient.
- **Commit:** `5013fdd`.

## W9 · 2026-11-21 · `start.bat` launcher (user request)
- **What was done:** a double-click launcher that builds the index on first run and opens the browser. It handles the `&` in the folder path and uses Windows (CRLF) line endings.
- **Result and evidence:** tested hidden: the app came up on port 8000.
- **Commit:** `5f41bd9`.

## W10 · 2026-11-21 · Abbreviations and correct quotes (user feedback)
- **Trigger:** "Static ML to score fermentation…" gave "More information needed" plus a quote from the wrong sentence.
- **What was done:** the offline classifier expands abbreviations (ML, LLM, MBR …), case-sensitive so "mL" stays millilitre. Each rule names the sentence it should quote (`quote_hint`).
- **Result and evidence:** the example is now read as a static model, and R3 quotes the scope sentence. Evaluation unchanged (dev 0.90, test 0.57): the remaining errors are about understanding, not vocabulary.
- **Commit:** `c631d4b` (DECISIONS D17).

## W11 · 2026-11-21 · Silent loss of meaning-based search (Windows DLL conflict)
- **Trigger:** while building a learning aid, search printed "dense retrieval disabled: DLL load failed … onnxruntime".
- **Cause:** onnxruntime and PyMuPDF load conflicting versions of the Microsoft C++ runtime (old copy shipped with Anaconda). It only worked when scikit-learn happened to be imported first.
- **What was done:** `import sklearn` first, in `app/__init__.py` (one place, applies everywhere). Added a test that fails if dense retrieval is ever off. Added `scripts/explore.py` (raw page, sections, chunks, search ranks, classify).
- **Result and evidence:** both retrievers active again; 74 tests.
- **Commit:** `05863ba`.
- **Follow-ups:** clean fix: install the latest Microsoft Visual C++ Redistributable (x64).

## W12 · 2026-11-21 · Evaluated Microsoft MarkItDown (user question)
- **Goal:** would converting the PDFs to Markdown help?
- **What was done:** ran MarkItDown on Annex 22 in a throwaway environment.
- **Result and evidence:** line numbers removed (good), but **zero headings** recovered and section numbers **detached from their text** ("4.1." / "4.2." / then 4.1's text). Our parser would then cite the wrong section.
- **Decision:** not for these PDFs; worth considering later for Word documents (company SOPs), where headings are stored.
- **Commit:** none (no code change).

## W13 · 2026-11-21 · Gemini API key and first live LLM runs (in progress)
- **Goal:** run the LLM classifier for real, then evaluate it against the 57 % baseline.
- **What was done:**
  - stored the key in `.env` (git-ignored, verified untracked);
  - listed the available models and chose `gemini-3.5-flash`;
  - first live call → **HTTP 400**; replaying the request showed size was not the issue (requests are ~6–8k tokens, the limit is ~1M).
- **Bugs found by the live run** (exactly why "untested live" was flagged):
  1. API errors crashed the pipeline instead of being logged as rejections → new `ProviderError`, turned into a logged rejection.
  2. A direct answer in Gemini's own JSON shape was accepted, then failed validation → now it is accepted only if it matches the schema; otherwise the schema-enforced call runs.
  3. Gemini 3 "thought signatures" were dropped between turns (the likely cause of the 400) → the model's own message parts are now replayed unchanged.
  4. **Broken schema (root cause of the wrong JSON shape):** `inline_refs` stripped Pydantic's decorative `title` labels *and* our real field named `title`, while still listing it as required. Gemini rejected the schema ("requires unspecified property 'title'"), and a silent fallback to schema-less JSON hid the error. Fixed, the fallback removed (errors now surface and are logged), and a test added.
- **Live result:** second run → both requests **rejected cleanly** (logged, no crash). The audit log showed the schema bug above and **HTTP 429: the free tier allows 20 requests per day for `gemini-3.5-flash`**. After the fix, `gemini-3.1-flash-lite` and `gemini-3.5-flash-lite` accept the schema and return schema-valid answers.
- **Result and evidence:** 77 tests. Lesson, the second time today: silent fallbacks hide bugs (compare W11); fail loudly and log.
- **Follow-ups:** a full evaluation needs about 100–160 requests (40 cases × 2–4 calls). That doesn't fit 20/day; options in the open-items table.

## W14 · 2026-11-21 · Free-tier research and first LLM evaluation
- **Goal:** choose a model that fits the free tier, then measure the LLM against the keyword baseline.
- **What was done:**
  - a research agent checked Google's official pages: Flash-Lite models ~500 requests/day free vs 20 for Flash; quotas are per project and reset at 09:00 Danish time; EEA users get paid-tier data terms (no product-improvement use); paid Flash-Lite costs about $0.50–0.75 per full run;
  - switched to `gemini-3.5-flash-lite` (user decision); added wait-and-retry for per-minute rate limits (not for the daily quota);
  - dev run with prompt 1.1: 10/10 outcomes, but only 62.5 % of judgments had a supporting citation (the model often cited nothing) and it never used the tool;
  - prompt 1.2 (changed on dev only): names the sections that hold each definition and asks the model to fetch a section when needed → 91.7 % supported, still 10/10 outcomes;
  - held-out test set run **once** with prompt 1.2.
- **Result and evidence:** test outcome accuracy **0.87** (baseline 0.57); clear cases 1.00; model type 1.00; **no error on any GMP-critical case**. 4 errors: 2 out-of-scope requests answered, 1 "more information needed" case screened as acceptable with human-in-the-loop controls, 1 non-GMP case given GMP controls. Meets 3 of 5 acceptance criteria; fails refusal recall (0.67) and primary-source retrieval (0.79). About 7.6 s per assessment. Results in `eval/results/test_gemini_*.json`.
- **Caution:** the aggregate test results are now known. Further prompt changes must be justified on dev; a later test run must be reported as a re-use of the test set.
- **Follow-ups:** improve refusal of out-of-scope requests and retrieval (on dev only); Azure OpenAI live test; label review.

## W15 · 2026-11-21 · Gemini as default classifier, with a choice in the form (user request)
- **Goal:** use the LLM in the web app, but keep the option to pick the keyword baseline.
- **What was done:**
  - `.env`: `GXP_PROVIDER=gemini` (the default);
  - the form has a **Classifier** dropdown (offering only providers with credentials); the API accepts an optional `provider` field, and an unknown provider gives 422;
  - the result page shows "Classified by: …" and a **"Screen again with: …"** button to compare both classifiers on the same text;
  - the form warns not to enter confidential information (the text may go to an external AI service);
  - if Gemini fails (e.g. daily quota used up), the error suggests switching to the keyword baseline;
  - tests pin the offline classifier, so they never spend Gemini quota or need the internet.
- **Result and evidence:** 78 tests. Live check on the real app: same text ("Static ML to score fermentation and drug production processes") → Gemini: *Acceptable with full Annex 22 controls* (it read the use as GMP-critical); keyword baseline: *Acceptable with risk-based controls* (it guessed non-critical). When the two disagree, a human should look, which is the point of keeping both.
- **Commit:** see git log ("Classifier choice in the web app").

## W16 · 2026-11-22 · AI product names, case and typos (user question); test isolation bug
- **Trigger:** "If I type ChatGPT instead of LLM, or with different upper/lower case, does the app understand?"
- **What was tested first:** 30 spellings in the keyword baseline. Case was already ignored, and ChatGPT and Copilot were recognised. **Claude and Gemini were refused as "no AI use described"**: they were in the generative-AI word list but not in the separate scope-check list. Mistral, Llama, DeepSeek, Grok, Perplexity, OpenAI and typos (Cahtgpt, ChatGTP, Gemnini, Copliot) were missed.
- **What was done:**
  - one shared product list (`GENAI_PRODUCTS`) used by both checks;
  - version suffixes ("GPT-5", "Claude 4");
  - typo tolerance for names of 6+ letters (similarity ≥ 0.85). A test runs it over every word of the 9 regulatory documents and finds no false match ("clause" vs "claude" scores 0.83 and is ignored).
- **Bug found along the way:** the web tests "forced" the offline classifier by patching dataclass defaults, which never worked (a dataclass captures its defaults at class creation). It only looked fine while `.env` said offline. Once Gemini became the default, the tests tried to call Gemini (they failed on a fake key, so no quota was spent). Earlier test runs also wrote **42 test records into the real audit log**. Fixed with an explicit `config.use_settings()` override and a test that asserts tests use temporary folders and the offline classifier. The 42 records were not deleted (append-only log); see open items.
- **Result and evidence:** all 30 spellings recognised; 97 tests; offline evaluation unchanged (dev 0.90, test 0.57); the real audit log is unchanged by a test run (59 → 59 records).
- **Note:** the Gemini classifier needs none of this. It understands names, typos and case by itself; this was about the keyword baseline and the scope check.

## W17 · 2026-11-22 · API limits written down (user request)
- **Goal:** keep a record of the real free-tier limits, so runs can be planned without guessing.
- **What was done:** `docs/API_LIMITS.md` with the AI Studio quota snapshot of 2026-11-22 (Flash-Lite 500/day, Flash models 20/day, Gemma limited by tokens per minute), requests per evaluation run, options beyond the free tier, data terms and the test-set re-use reminder.
- **Result:** documentation only; no code or evaluation change.

## W17 · 2026-11-22 · Structured intake form, case set v2 (110 cases), review page, new app interface
- **Goal (agreed in discussion with the SME):** replace the single text box with a structured intake form; expand the evaluation data to about 100 cases (dev/test about 30/70) written as filled-in forms with realistic messiness; give the SME a page to approve, reject or rewrite every case; rebuild the app interface. Design with the ui-ux-pro-max and design-taste-frontend skills (user requirement).
- **What was done:**
  - `app/intake_form.py`: the single definition of the form. 9 questions; "where is it used" and "what data" are multiselect; every option has a plain-language (i) explanation; "Not sure" everywhere. Answers are evidence for the classifier, never the classification itself (self-assessment bias).
  - `scripts/validate_cases.py`: checks form values against the definition and re-derives each outcome from the rules layer.
  - Four agents in parallel:
    1. converted the 40 old cases into forms → **dev set** (`eval/v2/dev_cases.jsonl`; same facts, no label changes, 10 deliberate contradictions);
    2. wrote **70 new test cases** (`eval/v2/test_cases.jsonl`; 35 borderline, every outcome ≥ 6 times, 10 contradictions, Danish words, product names, typos; 9 labels flagged as least certain);
    3. built the **review page** (`scripts/review_template.html` + `scripts/build_review_page.py` → `review/review_cases.html`; outcome recalculated live from the real rules; autosave; export and import of decisions);
    4. rebuilt the **app interface**: the form is the main page, quick mode is hidden at `/quick` ("accuracy may be lower"), and the result page is redesigned with "What you submitted". The raw form is stored in the result, the intake JSON (`proposer_answers`) and the audit record.
  - Both design agents loaded both skills, shared the same tokens (navy `#1E3A5F`, Figtree / Noto Sans, Tabler icons) and checked their pages in a browser (keyboard and hover tooltips, 375px, dark mode).
- **Result and evidence:** 110 cases (40 dev, 70 test), validator 0 errors; 116 tests; no em or en dashes in the templates.
- **Finding (app agent):** the **keyword baseline breaks on form text**. The question wording contains its trigger words ("…a QC result, a release…"), so every form comes out GMP-critical. Gemini is not affected. The fix is still to be agreed (see open items).
- **Deviation:** 40 dev + 70 test = 110 (36/64), not exactly 30/70, because all old cases were kept as dev.
- **Note:** the 30 old test cases are now dev data (read by the converter); the v2 test set is new and has not been run.

## W18 · 2026-11-22 · SME review of the 40 dev cases applied
- **Goal:** turn Sirio's review of the dev cases into label changes, with a script that can be reused for the 70 test cases.
- **What was done:**
  - `scripts/apply_review.py`: reads a review export and a case file. Approved cases get `label_status = sme_approved`, rejected cases are removed, rewrites with edits are applied (`sme_rewritten`), and a rewrite with only a comment is listed for a manual rewrite. Comments are printed, never applied automatically. It stops if a decision names an unknown case id, and warns if the cases changed after the review page was built.
  - The export was moved to `eval/v2/reviews/dev_review_2026-11-22.json` and committed as the record of the SME review.
  - Manual changes at Sirio's request: D010 rewritten with every question filled in (still `out_of_scope`, because the task box asks the tool to do the job itself); D041 added, the same task worded as a proposal (`outside_gmp`); D040 (weather) removed. Details in `eval/v2/DEV_NOTES.md`.
  - The review page was rebuilt (data hash 3379ba7714).
- **Why:** dev labels should carry an SME sign-off before tuning starts. D010/D041 form a pair that separates "a request to the tool" from "a proposal to use an LLM".
- **Result:** dev set 40 cases (39 `sme_approved`, D010 and D041 waiting for SME confirmation); validator OK; 116 tests pass.
- **Found during the review:** the status buttons on the review page are toggles, so a second click on "Approve" silently resets the case to open and drops it from the export (this happened to D015 and D023). Fix proposed, not yet built.
- **Note:** the review page keeps decisions per data hash, so the rebuilt page starts empty. The dev decisions are already applied; import the export only if you want to see them again.

## W19 · 2026-11-22 · Plain-answer outcome labels, review-page fix, D032 and D042 (SME decisions)
- **Goal:** act on four SME decisions taken after the dev review.
- **What was done:**
  1. **Review page** (subagent, with the ui-ux-pro-max and design-taste-frontend skills): a second click on an active status button no longer resets the case. Resetting is a separate "Mark as open" link shown under the status buttons, and it keeps comments and edits. Verified in a browser (double-click, keyboard, export, dark mode, 375px). Only `scripts/review_template.html` changed.
  2. **D042 added:** the ML sibling of D007 (the same routing done by a trained model → `permitted_risk_based`).
  3. **D032 changed** from `not_ai_annex11` to `needs_more_information`. SME reasoning: review by exception before batch release is GMP-critical and unflagged steps pass without QA reading them, so a vendor's demo is not enough to say "rules only".
  4. **All nine outcome labels reworded** in the pattern "what it is: what to do (which rule)", e.g. "Not ML: proceed as a standard GMP system (Annex 11)". `app/rules.py` → rules-1.2 (text only, logic unchanged); `docs/LABELING_GUIDE.md` §6b now also gives the plain answer per outcome; README and video script quotes updated; decision D18.
- **Why:** the SME could not tell from "Not an ML model: Annex 11 controls apply" whether a proposal could go ahead. The tool serves the proposer, the builder and the decision-maker, so the outcome must answer that directly.
- **Result:** dev set 41 cases (D040 removed, D041 and D042 added; D010, D041, D042 and D032 waiting for SME confirmation); validator OK; 116 tests pass; review page rebuilt (data 974046d56b).
- **Follow-up (same day, SME request):** "Cannot proceed: not allowed for GMP-critical use" became "Should not proceed: not for GMP-critical use (Annex 22 §1)", matching the draft's "should not" (D16, D18).

## W20 · 2026-11-22 · Compatibility check of the whole pipeline with form cases; evaluation harness for v2
- **Goal (user request):** before spending any Gemini quota, check that everything behind the new intake form works, and fix what does not.
- **Checks run (no API calls):**
  1. All 41 dev forms through the full pipeline with the offline classifier: 0 crashes, audit chain verifies.
  2. All 41 dev forms through the **LLM path with a scripted fake model** that answers with the expected labels (tests the prompt, schema, citation check, rules, intake JSON and audit, not the model): every outcome correct, the proposer's title and answers are kept, prompt size 13–20k characters (about 3–5k tokens).
  3. Retrieval with and without the question wording in the query: key-source recall 0.58 both ways, primary source 0.82 vs 0.85, so the question text does not hurt retrieval.
  4. `normalize_form` sorts multi-select answers into the form's own option order; harmless, but the harness must normalise forms the way the web app does.
- **Found and fixed:** `eval/run_eval.py` still read the old text sets (`case["description"]`), so it could not run the form cases. It now reads `eval/v2/` by default (`--cases v1` for the old sets), validates and renders each form exactly as the web app does, and supports a reproducible random sample (`--sample N --seed S`). Sample runs are tagged `_sampleN` in file names, reports and `history.csv`, so a smoke run can never be mistaken for the one-off test run. New `tests/test_eval.py` (5 tests).
- **Known, not a software error:** the keyword baseline scores 0.32 on the dev forms, because the question wording contains its trigger words (nearly everything comes out GMP-critical, and requests to the tool come out in scope). This is what baseline B fixes; Gemini is not affected.
- **Result:** 121 tests pass. First v2 reports: `eval/reports/dev_v2_offline_latest.md`, `dev_v2_sample10_offline_latest.md`.

## W21 · 2026-11-22 · First live Gemini run on form cases: 10 random dev cases, one at a time
- **Goal (user request):** check the whole software live on a small sample before any larger run, case by case, without wasting quota. Dev cases, not test cases, so the test set stays independent.
- **What was done:** 10 dev cases (`--sample 10 --seed 1`: D005, D008, D009, D014, D017, D025, D029, D031, D032, D037), each run separately with Gemini 3.5 Flash-Lite (prompt-1.2, rules-1.2), checking after each case: valid answer, labels, number of API calls, citations kept, key sources, audit chain. About 29 requests in total (of 500 per day). Report: `eval/reports/dev_v2_sample10_gemini_latest.md`.
- **Software error found and fixed:** Gemini answered several calls with **HTTP 503 "model experiencing high demand"**. The code did not retry it, so one 503 restarted the whole assessment (an extra call) and two in a row turned D014 into a rejected assessment. `providers._post_with_rate_limit_retry` now waits and retries the same call on 500/502/503/504 (5, 15, 40 s). Verified live: D017 and D031 each had 503s and completed. 5 new tests (backoff, give-up, a real 400 not retried, daily quota not retried). D014 was re-run after the fix and was correct.
- **Result:** every answer valid and every citation kept; audit chain intact; no software errors after the fix. Verdict 6/10 correct (small sample, not a benchmark). Autonomy 100%.
- **Classification errors (for prompt tuning on dev, not software):**
  - **Refusal (D009, D031):** requests to the tool itself ("summarise Q9 vs Q9(R1)", "write a farewell speech") were treated as LLM use cases. The form frames every entry as a proposal, which may make this worse. Refusal recall 0.5 here (0.67 on the old test set).
  - **D017 (most serious kind):** "QA makes the final call anyway" convinced the model that deviation classification and batch-hold proposals are non-critical. They feed a disposition decision, so it is critical and human review does not change that (A22 §1). The tool said "proceed with human review" where the label is "should not proceed".
  - **D032:** the model trusted the proposer's "trained model" tick and gave full Annex 22 controls instead of "not yet: ask the vendor". Stricter, not dangerous.
- **Small issues noticed, not fixed:** (1) "unclear" judgments have no citation and are therefore shown as "Unsupported" on the result page, which is misleading (D029); (2) the "key source cited" metric counts the fixed passages that controls always cite, so it is inflated (D032).

## W22 · 2026-11-22 · Baseline B: the keyword baseline reads the form's ticks first
- **Goal:** fix the keyword baseline on form input (W17 finding: the question wording contains its trigger words, so nearly everything came out GMP-critical), with the mapping agreed as decision B.
- **What was done:**
  - `app/assessors/offline.py` (offline-1.2): new `classify_form`. Ticks decide where answered (gmp_impact yes → critical, no → non-critical, or not GMP if only business areas are ticked; ai_type and output_use map one to one). Keywords run only on the proposer's own words (title, task, explanations, "who checks"), never on the question text, and only where the tick is "Not sure" or blank. A ticked AI type counts as an AI use for the scope check, so a rules engine whose text never says "AI" is still screened. The free-text logic was split into reusable pieces; quick mode is unchanged (old dev set still 0.90).
  - The pipeline now passes the form to the classifier (`assess(..., form=)`); the Gemini classifier accepts it but does not use it yet (that is LLM-efficiency idea 1).
  - `tests/test_offline_form.py`: 10 tests (tick mapping, question wording ignored, "not sure" falls back to keywords, business-only areas, scope, end to end).
- **Result on the 41 dev forms:** verdict accuracy **0.32 → 0.63**; in scope 0.93, GMP relevance 0.74, model type 0.88, autonomy 0.82. **9 of the 10 contradiction cases are wrong**, as expected: a checklist believes the ticks, which is exactly what those cases test. The other 6 errors (D016, D017, D019, D036, D037, D041) are the old keyword limits (e.g. "who actually writes GAMP 5" is not recognised as a question). Not tuned further: the baseline is meant to be a simple, fair floor. Report: `eval/reports/dev_v2_offline_latest.md`.
- **Why it matters:** the baseline is now a "static checklist" the LLM must beat. The interesting comparison is on the contradiction cases, where reading the description has to win over the ticks.

## W23 · 2026-11-22 · prompt-1.3: one call per case, structured form fields, prompt fixes from the dev run
- **Goal (user: "yes", then "go with 2 as well"):** LLM-efficiency ideas 1–3 and the prompt fixes for the weak spots seen in W21, tuned on dev only.
- **What was done:**
  - **One call instead of two (idea 2).** In all W21 live runs the model never used the get_section tool, and its free answer never had the right shape, so every case cost a tool-offering call plus a schema-enforced call. Now the core definitions (A22 §1, §3.3, §10.5; `pipeline.CORE_SECTIONS`) are always among the passages, and the default flow is a single schema-enforced call. The tool round is still there behind `GXP_LLM_TOOLS=1` and is tested.
  - **Structured fields (idea 1).** With a form, the model gets each answer as a field (`- gmp_impact (ticked): Not sure; explanation: "…"`) plus a question legend, instead of the rendered form text, so ticks and the proposer's own words are kept apart.
  - **Stable prefix (idea 3).** Passages now come first, in a fixed order (core sections, then the framework queries, then the hits for this case), and the use case comes last. The start of every request (system text + about 8 fixed passages) is identical, which providers can cache. On the free tier this saves tokens and time, not requests.
  - **Prompt fixes (step 2):** (a) requests to the tool itself ("write a farewell speech", "summarise Q9(R1)") are out of scope even when the other form answers are filled in, while a non-GMP proposal stays in scope as not_gmp; (b) human approval, or "QA makes the final call anyway", changes autonomy, never criticality; deviation classification and batch-hold proposals are named as critical; (c) ticks are the proposer's self-assessment: when a tick contradicts the description, the description wins and the contradiction goes into open_questions; when neither settles it (vendor claim only), "unclear".
  - Tests: 3 new or changed (one call, core passages first, structured fields, identical prefix across cases; tool loop still works when switched on). 138 pass.
- **Checks without API:** fake-model run over all 41 dev forms: all outcomes correct. Prompt about 19k characters (about 5k tokens). Offline baseline unchanged (0.63).
- **Not yet measured:** the effect on Gemini's accuracy. That needs a dev run (41 cases, about 41–50 requests with one call per case).

## W24 · 2026-11-22 · Full dev run with Gemini, prompt-1.3 (41 form cases)
- **Goal:** measure prompt-1.3 (W23) on all dev cases. Dev only; the v2 test set is still untouched.
- **Result:** verdict accuracy **0.83** (34/41) vs **0.63** for baseline B. Every answer valid, every citation kept. In scope 0.95, GMP relevance 0.91, model type 0.91, autonomy 0.88; refusal precision and recall 0.86. Report: `eval/reports/dev_v2_gemini_latest.md`.
- **Contradiction cases (ticks contradict the description):** Gemini 8/10, baseline B 1/10. This is the main argument for the LLM over a checklist.
- **Safety check:** none of the 13 GMP-critical cases was called non-critical or not GMP.
- **On the W21 sample (same 10 cases):** 6/10 → 8/10. Fixed: D009 and D031 (requests to the tool now refused) and D017 (human review no longer lowers criticality). New error: D029.
- **Remaining errors (7):**
  - D032 (needs more information → Annex 11): it now follows the description ("rules we configure") instead of asking the vendor. **More lenient than the label**: the one error that skips a question on a GMP-critical review.
  - D029 (needs more information → out of scope): a vague but genuine proposal was refused, so the refusal fix overshoots on vague text. The only clear case wrongly refused.
  - D035 (needs more information → human-in-the-loop): it assumed a review step that is not stated. Lenient.
  - D010 (out of scope → not GMP): the filled-in self-assessment request was read as a proposal. Harmless direction, and arguably a fair reading.
  - D026 (static → dynamic, stricter), D036 (not GMP → non-critical, stricter), D042 (non-critical → critical, stricter).
- **Cost:** 58 HTTP requests for 41 cases: 41 successful, **16 were "503 high demand" retried** by the W21 fix, 1 per-minute 429 retried. Without the W21 fix, a large part of this run would have failed. One call per case works (W23).
- **Caching:** the identical prefix was reused in only 1 of 41 calls (about 4,300 prompt tokens per call). Google's implicit caching does not reliably kick in here, so idea 3 currently brings no measurable saving. It costs nothing; kept.

## W25 · 2026-11-22 · start.bat fixed: an old server held the port (user report)
- **Problem:** double-clicking `start.bat` "did not work". Cause (subagent, verified): a copy started the day before was still running on port 8000, without `--reload`, so it kept serving yesterday's code; every new start failed with "port already in use" while the browser opened the old copy. A fixed 5-second wait also opened the browser before the app was ready.
- **Fix (`start.bat` only):** checks port 8000 first; if an older copy of the app (python.exe) holds it, press R to restart it with the current code or O to open it; any other program is left alone. The browser opens only once `/api/health` answers. Verified by launching it like a double-click from another folder.
- **Note:** if a script file is changed while its window is still running it, cmd may run lines of the new file; close old windows before editing a running .bat.

## W26 · 2026-11-22 · Dangerous-error metric (plan step 1: acceptance criteria)
- **Goal:** agreed plan, step 1. Judge the tool on dangerous errors first, accuracy second (D19). Decided with the SME question by question.
- **What was done:** `eval/safety.py` (strictness ranking + rules, `is_dangerous`, `error_kind`); `eval/run_eval.py` reports `dangerous_errors`, `dangerous_errors_on_gmp_critical`, `wrongly_refused` (and how many of them were dangerous), `wrongly_screened`, `stricter_or_not_yet`; case ids only for dev. `--rescore <result.json>` recomputes a saved run without API calls. `history.csv` gained the new columns (old rows kept). `tests/test_safety.py`: 31 tests pinning each SME decision. Guide §6c, decision D19.
- **Re-scored today's dev runs (no API):**

| | Verdict accuracy | Dangerous errors | of which GMP-critical | Wrongly refused (dangerous) |
|---|---|---|---|---|
| Gemini, prompt-1.3 | 0.83 | **3** (D029, D032, D035) | 1 (D032) | 1 (D029) |
| Baseline B | 0.63 | 8 | 5 | 0 |

- **Reading:** the target is 0. Gemini's 3 dangerous errors are all cases where the correct answer is "Not yet" and the tool went ahead or refused: it does not yet say "unclear" when it should. That is the second acceptance criterion and the topic of plan steps 3 and 4 (stricter-wins rule, ask twice).
- **Result:** 167 tests pass.

## W27 · 2026-11-22 · Error analysis of the dangerous dev errors (plan step 2, in progress)
- **Goal:** find the cause of each dangerous error before fixing anything (model, our prompt, the input form, or the label).
- **D035, cause: the model.** The proposer ticked "Not sure" for what happens with the output and wrote "who checks: not decided yet"; Gemini still answered "a person approves each output". LLMs fill gaps with the most typical scenario, and the prompt rule "if information is missing, use unclear" did not stop it. **SME decision:** add a deterministic rule in step 3: if output_use is "Not sure" or blank and "who checks" describes no check, the human-approval classes cannot be claimed; the outcome becomes "Not yet" with the question. Accepted trade-off: when the proposer wrote the review step in the wrong field, the tool asks a needless question, which is never dangerous (D19).
- **D029, cause: the label.** The SME judged the tool right: no use is proposed, so "Not assessed" is correct ("garbage in, no assessment"). Label changed (DEV_NOTES). `eval.run_eval --rescore` now refreshes labels from the case files, so saved runs can be re-scored after a label change without API calls.
- **Re-scored dev (no API):** Gemini 0.85, **2 dangerous errors** (D032, D035), 1 on a GMP-critical case (D032), 0 wrongly refused. Baseline B 0.61, 8 dangerous.
- **Next:** D032.

## W28 · 2026-11-22 · Safety guards G1 and G2 (plan steps 2 and 3)
- **Goal:** fix the causes found in the error analysis (W27) with deterministic rules agreed with the SME. D032, cause: our prompt ("description wins" is too absolute); SME decision: ticks may only make the outcome stricter.
- **What was done:** `app/guards.py` (G1 review not stated, G2 ticks stricter), run in the pipeline right after the rules (rules-1.3). The strictness ranking moved to `app/safety.py` (`eval/safety.py` re-exports it), so the app and the evaluation share one definition. `tests/test_guards.py`: 17 tests, including an exhaustive check that a guard can only ever return "Not yet". Guide §6d, decision D20, ARCHITECTURE updated.
- **Bug found by the tests:** G1 also softened a GMP-critical LLM's "Should not proceed" to "Not yet"; fixed (G1 only where review changes the outcome).
- **Simulation on the saved Gemini dev answers (no API):** dangerous errors **2 → 0**; accuracy unchanged 35/41 (D016, D023 became a harmless "Not yet" because their ticks contradict the description).
- **Result:** 183 tests pass. Plan step 4 (ask twice) is next; it may no longer be needed on dev, and costs one extra call per case.

## W29 · 2026-11-22 · Second dev run, consistency check and "ask twice" simulation (plan step 4); paid-tier pricing
- **Goal:** step 4, tested cheaply before building anything (SME suggestion): a second full dev run, then compare both runs offline and simulate "ask twice".
- **Second dev run (prompt-1.3, rules-1.3 with guards, live):** accuracy **0.88** (36/41), **0 dangerous errors**, refusal precision 1.0. 53 requests (10 retried 503s, 2 retried 429s). Report: `eval/reports/dev_v2_gemini_latest.md`. The remaining 5 errors are harmless: D016 and D023 (guard G2 "Not yet" by design), D010 (screened a request), D026 and D036 (stricter).
- **Consistency:** both runs gave the same classification in 38/41 cases and the same final outcome in **40/41**. The only change of outcome was D042 (routing deviations: critical in run 1, non-critical in run 2), a genuinely borderline label.
- **Ask-twice simulation (both runs with guards):** A (disagree → Not yet) 35/41, 0 dangerous; B (stricter wins) 35/41, 0 dangerous; single runs 35/41 and 36/41, 0 dangerous. On dev, asking twice catches no dangerous error and would double the cost. SME decision: **neither is built** (D21), no gain for double the cost.
- **Paid-tier pricing (subagent research, `docs/API_LIMITS.md`):** about $0.002–$0.009 per request; a 70-case test run $0.27–$0.62; Google AI Pro's $10/month API credits cover the workload; prepay minimum $5 is a hard spending cap.

## W30 · 2026-11-22 · Test labels reviewed (70 cases): independent pre-review + SME decision
- **Goal:** SME sign-off on the 70 held-out test labels before the single test run, without the person who tunes the tool reading the test cases.
- **How:** a fresh subagent with no knowledge of the tuning pre-reviewed every label against the guide (§1, §6, §6b–6d), decisions D16–D21 and the SME's dev decisions (D010/D041, D029 "no proposal, no assessment", D032 vendor claims). It wrote a file in the review page's import format and reported only counts. The SME checked the flagged cases on the review page.
- **Result:** 67 approved (20 of them with a "BORDERLINE:" note), 3 proposed rewrites, **all 3 accepted by the SME**: T004 → Not assessed (too vague to be a proposal), T032 → Not yet (the SME judged both readings acceptable; the safer one kept), T043 → Not yet (a question back is safer than "Not ML"). The SME first wrote "T034" for the third case; confirmed T043 (typo). Records: `eval/v2/reviews/test_prereview_2026-11-22.json` (agent), `eval/v2/reviews/test_review_2026-11-22.json` (final). Applied with `scripts/apply_review.py --quiet` (new: comments not printed, so test content stays out of the tuner's context).
- **Fixed:** `apply_review.py` did not clear key sources and category when a label became out of scope; the validator caught it.
- **Review-page usability finding:** "Approve" means "keep the original label" and silently discards an imported proposal, which confused the SME (the outcome changed back on click). Better labels: "Keep original" / "Use proposed change". Open item.
- **Test-run plan (SME):** run the test set once; decide afterwards whether a second run (for consistency on unseen data) is worth it. No tuning in between. (The SME later dropped the "not on the same day as the dev tuning" rule: what protects independence is a frozen, committed version and no tuning on the results.)
- **Note on independence:** the SME described three test cases in chat, so the tuner knows their gist. Nothing in the prompt or the guards is changed because of them.

## W31 · 2026-11-22 · v2 test run (70 held-out form cases), once, frozen version
- **Version:** commit `0f9f242`, prompt-1.3, rules-1.3 (guards), corpus e97079b5633b, Gemini 3.5 Flash-Lite. Labels SME-approved (W30). Run the same day as dev tuning (SME dropped the different-day rule); nothing was tuned after the results. Aggregates only were looked at; per-case results stay in `eval/results/test_v2_gemini_20261122T121712.json`, unread.
- **First attempt crashed** before any result: one test form has a task text under 20 characters, which the web app rejects before classification. The harness now scores such a form as "Not assessed" (`forms_rejected_by_validation`), as the app behaves. Tool code unchanged.
- **Result vs acceptance criteria (D19):**

| | Gemini (prompt-1.3, guards) | Baseline B |
|---|---|---|
| **Dangerous errors** (target 0) | **0** | 13 |
| on GMP-critical cases | **0** | 9 |
| Wrongly refused | 0 | 2 |
| Verdict accuracy | 0.87 (clear 0.92, borderline 0.80, out of scope 1.00) | 0.59 |
| Refusal precision / recall | 1.00 / 1.00 | – / 0.36 |
| Valid answers | 100% | 100% |

- **The 9 remaining Gemini errors are all "stricter or Not yet"**, i.e. harmless by D19. Primary-source retrieval 1.00, citations kept 98.5%. 83 requests (12 retried 503s, 2 retried 429s), mean latency 6 s.
- **Reading:** both acceptance criteria are met on unseen data. With 0 dangerous errors in 70 cases, the true rate is still uncertain (rule of three: below about 4%). Known limits stay as listed in the open items (same people wrote cases and rules; synthetic inputs).

## W32 · 2026-11-22 · Documentation of the results; small fixes (user: "1. write down and document", "2. ok go")
- **Validation note rewritten** (`docs/VALIDATION_NOTE.md`): form input, the v2 data and how independence was kept, SME label verification (honest count: 3 dev cases written at the SME's request still await confirmation), the acceptance criteria D19 with the test results, consistency, how the result was reached, known limits, guards in the risk section, change control incl. "a dangerous error found later".
- **README** updated to the v2 results and the guards; LLM marked as verified live; `start.bat` mentioned.
- **"Unclear" no longer shown as "Unsupported"** (`app/citations.py`): an "unclear" judgment claims nothing, so it needs no source; it now says "Not enough information in the proposal to classify this; see the questions". Test added (185 pass). Note: this raises `judgments_supported_rate` slightly for runs after this change.
- **Video script:** marked as to be updated after the redesign.
- **SME decisions:** no second test run for now (quota, nothing calls for it); the 42 old test records stay in the audit log ("keep").
- **Not done here:** the review-page button wording ("Approve" keeps the original label) goes into the UI redesign, which is done by a subagent with the design skills.

## W33 · 2026-11-22 · Follow-up loop, backend (SME design choice: inputs next to each question)
- **Goal (SME idea):** on "Not yet", the proposer answers the questions and resubmits; at most 3 rounds, then "please resubmit with a clearer scope". The SME chose: each question comes with the matching form inputs (the same choices with their (i) help, prefilled), plus a text reply for the classifier's own questions, so corrected ticks reach the rules and the guards.
- **What was done (backend only; the pages follow in the redesign):**
  - `app/intake_form.py`: optional `follow_up` list of {question, answer} in the form (validated; empty answers dropped; first submissions keep their exact shape); `MAX_ROUNDS = 3`; `CLASSIFICATION_INPUTS` (which form questions settle which field). `form_to_text`, the prompt's `format_form` and the baseline's free text include the answers (the baseline reads answers only, never question text).
  - Rules and guards now say which field each question is about (`RuleOutcome.question_fields`). `pipeline.follow_up_items` turns a "Not yet" result into `AssessmentResult.follow_up`: "fields" items (e.g. G1 → "what happens with the output" + "who checks"; G2 → the contradicted choice) and up to 3 "text" items from the classifier. `follow_up_allowed` is false in the last round.
  - Round and parent request are recorded in `RunMeta` and the audit log. `/assess` reads hidden `round`, `parent_request_id` and `fu_q_<n>` / `fu_a_<n>` pairs (earlier answers are posted again, so they accumulate); round 4 is refused with the "clearer scope" message. `/api/assess` accepts `round` and `parent_request_id`.
  - Versions: prompt-1.4 and offline-1.3 (identical to before for a first submission).
  - `tests/test_followup.py`: 9 tests including a full two-round loop through the web app. 194 pass.

## W34 · 2026-11-22 · UI redesign: landing, sources page, follow-up section, green palette (subagent with the ui-ux-pro-max and design-taste-frontend skills)
- **Goal (owner's direction):** deep green + warm neutral, no blue; a bit more style but still easy to use; a landing page, a sources page and the follow-up section on the result page. Presentation and routing only: no change to questions, rules, guards, pipeline, schema or API JSON.
- **What was done:**
  - Routes (`app/main.py`): `/` is now a landing page (what, for whom, how, what it does not do, how it was tested); the form moved to `/submit` (`index.html` renamed `submit.html`); new `/sources` with `SOURCE_GROUPS` (every document of `app/ingest/sources.py` exactly once, tested). Templates get `max_rounds`, `questions_by_id`, `sources_by_id` and the provider code.
  - `app/templates/_form_macros.html`: the question inputs and the classifier selector, shared by the form page and the follow-up section, so both render the same inputs and (i) help.
  - Result page: outcome first, warnings, then the follow-up section ("Answer to continue", "Round X of 3"): "fields" items show the same inputs as the form, prefilled; "text" items post `fu_q_<n>`/`fu_a_<n>`; earlier answers are re-posted after them; the other answers as hidden fields (never duplicated); hidden `round`, `parent_request_id`, `provider`. In the last round: the questions plus the "submit it again with a clearer scope" message and a link to `/submit`. Classification and controls are collapsible panels (closed while a follow-up is shown); each citation also links to the official document and to `/sources`; "What you submitted" lists earlier follow-up answers; run details show round and "Follow-up to request <id>". The "screen again with another classifier" form now also carries the follow-up answers, round and parent.
  - `app/static/style.css`: new tokens (accent #17594A, base #F4F3EE, graphite #1E2321; harmonised go/stop/ask/neutral; dark mode), all text pairs WCAG AA (lowest 5.57:1). `app/icons.py`: 14 more Tabler 3.31.0 outline icons (path data copied from the package). `app/static/app.js`: the follow-up form shows the "AI classifier" wait message when needed.
  - Review page (`scripts/review_template.html`): same palette. When a case holds a proposed change, the buttons read "Keep original" and "Use proposed change", with a one-line explanation and a "Proposed change: ..." summary. Export format unchanged (checked in the browser).
- **Tests:** `test_api.py` updated for `/submit`; new tests for the landing links, sources on every page, the sources page (titles + official URLs), the follow-up inputs (prefilled, no hidden duplicates, round/parent/provider), text items and earlier answers as `fu_q_`/`fu_a_` pairs, and no inputs after the last round. All pass.
- **Verified in a browser** (keyword baseline): landing → example → result; the "Not yet" translation case → answers → round 2 ("proceed if a person approves each output"); last-round message; keyboard focus and (i) tips; 375 px; dark mode; no console errors.
- **Main agent review before commit:** 200 tests pass; no blue left; only presentation and routes changed. The classifier selector still showed the old scores ("~57 %", "~87 %"); updated to the v2 test results (59 % / 13 dangerous vs 87 % / 0 dangerous).
- **Side effects to know:** the browser checks ran with the normal settings, so about 6 assessments were appended to the real audit log and `data/results/` (keyword baseline, no API). The "screen again with another classifier" button now carries the follow-up answers, round and parent request (it silently dropped them before).
- **Gap found (not fixed):** if a follow-up round fails form validation, `/assess` re-renders the full form and the follow-up answers are lost.

## W35 · 2026-11-22 · Live SME test: three "Not yet" rounds; GMP question and contradiction explanations reworked
- **Trigger:** the SME screened a real-looking idea with Gemini ("Claude analyses fermentation data and suggests process improvements; changes go through change control") and got "Not yet" three rounds in a row. Cause: guard G2 saw a contradiction (ticked "Yes, affects GMP" = critical; the reading = non-critical) and only asked a question; the SME never learned what was contradictory, kept "Yes" and answered the classifier's other questions, which cannot change the outcome. SME and Claude agree the case is non-critical (ideas evaluated through change control).
- **SME decisions:** (1) the GMP question separates **direct** from **indirect** impact, which is draft Annex 22 §1's own wording ("direct impact on patient safety, product quality or data integrity"); the line is what the decision is based on, so human confirmation does not make a use indirect (D017 lesson). (2) A contradiction is **explained**, not just asked: which answer conflicts with the description, what each reading means, the outcome each would lead to, and how to resolve it. (3) No special handling when the proposer stands by the answer: explain and ask again (Claude's proposal "take the stricter reading as final" was rejected).
- **What was done (backend):** `app/intake_form.py` form-1.1 (new GMP label, option texts "Yes, directly" / "No, only indirectly", help text; values unchanged, so the 111 cases stay valid). Guard G2 builds per contradiction a detail record (`RuleOutcome.question_details`) and lists only the fields whose tick alone makes the outcome stricter; `FollowUpItem.contradiction` and `FollowUpItem.blocking` (rules/guard questions block; the classifier's own questions are "points QA will want answered"). rules-1.4 (outcomes unchanged). Guide §2 updated. Tests: the SME's case as a guard test, plus a follow-up test; 202 pass.
- **Note for evaluation:** the option labels the classifier sees changed ("Yes, directly"), so the next dev run measures form-1.1; the test result (W31) was on form-1.0.
- **In progress:** a subagent reviews the regulatory texts against all form questions (read-only); the page display of contradictions and blocking/non-blocking questions follows in one UI pass with its findings.

## W36 · 2026-11-22 · Dark mode: brighter green accent (owner: "a brighter green, as everything is already dark")
- **Goal:** in dark mode only, a brighter and more vivid green accent, with enough contrast to read. Light mode, layout, copy and Python unchanged.
- **What was done:** dark tokens in `app/static/style.css` and `scripts/review_template.html` (both dark blocks). The review page was rebuilt with `scripts/build_review_page.py`. Old → new: accent `#7FC8A9` → `#52D68A`, hover `#9AD6BC` → `#74E0A2`, text on accent fills `#0D1A14` → `#0B1A11` (dark text, not white), tint `#1B2F27` → `#16301F`, line `#3C6B58` → `#33784F`, link / accent-text `#8FD0B4` → `#6EDC9C`, focus ring `#7FC8A9`/`#8FD0B4` → `#52D68A` (app) / `#6EDC9C` (review page). The hue moved from 155° (mint) to 145° (true green), and saturation went from 40 % to 62 %. Outcome tones are unchanged.
- **Why:** the old mint looked dull on the dark background. A bright fill needs dark text, because white text on `#52D68A` is only 1.8:1.
- **Contrast (WCAG 2.2 AA):** accent text 9.95:1 on bg, 9.23 on card, 7.68 on tint; links 10.86 / 10.07 / 8.38; dark text on accent 9.70, on hover 11.05; focus ring and checked borders 9.2:1 or more against card. The go / stop / ask / neutral tones on their own backgrounds are 9.06 / 8.40 / 8.95 / 9.47. Go (yellow-green, 93°) stays a different hue from the accent (145°) and always shows an icon and a label.
- **Verified in a browser** (dark emulation, keyword baseline): landing, `/submit` with an example (checked state and focus ring), the result page, `/sources`, the review page; light mode still shows `#17594A`. No console errors. 202 tests pass. About 1 assessment was added to the real audit log by the browser check.

## W37 · 2026-11-22 · Form-1.2 from the regulation review (SME decisions D22)
- **What was done:** `app/intake_form.py` form-1.2: GMP question with "No, not used for GMP work" and the wider "Yes, directly" (not-checked items, GMP records); AI type options reworded in Annex 22's terms plus a probabilistic option; clearer help for task, areas, output use, who checks, data, source; new question `replaces_check` (in "How the output is used"). Baseline and guards map the new answers (`not_gmp`, `probabilistic`); G2's resolution text names the new answer. prompt-1.5: "critical" defined by what the GMP decision rests on, including not-checked items and GMP records. Form examples updated (the SOP-drafts example now ticks "No, only indirectly", otherwise it would itself trigger a contradiction). All 111 cases get `replaces_check` unanswered; labels unchanged. Tests: 4 new (incl. the loop the review found); 206 pass. Offline dev unchanged (0.61, 8 dangerous).
- **Next:** one UI pass (subagent with the design skills) for the contradiction explanations and the blocking / "points QA will want answered" split on the result page; then a dev run with Gemini on form-1.2.

## W38 · 2026-11-22 · Result page: contradictions explained, blocking questions separated (subagent with the design skills)
- **What was done:** the follow-up section splits "Answer these to get a result" (questions that decide the outcome) from "Points QA will want answered" (optional; "does not change the screening result"). Each G2 contradiction is shown side by side: "You answered … means … would lead to <outcome>" vs "Your description reads as … would lead to <outcome>", with "How to resolve" right above the prefilled input. The last-round list also shows the contradiction. Four-answer questions (the GMP question) lay out 2x2. 2 new tests; 208 pass.
- **Verified** in a browser on a scratch server with temporary audit folders (0 entries in the real audit log): light, dark, 375px, keyboard; a G2 page resubmitted with "No, only indirectly" came back as round 2 "Generative AI: proceed if a person approves each output".
- **Noted:** the keyword baseline reads ticks first, so it can never produce a G2 contradiction; only an LLM classifier can. `style.css` has no version tag, so a hard refresh (Ctrl+F5) may be needed after updates.

## W39 · 2026-11-22 · Gemini limits respected by the code (user request); dev run on form-1.2
- **User request:** "you are always matching the top usage limit, make sure this is respected". With one call per case, runs reached Google's 15 requests per minute and relied on the 429 retry.
- **What was done:** `QuotaGuard` in `app/llm/providers.py`, used for every Gemini HTTP attempt (retries included, since failed requests also count against Google's quota): at most 12 requests per minute (`GEMINI_MAX_RPM`, spacing 5 s) and at most 450 per day (`GEMINI_DAILY_BUDGET`); beyond the budget a request is refused before it is sent (logged rejection with a clear message). The day count lives in `data/usage/gemini_requests.json` (git-ignored), shared by app and evaluation, seeded with today's estimate (346). Counter day starts 08:00 UTC (Google resets 09:00 Danish time; an hour late in summer, on the safe side). 2 tests with a fake clock; 210 pass.
- **Dev run, form-1.2 + prompt-1.5 (before the guard):** accuracy 0.80 (was 0.88), **1 dangerous error: D038**. 42 requests (1 retried 429). D038: the proposer ticked "a person approves each output" but "who checks" only says "QA and the area owners receive it" and the report is e-mailed automatically; the previous run read it as "nobody checks", this run believed the tick (the new option label "A trained person checks and approves each output" may be more persuasive; one run cannot separate that from run-to-run variation). The outcome "proceed if a person approves each output" is more permissive under both the old and the new label. Other changes are harmless: D023 and D024 read as "probabilistic" (new option), D005 and D042 stricter, D016 "Not yet".
- **Open:** how to close the D038 gap (proposal: extend guard G1 so that a ticked "person approves" with a "who checks" that only describes receiving the output cannot count as a check). For the SME to decide.

## W40 · 2026-11-22 · Close-out before compaction: state, D038 relabel, handover
- **D038 relabelled** (before the W39 run): the AI-written monthly EM trend report, e-mailed without review, is a GMP record used as such (CH4D 4.24) → critical → "Should not proceed" (was non-critical / "add human review"). Claude's judgment under the form-1.2 definition of "direct", agreed by the SME; both outcomes were a "no". Recorded in the case and `eval/v2/DEV_NOTES.md` (commit e9ab1d9).
- **Learning session (SME, /learn-while-building):** the regulation review's findings were explained one by one. Points the SME worked through: answer options must cover every real situation (MECE: a missing "not GMP" answer forced a wrong one and caused a G2 loop); "every output checked" decides the autonomy field, "what the decision rests on" decides criticality (D017-type: QA checks every proposal, still critical); an AI that lowers sampling decides what is not tested, so it is direct; transcription into LIMS makes the AI output the GMP record (Annex 11 §6 accuracy check is a control, it does not make the use indirect); under draft Annex 22 §1 an LLM with direct impact should not be used, whatever the supervision, while indirect LLM use needs a human in the loop.
- **State at close (commit 5a1914a + this entry):** form-1.2, prompt-1.5, rules-1.4, offline-1.3; 210 tests; app redesigned (landing, /submit, /sources, follow-up rounds with contradiction explanations; green palette, brighter in dark mode); Gemini paced to 12/min and capped at 450/day (`data/usage/gemini_requests.json`, seeded with an estimate of 346 for today). Latest dev run (form-1.2): accuracy 0.80, **1 dangerous error (D038)**; the v2 test result (W31, form-1.0) stays the reference: 0 dangerous, 0.87.
- **Pending SME decision:** extend guard G1 so a ticked "a person approves each output" with a "who checks" that only describes receiving the output ("receives it", "gets it", "is sent to") does not count as a check → "Not yet: who checks it, and how?". Then a dev run (~45 requests).

## W41 · 2026-11-23 · Guard G1b: receiving is not a check (SME decision D23); dev run 0 dangerous
- **SME decision:** "No, receiving does not really count as a check, should be more explicit. I think a question should be asked."
- **What was done:** `app/guards.py` G1b (`G1-check-not-described`): when "a trained person checks and approves each output" is ticked but "who checks" is empty, says nobody, or only says who gets the output ("receives it", "e-mailed to", "gets it", "reads it"; the output-use note counts too), and the review step decides the outcome, the result is "Not yet" with the question "Who checks each output before it is used, against what, and where is the check recorded?". Any check word (reviews, approves, verifies, signs, compares, second-person, Danish *tjek/kontrol/godkend*) lets it through. G1 itself also treats a receive-only text as no check. A critical LLM stays "Should not proceed". rules-1.5. Tests: 16 new guard cases (receive-only, receive + check, empty, a clear "no" kept); 224 pass.
- **Empty "who checks":** with "person approves" ticked it also gets the question (the form then gives no evidence of a check); proposed by Claude, confirmed by the SME on 2026-11-23.
- **Simulated first (no API) on the saved dev answers:** latest run 1 → 0 dangerous (only D038 changes); the two older runs: no new firing.
- **Live dev run (form-1.2, prompt-1.5, rules-1.5; 41 requests):** accuracy 0.83 (0.80 before), **0 dangerous errors**, 0 wrongly refused, 1 wrongly screened (D010, harmless), 6 stricter or "Not yet". D038 was read as critical this time (correct, so the guard was not needed); **G1b caught D020 live**: ticked "person approves", "who checks" empty, note "the operators go through it"; Gemini read "a person approves" → would have been "proceed if a person approves", more permissive than the label "add human review" (acts autonomously). It was caught by the empty-field branch. Remaining stricter errors: D023, D042 read as critical; D026 as self-learning; D036 as GMP; D016 G2 "Not yet". Result: `eval/results/dev_v2_gemini_20261123T080430.json`.

## W42 · 2026-11-23 · Readable source page; traffic-light green for "proceed" (subagent with the design skills)
- **Owner's requests:** a cited source opened raw JSON (`/api/section`); the "proceed" green "is not a traffic light green". The subagent loaded ui-ux-pro-max and design-taste-frontend first (checked in its transcript).
- **What was done:** new page `/section?doc=…&section=…&q=<quote>` (`app/section_page.py`, `app/templates/section.html`): full document name, status badge (draft notice for the July 2025 drafts, shorter one for FDA's draft guidance), date, PDF pages, link to the official document, back to "All sources"; the section and each subsection under its own heading, max ~70 characters a line; the cited quote is highlighted with a "Go to the passage" link; unknown section → "Section not found" (404). Paragraphs are rebuilt at sentence boundaries (the stored text has no line breaks); the page says the official PDF is the reference. `/api/section` still returns JSON. Result-page citations open the new page in a new tab.
- **Colours:** go tone light `#3A6B22` on `#EDF2E4` → `#13773A` on `#E6F4EA` (4.96:1); dark `#A9D08A` on `#1A2617` → `#6FD982` on `#12291A` (8.78:1). The dark accent moved from `#52D68A` to jade `#4CD4A2` (9.2:1) so "go" and the accent stay distinct; light accent `#17594A` unchanged. `scripts/review_template.html` updated (generated review page not rebuilt). Stylesheet and script links now carry `?v=` (closes the cache-busting item).
- **Verified:** scratch server (port 8010, offline provider, temp audit folder; real audit log unchanged at 75 lines), light, dark, 375px. 6 new tests; 230 pass.

## W43 · 2026-11-23 · "Not yet" label renamed (SME decision)
- **SME:** the label "Not yet: answer the open questions first" read badly. Claude proposed five options (recommended "More information needed: answer the questions below"); the SME chose their own wording: **"Pending clarification: update any missing or conflicting details below"**. It covers both reasons for this outcome: missing information and a contradiction between ticks and description.
- **What was done:** `VERDICT_LABELS` in `app/rules.py` (rules-1.6, text only, logic unchanged, as with D18), guide §6b, README. The code `needs_more_information` is unchanged, so cases, results and tests stay valid. Older docs and code comments keep "Not yet" as internal shorthand (noted in guide §6b). 230 tests pass.

## W44 · 2026-11-23 · Follow-up answers kept when a follow-up round fails (open item from W33)
- **Bug:** if a follow-up round failed form validation (e.g. task description too short) or the LLM call failed (502), the form page came back without the follow-up answers, the round and the link to the earlier request; resubmitting started a new case at round 1.
- **What was done:** backend (Claude): `_safe_form` keeps well-formed follow-up answers (cut to the form limits); `_form_page` carries `round` and `parent_request_id`; all error paths in `/assess` pass them; an invalid follow-up answer gets its own field error. Page (subagent; loaded ui-ux-pro-max and design-taste-frontend first, checked in its transcript): on round > 1 the form shows "Follow-up round N of 3. You are still working on the same use case" with a "Start a new use case instead" link, hidden round and parent fields, and a section with the earlier answers as editable fields; "Clear form" and the examples also clear them; they are not counted as form questions.
- **Tests:** 4 new (answers and round kept on a 422, resubmission stays in round 2 with the same parent, no follow-up fields on a first-round error, `_safe_form` drops malformed items); 234 pass. Verified in a browser on a scratch server (offline, temp audit folder): error page, fix, resubmit → round 2 linked to the first request; light, dark, 375px.

## W45 · 2026-11-23 · API errors explained in plain language, technical reason under "details" (SME request)
- **SME:** "plain language version please! maybe add an 'expand for details' where you show the technical message". Before, every failure said "The model did not return a valid assessment", even when Gemini was only overloaded or the quota was used up; the real reason was only in the audit log.
- **What was done (backend, Claude):** `ProviderError` carries a `kind` and the HTTP status (`classify_http`, `http_error` in `app/llm/providers.py`, using the provider's own error message): overloaded (5xx), rate_limit (429 per minute), quota_day (429 per day), daily_budget (QuotaGuard), auth (401/403, invalid key), rejected (other 4xx), network (no response). The assessor raises `ProviderFailure`; the pipeline turns it into `AssessmentFailed` with a plain message per kind (`FAILURE_MESSAGES`: what happened, that the answers are kept, what to do) and the technical reason in `detail`; the audit record gets `failure_kind`. No second assessment attempt after an API failure, except a network error (the HTTP layer already retries 429/5xx; retrying a used-up quota or a wrong key only spends requests). `/api/assess` returns `kind` and `detail` too.
- **Page (subagent; loaded ui-ux-pro-max and design-taste-frontend first, checked in its transcript):** the red banner shows the plain message; under it a collapsed native "Show technical details" disclosure with the technical text (small monospace, wraps, copyable), on the form and in quick mode; validation errors have no details block.
- **Tests:** 18 new in `tests/test_api_errors.py` (classification, provider message, one call per non-retryable failure, network tried twice, page and API show message and detail), with a fake client; no API called. 252 pass. Verified in a browser on a scratch server with a fake 503 (light, dark, 375px, keyboard, screen reader).

## W46 · 2026-11-23 · Source map for citations (second-opinion review, point 1; SME: "let's go with the map")
- **Goal:** the citation shown next to each judgment must really back it. The review found that the support check passed almost everything: a paragraph was kept if its meaning score was at least 0.55 *or* its word score at least 30 %, and nearly every GMP paragraph scores about 0.6 against any GMP sentence (8 in 10 of the 591 paragraphs would pass for "critical").
- **Benchmark (dev only, saved answers, no API):** two independent judge agents read the 116 citations of the latest Gemini dev run (prompt-1.5, 41 cases, 101 judgments) and marked each as supports / partial / does not support, after first picking their own best source. Result: 81 support, 21 partial, **14 do not support**, and the old check kept all 14. 13 of the 14 are autonomy answers, typically "nobody checks the output" backed by the Annex 22 §1 sentence that a person *should* check each output. The 116 citations are only 28 distinct (answer, paragraph) pairs, marked consistently in 27, so the answer key is a small table.
- **Root cause:** the prompt pointed every autonomy answer to A22 §3.3 and §10.5, which describe a human checking. A check can only drop a wrong citation, never supply the right one.
- **What was done (D24):**
  - `app/source_map.py` (map-1.0, **draft, awaiting SME confirmation**): for each of the 12 answers the paragraphs that define it (9 paragraphs in all), each with the sentence that backs it; the benchmark's known-wrong pairs; pinned to corpus `e97079b5633b`.
  - Citation check: a cited paragraph is kept only if it was shown to the model **and** is in the map for that answer; the similarity score is kept as information only. The quote is the sentence the map entry names. Nothing outside the map is shown ("related reading" deliberately not built, SME decision).
  - Retrieval: the map's paragraphs are always given to the model (adds the FDA model-influence paragraphs).
  - prompt-1.6: the evidence rules list the defining paragraph for every answer, generated from the map. offline-1.4: the keyword baseline cites the map's main paragraph (classification unchanged: identical verdicts on all 41 dev cases).
  - Quotes now also end at a question mark or a closing quotation mark (an FDA sentence was cut off before its key words).
  - Versions: `source_map_version` in results, audit records, intake records and eval runs.
  - Eval: new metrics `model_citations_in_map_rate`, `model_citations_known_wrong`, `model_citations_outside_map` (the model's own citations before the check) and `judgments_with_source_rate`.
- **Effect, replayed on the saved prompt-1.5 answers:** wrong citations shown 14 → 0, but 20 of 101 judgments would show "Not covered by the sources" (12 of them "nobody checks"), because the old prompt led the model to the wrong paragraph. prompt-1.6 addresses that; it needs one Gemini dev run after the SME has confirmed the map.
- **Tests:** `tests/test_source_map.py` (9: coverage of every answer, corpus pin, map paragraphs always retrieved, prompt lists every paragraph, opposite-meaning citation dropped, quote per answer, baseline cites only the map). 261 pass. Offline dev run: verdicts unchanged, model citations 100 % in the map.

## W47 · 2026-11-23 · Source map reviewed against the whole corpus (map-1.1, SME: "yes"); Gemini dev run with prompt-1.6
- **Review (SME request: "have a subagent double check these paragraphs among all of them"):** an independent reviewer agent read all 159 AI-specific paragraphs (A22, FDA-CRED, FDA-DP, FDA-WL) in full and searched A11, A11D, CH4D, Q9 and AIA by keyword. 7 of 12 answers fine, 5 changes, all checked against the paragraph texts and **accepted by the SME**:
  1. "not GMP" rests on the GMP boundary of Annex 11 (Principle; draft §1), plus FDA credibility §II, instead of the Annex 22 scope sentence (outside Annex 22 is not outside GMP);
  2. "static" uses the Annex 22 glossary definition ("Static – Frozen model") instead of the deterministic-output sentence;
  3. "acts with oversight" gains AI Act Art. 14 (override, reverse, stop button) and loses the bare "model influence" definition;
  4. "acts autonomously" rests on FDA's sole-determinant example, described as the clinical example it is, without the bare definition;
  5. the §10.5 description keeps its condition ("depending on the criticality … may imply").
  No EU GMP text defines the two "acts" answers; the map says so. A paragraph holding two examples (FDA §IV.A.2) or several glossary entries gets the right sentence highlighted (`QUOTE_START`, tested).
- **Gemini dev run (prompt-1.6, map-1.1, rules-1.6; 41 requests, quota 44 → 85 of 450):** 0 dangerous errors; accuracy 0.805 (previous run 0.829: D038 became a harmless "Not yet"; D023 changed from one wrong outcome to "Not yet"; D016 failed on a network error, nothing shown). Median latency 6 s (one request hung for 14 minutes on the network, so the mean reads 30 s).

| Citations, dev (same map-1.1 check) | prompt-1.5 answers (replayed) | prompt-1.6 run |
|---|---|---|
| Model citations in the map | 72 % | **96 %** |
| Known-wrong citations | 14 | **1** |
| Judgments that show a source | 78 % | **97 %** |

- **Left over:** 3 "nobody checks" judgments show "Not covered by the sources" (one cited the Annex 22 human-in-the-loop sentence, one cited the warning letter's paragraph on unreviewed AI documents, one cited nothing). Visible and harmless; the verdict is unaffected.
- **Tests:** 262 pass (new: highlighted sentence per tricky entry).

## W48 · 2026-11-23 · Review of the source-map commit; total request deadline; change control covers the map
- **Claude's review of D24 (other chat's commit 5e2696a):** sound: a measured problem (14 of 116 shown citations wrong, all kept), root cause found, a deterministic table instead of an unvalidated threshold (same logic as D20), reviewed, SME-confirmed, versioned, pinned to the corpus; failure is now visible. Points raised: a citation now shows *which definition was applied*, not evidence about the case (be ready to explain); the 96 % is a dev number from the set the map was built on (a test run would show whether it holds); change control did not mention the map; one request took 851 s (D017).
- **What was done (SME: "yes fix them"):** (1) `VALIDATION_NOTE.md` §8: a corpus change and the final Annex 22 now also require a map re-review; new row for map changes. (2) `app/llm/providers.py` `_send`: the answer must arrive within a total deadline (`LLM_REQUEST_DEADLINE`, default 120 s); httpx's 90 s timeout only bounds each wait between bytes, so a slow trickle could hold a request for minutes. A timeout is its own failure kind ("Gemini took too long to answer…"), not retried. Cause of the 851 s is not certain (a trickle, or the computer sleeping, look the same in the logs); the deadline covers the first.
- **Tests:** 3 new (timeout kind, trickle stopped at the deadline with a fake clock, normal answer through the streaming path); network mocks now patch `providers._send`. 265 pass. No API called.

## W49 · 2026-11-23 · Repo prepared for publication: personal references removed from files and history; pushed to GitHub
- **Goal:** publish the repo without personal context: no private references, no local paths, no personal notes.
- **What was done:** screened every file at HEAD, every file version in every commit and every commit message. Reworded the few true hits (project line and spec path in `CLAUDE.md`, one sentence each in `WALKTHROUGH.md` and this log). Removed the personal learning log (`docs/LEARNING.md`) from the working tree and from all history. History rewritten with `git filter-repo` (`--replace-text`, `--invert-paths`); authors and dates unchanged. A full backup bundle of the old history was kept outside the repo.
- **Commit IDs:** the rewrite changed every commit ID. Cited IDs in the docs, eval reports, `eval/results/*.json` and `history.csv` were mapped old → new with filter-repo's commit map, so every cited ID still names the same change.
- **Checks:** re-screen clean; `.env`, audit logs, usage counters, local Claude settings and browser snapshots were never tracked. 265 tests pass.
- **Commit:** this entry's commit.

## W50 · 2026-11-24 · Feature check (functional test, before the freeze) and fixes
- **SME plan:** check that all features work, fix, then freeze; the held-out test set runs once afterwards on the frozen version. "I would like to have all the results saved, so we can analyze them afterwards… I would like to manually check only the flagged ones."
- **Feature check (subagent with the design skills; scratch servers, offline baseline plus 8 Gemini requests; real audit log unchanged):** 32 checks: 21 pass, 1 fail, 7 flagged, 3 info. Saved in `qa/feature-check-2026-11-24/` (`report.md`, `results.json`, `responses/` with every result; screenshots kept locally, git-ignored for size).
- **Fail F10e:** Gemini wrote source ids in square brackets as the prompt shows them (`[A22:1:1]`); the citation check treated them as unknown, so every judgment showed "Not covered by the sources" (outcome unaffected). Fix: `Judgment.citations` strips wrapping brackets and quotes when the model answer is parsed (`app/schema.py`); the id must still match a passage exactly; the raw answer stays in the audit log.
- **Flags, all fixed (SME: "yes fix all, go with a"):** F02b "nine questions" → ten (landing, README; validation note says the test run used the 9-question form-1.0); F03k the R3 explanation names only what is unclear (`R3_TEXT`); F04b run details show rules and source-map versions; F06b (option a) after the last round the label reads "Pending clarification: no rounds left, submit again as a new proposal with a clearer scope" (`FINAL_ROUND_LABEL`), the "update details" and "Screen again" offers are hidden, "Start a new proposal" is the only primary button, the open questions stay listed; F08b every failure message says the answers are kept; F11b the adaptiveness × autonomy grid is flipped below 640 px so it fits a phone; F11c section pages no longer repeat a subsection title as the first sentence. Pages by a UI subagent (loaded ui-ux-pro-max and design-taste-frontend first, checked in its transcript), before/after screenshots in `qa/.../fixes/` (local).
- **Versions:** rules-1.7 (user-facing rule texts). **Tests:** 14 new; all pass.
- **Next:** freeze; then the final held-out test run (SME decision pending).

## W51 · 2026-11-24 · Too-strict errors: only the low-risk fix (prompt-1.7, D25); plan to the demo
- **SME:** improve the three too-strict dev errors (D026, D036, D042) only where it is low risk and high value; worried about overfitting.
- **Analysis:** all three were systematic (also wrong in W41): definitions applied too broadly. A blind reviewer agent (regulatory texts only, no labels, no notes) agreed with all three labels (D042 non-critical, medium; D026 critical + static, medium; D036 not GMP, medium-low). Overfitting test used: "would a GMP expert write this definition without having seen the case?" D026 passes clearly (A22 §1 wording, already in form-1.2); D042 is narrow and loosening "GMP record" risks the four "Should not proceed" record cases; D036 is a grey zone where too strict costs little.
- **Decision (D25):** prompt-1.7: static vs dynamic is decided by the version in use (retrained but released after re-test and approval = static; new versions live without test-and-release = dynamic); label guide aligned. D036 and D042 stay as documented grey zones. New strict sibling **D043** (same soft sensor, vendor pushes each nightly model live) must stay dynamic → "Should not proceed"; label is Claude's proposal, **awaiting SME confirmation**.
- **Gemini dev run (prompt-1.7, rules-1.7, 42 cases):** 0 dangerous, 0 wrongly refused; D026 now read as static and, because the proposer ticked "self-learning", guard G2 asks with the contradiction explained (was a wrong "Should not proceed"); D043 and D018 still dynamic → "Should not proceed". **8 cases got no answer: Google HTTP 503 "high demand"** after the app's retries, so the headline accuracy (0.714) is not meaningful; on the 34 answered: 30 correct (88 %), the 4 misses all "Pending clarification". D036 and D042 were right this time without a fix (run-to-run variation). SME: "these results are fine".
- **Plan agreed (SME):** (1) the SME reads every page and gives feedback; (2) the texts are then rewritten in plain language with the SME's humanizer skill (prompt to follow); (3) freeze and tag; (4) full held-out test run, slower than usual (about 1 request / 20 s, ideally in the Danish morning); answers lost to HTTP 503 are discarded and those cases re-run; (5) docs with the final numbers; (6) video. Azure on hold (no account, costs money); free hosting options to be looked at later.

## W52 · 2026-11-24 · `/paraphrase` skill ("the Gemini workflow"): Claude drafts, Gemini rewrites, Claude checks
- **Goal (SME):** better-written texts with no copy-paste and no API tokens: Gemini rewrites for style, Claude checks that nothing key was changed, dropped or added, and a report shows the text passed (step 2 of the W51 plan: plain-language rewrite of the pages).
- **What:** user-level skill `~/.claude/skills/paraphrase/` (`SKILL.md` + stdlib script `scripts/paraphrase.py`, no network calls). Route: the Gemini **website** in a **temporary chat** (not in the Gemini history), driven by Claude in Chrome. Steps: `prompt` (message with style brief and protected terms, browser snippets) → Gemini → `ingest` (answer copied in pieces, length verified against the page) → mechanical `check` (protected terms, numbers, dates, ids, links, code blocks; flags must/should/may/not/only/all, structure, length) → Claude's claim-by-claim meaning check, minimal fixes → `report` (PASSED / PASSED after N fixes / FAILED / INCOMPLETE, with all three versions). Runs kept in `~/.claude/paraphrase-runs/`. Project settings: `.claude/paraphrase.md` (audience and style brief; protected terms from the labeling guide).
- **Routes ruled out:** (1) Antigravity: the installed version has no supported way to receive a message from another program (only an undocumented internal server). (2) Gemini CLI: with no settings file it took `GEMINI_API_KEY` from the project `.env`, so the first test calls ran on the app's AI Studio key (outside the QuotaGuard count; about 15–25 requests, most failed with HTTP 503); shown by the same call refusing to start from a folder without `.env`. `~/.gemini/settings.json` now forces Google login and excludes the key (tested with a fake key: ignored), but Google no longer accepts Gemini CLI on personal Google logins ("migrate to the Antigravity suite"), so the CLI is unusable without a key. Gemini CLI then uninstalled (SME request) together with everything it created that day (settings, chat logs of the test calls, error reports, two `projects.json` entries); the older `~/.gemini` contents (Antigravity, earlier Gemini CLI use) untouched.
- **Why:** the SME does not want API tokens spent and wants no manual step; the website uses the normal Gemini account. Data policy unchanged: only project text is sent; the skill refuses secrets and company material.
- **Result:** first live run on guide §6b/§6c (2026-11-24, Gemini mode "Hydrogen"): 0 hard failures; the meaning check found one invented actor ("Evaluators judge the tool" for "The tool is judged") and restored it → **PASSED after 1 fix**. Earlier, on a deliberately flawed rewrite, the mechanical check caught the lost date and code name, while the reversed "draft" status, the swapped outcome order and the weakened "accuracy is secondary" were caught only by the meaning check (as designed).
- **Next:** use it for the plain-language rewrite of the pages (W51 plan, step 2).

## W53 · 2026-11-24 · Owner's page review, part 1: classifier labels, progress while screening, rotating examples, testing copy
- **Feedback (owner):** the classifier menu should say what a classifier is, not how it scored; pressing "Screen" gave no sign of what was happening; the landing card should rotate three examples; the testing text should not say "verified by an SME" ("reviewed manually") and should be shorter and more general, without numbers.
- **What was done:** classifier labels "Keyword baseline: a fixed checklist, no AI" / "Gemini …: AI classifier" (`app/main.py`, Claude). Pages (subagent; loaded ui-ux-pro-max and design-taste-frontend first, checked in its transcript): (1) every screening form (intake, follow-up, screen again, quick mode) shows a progress panel: "Your answers were sent for screening.", elapsed seconds, a bar easing toward 90 % that never claims to be done, and the real stages in the code's order (passages → AI classifies → citations checked → rules decide), only the AI stage shown as running; a calm "taking longer than usual" note after 30 s; for the keyword baseline the panel only appears if the page has not loaded after 0.9 s; accessible (status region, progressbar, reduced motion); errors unchanged. (2) Landing card rotates three examples (frozen vision model on vials → full controls; LLM drafting SOPs with QA approval → proceed if a person approves; LLM deciding batch disposition → should not proceed), labels verbatim from the rules and checked against them in a test; swaps every 5.5 s, pauses on hover, focus and hidden tab, dots and a pause button, no auto-rotation with reduced motion. (3) Testing copy: "It was tested on synthetic cases kept apart from development, each with a manually reviewed label, and compared with a simple keyword checklist. The main criterion: it should never give an outcome more permissive than the correct one." with a link to the validation note.
- **Tests:** 3 new; 290 pass. Browser-checked on a scratch server (offline, temp audit folder): light, dark, 375 px, keyboard, reduced motion.
- **Noted:** README still says "verified by a process SME" (3 places): to change with the docs refresh after the test. `.claude/paraphrase.md` (W52) is a local settings file and is not committed.

## W54 · 2026-11-24 · Plain-language rewrite of the app's texts with the Gemini workflow (W51 plan, step 2)
- **SME:** paraphrase the whole app with the `/paraphrase` skill, done by a subagent; keep decided keywords and short sentences; Claude checks and corrects Gemini; the SME reviews on the pages, not in report files (skill step 4 changed accordingly: apply, then a short chat note).
- **What was done (subagent; loaded paraphrase, ui-ux-pro-max and design-taste-frontend, checked in its transcript):** 147 prose texts in 5 Gemini runs (Gemini website, temporary chats, mode "Hydrogen"; one run retried after an error); Gemini changed 89. Kept word for word: outcome labels, the GMP answer options, question and option labels, buttons and navigation, the testing sentence, regulatory quotes, document names, "draft". Claude's meaning check restored four required-control texts where Gemini had strengthened the wording ("must" added to intended use, acceptance criteria and quality-unit review; "call for" → "require" for the FDA credibility control). Three reworded control descriptions made the app pick a different source sentence; fixed `quote_hint`s keep every control quote as before. Files: `app/controls.py`, `app/guards.py`, `app/intake_form.py` (help texts only), `app/pipeline.py`, `app/rules.py`, `landing.html`, `quick.html`, `section.html`; two tests updated for new copy.
- **Classifier input unchanged:** the classifier reads question and option labels (`form_to_text`), not help texts, so no new dev run is needed. rules-1.8 (rule texts).
- **Checked by Claude:** rule and guard texts keep their safety meaning (e.g. "should not be used", "does not assume a review step", "does not select the more permissive reading"). 290 tests pass. Pages checked at 375 px, light and dark; real audit log unchanged.
- **Next:** the SME reads the pages; then freeze and the held-out test run.

## W55 · 2026-11-24 · "An answer takes more than 30 s and seems stuck": server froze during a screening; 503 waits shortened
- **Owner's report:** a screening took more than 30 s and looked stuck.
- **Found:** (1) Google answered HTTP 503 "high demand" again (audit 15:07 UTC); the app retried with waits of 5, 15 and 40 s, so the error page came after more than a minute. (2) **Bug:** `/assess` is an `async` route that called the assessment directly, so while it waited for Gemini the whole server froze: the home page took 40 s to load during the owner's request, and the new progress page could not load its assets. (3) The audit log's lock was per instance, but the pipeline creates an instance per request, so two parallel requests (quick mode and the API already ran in worker threads) could read the same last hash and fork the chain.
- **Fixed:** `/assess` runs the assessment in a worker thread (`run_in_threadpool`); one audit lock per log file shared by all instances; in the web app a 503 is retried twice (3 s, 8 s), so the plain "Gemini is overloaded" message comes after about 15 s; the evaluation keeps the patient 5/15/40 s retries (`EVAL_TRANSIENT_DELAYS`).
- **Tests:** server answers a page while a slow assessment runs; 6 threads × 25 appends keep a valid chain; retry waits for app and evaluation. 293 pass.
- **Note:** the owner's server was still on rules-1.7 (not restarted after W54).

## W56 · 2026-11-24 · Sources reviewed by the owner: a classification source defines its class, the outcome source states the consequence (map-1.2, rules-1.9, prompt-1.8)
- **Owner's finding:** under "Model type: Generative AI" the page quoted "…the document does not apply to Generative AI and LLM, and such models should not be used in critical GMP applications": a scope exclusion, not evidence that the tool *is* generative AI. **Principle agreed (owner):** each classification is backed by the regulation's definition of that class; the outcome by what the regulation does with that combination; the model can only cite from the approved list (source map).
- **Changes:** (1) generative → EU AI Act Art. 50 ("AI systems, including general-purpose AI systems, generating synthetic audio, image, video or text content", quote trimmed; Annex 22 never defines generative AI); (2) dynamic and (3) probabilistic: the Annex 22 §1 sentences are quoted only up to their definition (`QUOTE_END`); (4) outcome "Not GMP" rests on the Annex 11 scope (Principle) plus AI Act Art. 6 as the high-risk reminder (the bare Annex III heading is gone); (5) "Should not proceed" quotes the Annex 22 §1 sentence for the model type at hand (dynamic / probabilistic / generative), not always the LLM one. **Not changed:** "Non-critical ML" keeps the A22 §1 scope sentence: the alternative ("…the principles described in this document may be considered") sits in the human-in-the-loop sentence about non-frozen models and LLMs and would suggest a review duty for frozen models. `best_quote` now applies start/end trims to the whole sentence before shortening.
- **Versions:** map-1.2, rules-1.9, prompt-1.8 (the prompt lists the map's paragraphs, so the classifier's evidence list changed: one dev run needed before the freeze). **Tests:** 3 new (classification quotes never state a consequence; "Should not proceed" quote per model type; "Not GMP" rests on the GMP scope), 4 updated for the new generative source; 296 pass.
- **Also explained to the owner:** an LLM is "locked" on the adaptiveness axis because the version in use does not learn from use; its output varies (probabilistic), and a silent provider version change is the real GMP risk (model version logged; change control, validation note §8).
- **In progress:** an independent reviewer agent checks all class and outcome sources against the principle; a design subagent builds a graphical "How it works" page (owner's choices: process flow + decision tree, pick-a-path interaction).

## W57 · 2026-11-24 · Independent review of the sources applied (map-1.3, rules-1.10, prompt-1.9)
- **Review (blind agent, regulatory texts and code only):** agreed with all five W56 changes and with keeping "Non-critical ML" off the human-in-the-loop sentence for frozen models; found more cases of the same pattern.
- **Applied (owner: "apply A and C1, not C2, drop B"):** non_critical quotes only "…which do not have direct impact on patient safety, product quality or data integrity"; informs and recommends quote §3.3 only up to "…made by a human operator (human-in-the-loop)"; recommends no longer lists the duty sentences (FDA warning letter "must be reviewed and cleared", A22 §1 "should always be responsible"), which back the outcomes instead, leaving §3.3 and §10.5 ("consistent review and/or test of every output"); the Annex 22 glossary definition is the main source for static; a sentence shown by two paragraphs of one class appears once; the "Non-critical ML" outcome quotes Annex 11 §1 "…decisions on the extent of validation and data integrity controls should be based on a justified and documented risk assessment…" and ICH Q9 §3 "The level of effort, formality and documentation… commensurate with the level of risk"; its label becomes **"Non-critical ML: proceed with risk-based controls (Annex 11, ICH Q9)"** (C1). The support-score claim for generative no longer contains the consequence wording.
- **Not applied (owner):** honesty notes for classes no text defines (B); optional extra sources (C2: draft Chapter 4 §4.23 for critical, FDA "self-evolving" for dynamic). Kept AI Act Art. 6 as the Not-GMP reminder (the outcome text asks to check high-risk listing).
- **Versions:** map-1.3, rules-1.10, prompt-1.9 (the evidence list for "recommends" changed): the planned dev run before the freeze covers it. **Tests:** 4 new; 299 pass.

## W58 · 2026-11-24 · Smoke run on dev (10 cases, prompt-1.9); "How it works" page
- **Smoke run (owner: "try with just 10, randomly"; run on dev, not on the held-out test set, which stays for the frozen version):** 10 random dev cases, 6 requests/min: 8 answered, 2 lost to Google HTTP 503 after the patient retries (24 requests for 10 cases); 0 dangerous; 7 of 8 answered correct (D026 "Pending clarification" via G2, as in W51); model citations in the map 100 %, known-wrong 0, judgments with a source 100 %. Mean latency 38 s (retries). `eval/results/dev_v2_sample10_gemini_20261124T180551.json`.
- **"How it works" page (owner's brief: very graphical, minimal text, (i) for details; owner's choices: process flow + decision tree, pick-a-path):** subagent (loaded ui-ux-pro-max and design-taste-frontend first, checked in its transcript). `/how-it-works`: the seven process steps plus the audit log, with an "up to 3 rounds" loop back to the form; "Rules decide" opens into a decision tree (in scope? → GMP relevance → model type → autonomy → 13 colour-coded outcome leaves with source tags and (i) popovers); click an answer and its path draws in; three animated example paths and a reset; vertical stepper on narrow screens; text equivalent for screen readers; reduced motion respected. Labels, tones and sources are read from the code (`app/how_it_works.py`), and `tests/test_how_it_works.py` walks the embedded tree for all 120 class combinations plus "not a concrete AI use" and compares each leaf with `decide()`. Nav link and a landing-page link. 309 tests pass.
- **Not done:** the `/paraphrase` pass on the page's text: Gemini's website returned an error, then declined on the retry (temporary chat). To repeat when Gemini is available.

## W59 · 2026-11-24 · FREEZE (tag `v1.0-freeze`) before the held-out test run; retry option for provider failures
- **Owner:** "I think now we are ready for the freeze."
- **Frozen (what the test run measures):** prompt-1.9, rules-1.10 (incl. guards G1, G1b, G2), source map map-1.3, form-1.2 question and option labels (the classifier reads these), corpus `e97079b5633b`, model `gemini-3.5-flash-lite`, retrieval settings. Any change to these after the tag is a change to the system and makes a later test run a re-use (validation note §8).
- **Still allowed after the freeze:** page design and wording the classifier never reads (templates, help texts, landing, "How it works"), docs, the demo video. The `/paraphrase` pass on the "How it works" page falls in this group.
- **Evaluation script:** `--retry-unanswered <result file>` re-runs only the cases that got no answer because of the provider (HTTP 503 "overloaded", network, timeout, per-minute rate limit), refuses if prompt, rules, source map or corpus changed since the run, and records `retries` (cases retried, still unanswered) in the result; invalid model answers are real results and are never retried (owner decision W51). New metric `unanswered_provider_failures`. Test-set runs still print totals only. 3 tests (fake flaky provider, no API).
- **Plan from here (W51):** in the Danish morning: one full dev run on the frozen version (the source list changed twice since the last full run) as a check, not for tuning; then the held-out test run, slow (`GEMINI_MAX_RPM=3`), then `--retry-unanswered` for any 503 losses. If the dev check shows a dangerous error, stop and decide with the owner before the test run.
- 312 tests pass.

## W60 · 2026-11-24 · 15-second demo video for LinkedIn; classifier label tidied
- **Owner's brief:** 15 s for people scrolling LinkedIn; fields filled fast with a typing effect, as if someone used the app; a plausible case most people understand.
- **Made by a subagent (loaded ui-ux-pro-max and design-taste-frontend first, checked in its transcript):** `media/demo-15s.mp4` (local, git-ignored): 15.0 s, 1080×1350 (4:5), 30 fps, H.264, no audio, 2.9 MB, plus a poster frame. Case: a chatbot drafts cleaning SOPs; QA reviews and approves every SOP in the eDMS. Landing ("Can we use AI for this?") → the form typed and clicked ("A first GMP check, in seconds") → the green outcome "Generative AI: proceed if a person approves each output (Annex 22)" and the Annex 22 §1 page with the passage highlighted for 2.3 s ("Every answer cites the regulation") → end card with the product line, the owner's principle sentence and the GitHub link. A real Gemini answer (1 request), replayed for retakes; recorded on a scratch server, real audit log unchanged.
- **Label (owner):** "Gemini 3.5 Flash-Lite (AI classifier)" / "Keyword baseline (a fixed checklist, no AI)" instead of the repeated model id (page text only, freeze unaffected).
- **Next (owner asked about publishing):** Hugging Face Spaces after the test run and before the LinkedIn post (Dockerfile, public-demo cap, confidentiality notice, demo-only audit log; a separate free Gemini key recommended so the demo does not share the test quota).

## W61a · 2026-11-24 · LinkedIn post drafted; process-flow image
- **Goal (owner):** a short, catchy LinkedIn post for the project, with the demo video, a preview of the process flow and a couple of emojis; paraphrased by Gemini.
- **What:** `media/linkedin-post.md` (local, git-ignored): drafted by Claude, rewritten by Gemini (web, temporary chat), meaning-checked by Claude: passed after 2 fixes ("right now" kept; plain link instead of Markdown, which LinkedIn shows raw). `media/linkedin-process-flow.png` (2385×1249, 1.91:1): the flow strip and principle line of /how-it-works, captured at 2× from a local server.
- **Why:** no company names in the post (data policy); numbers taken from the README (W31 test run).
- **Owner edits (same day):** shorter; hook "With draft Annex 22 out, every AI idea in EU GMP starts here"; accuracy and the keyword-checklist comparison removed (the number undersells the tool and nobody screens with a keyword list); instead the contradiction check and follow-up questions; "111 cases, labels checked by hand", with the 0 dangerous errors tied to the 70 held-out cases only; app link (Azure Container Apps) and GitHub link. Then opened with the problem: AI is spreading, pharma struggles because of regulation, rightly so (GMP rules protect patients). Second Gemini pass on this version: passed after 1 fix (links back to plain URLs). Owner added the Azure / Gemini API line; hashtags changed to #GMP #Annex22 #AIinPharma #ComputerSystemValidation #QualityAssurance (#CSV is read as the file format, #AI is too broad). New opening in the owner's words (2026-11-28): AI in pharma is not as simple as elsewhere, GMP protects patients, every AI idea needs a regulatory check first; the "Can we use AI for this?" hook dropped (too vague); "GMP screen", not "compliance screen" (the post says it is not a compliance decision). Opening question (owner's pick of 5): "Where does EU GMP draw the line for AI? 🤔". Results line made confident, no extra numbers: "Tested on 100+ realistic cases, every one checked by hand. Not a single unsafe call in the final test." ("unsafe call" = dangerous error; "in the final test" keeps it tied to the held-out run.)
- **Open:** "0 dangerous errors" is from the W31 run (form-1.0); confirm it after the frozen test run (W59) before posting. LinkedIn does not allow a video and an image in the same post: video in the post, flow image in the first comment (or a later post).

## W61 · 2026-11-24 · Deployment decision: Azure Container Apps on a personal free account (D27); documents brought up to date
- **Owner:** Azure if possible, at no cost; the DTU student account and its credits are used for something else, so not that one.
- **Checked on Microsoft's pages (2026-11-24):** the Azure free account gives $200 credit for 30 days plus 65+ always-free services; to keep the always-free services after 30 days (or once the credit is used) the account moves to pay-as-you-go, still at no cost within the free amounts. **Container Apps** (consumption plan) is free up to 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests per subscription per calendar month, with no charge while the app is scaled to zero. **App Service Free (F1)**: 60 CPU minutes per day (max 3 per 5 minutes), 1 GB memory, 1 GB storage; the app stops (HTTP 403) until midnight UTC when a quota is exceeded; Microsoft calls F1 a trial tier, and its Q&A has several reports of Linux F1 apps stuck in "quota exceeded". Azure Container Registry: free for 12 months on one Microsoft page, paid on another (not relied on).
- **Estimate for our app** (0.5 vCPU, 1 GiB, awake about 5 minutes after each visit): about 150 vCPU-seconds and 300 GiB-seconds per visit, so the free amount covers roughly 1,200 separate visits a month; running nonstop would need about 7 times the free amount, so scale-to-zero is required.
- **Decision (owner, D27):** Azure **Container Apps**, consumption plan, minimum replicas 0, image on the GitHub container registry (free for public images), a **budget alert at €1**, a personal Azure free account (the owner creates it). Public-demo settings: a lower daily Gemini cap, a notice not to enter confidential or company information, the audit log marked as demo-only (the container file system is not kept). A separate free Gemini key for the demo is recommended, so visitors do not share the test-run quota. Hugging Face Spaces stays the fallback if the Azure account is not possible. `docs/DEPLOYMENT.md` rewritten for this; the earlier App Service guide kept as the alternative.
- **Documents updated in the same commit:** `docs/DECISIONS.md` (D27), `docs/DEPLOYMENT.md`, `docs/PLAN.md` (status per step, acceptance criteria now point to D19), `docs/VALIDATION_NOTE.md` §4b (changes W48–W60 and the freeze), `docs/ARCHITECTURE.md` (new modules: section page, How it works, the source map's quote trimming, guard G1b).
- **Next:** the owner creates the Azure free account; in the morning the dev check and the held-out test run on `v1.0-freeze`; then the docs with the final numbers, the deployment, and the LinkedIn post.

## W62 · 2026-11-24 · History cleaned of a personal note (owner request)
- A personal remark in the W53 entry was reworded and removed from every commit with `git filter-repo` (backup bundle kept locally first); the history was force-pushed. Commits from W53 onwards and the tag `v1.0-freeze` got new ids (same content apart from that sentence; the freeze tag now points to the rewritten freeze commit). Commit ids cited in the evaluation records were updated from filter-repo's commit map.

## W63 · 2026-11-24 · Public repository holds release snapshots only (owner decision)
- **Owner:** "just go with the snapshot approach … we have everything in the decision files."
- **How:** the full development history stays in the private local repository (`main`). A separate branch `public` holds release snapshots: one commit per publication with the files as they are at that moment (built with `git commit-tree` from `main`'s tree, so nothing from earlier versions, old commit messages or old author data is published). Only `public` is pushed, as the GitHub repository's `main`; tags are not pushed. The GitHub repository is deleted and recreated by the owner first, so nothing from the earlier pushes stays in GitHub's cache.
- **Effect:** commit ids in these docs and in the evaluation records point to the private history (noted at the top of this log); the reasoning and evidence stay public in WORKLOG, DECISIONS and the result files.

## W64 · 2026-11-24 · Container image and build workflow; coordination with the deployment chat
- **Coordination:** a separate chat guides the owner through the Azure portal. Agreed split: this session writes every repo file (Dockerfile, `.dockerignore`, workflow, docs); the deployment chat writes none and guides the portal steps (package visibility, image swap, scaling, secrets and settings, budget alert, smoke test, a Log Analytics learning step). Messages between the two chats go through Claude's cross-session messaging; the owner approves them.
- **Azure (owner, portal):** resource group `rg-gxp-ai`, environment `cae-gxp-ai`, container app `gxp-ai-screener`, region North Europe (the docs said West Europe; corrected), logs to Azure Monitor without a diagnostic setting yet. The app runs the Microsoft quickstart image until ours is ready.
- **Files:** `Dockerfile` (corpus and index built at image build time; a hash mismatch or a corpus version different from the source map fails the build; non-root; health check), `.dockerignore` (only requirements, app, scripts, startup script), `.github/workflows/image.yml` (build, push to ghcr.io, then start the image and smoke-test health, home page and one keyword-baseline screening). Not built locally (no Docker on this machine): the first run on GitHub is the test. The API call used by the smoke test was checked locally.
- **Next:** the owner recreates the GitHub repository; a new snapshot (with these files) is pushed; the owner runs "Build image"; the deployment chat continues with the portal steps. Before the demo is public: a `GXP_PUBLIC_DEMO=1` setting for the confidentiality notice and the demo-only audit note.

## W65 · 2026-11-24 · Public-demo setting (`GXP_PUBLIC_DEMO=1`)
- **What:** off by default; when on (the Azure deployment sets it): the intake form and quick mode show "Public demo. Do not enter confidential or company information. Use made-up or public examples. Your answers may be sent to an external AI service." (it replaces the usual confidentiality line, so the two do not repeat); the result page says under Run details that the audit log is not kept (storage resets when the container restarts; records are for demonstration only); a small "Demo" badge in the header. Built by a UI subagent (loaded ui-ux-pro-max and design-taste-frontend first, checked in its transcript); `app/config.py` `public_demo`, Jinja global in `app/main.py`. 4 tests; 316 pass. Browser-checked on a scratch server (light, dark, 375 px).

## W66 · 2026-11-24 · First image build failed on the corpus download; the 9 public documents are now part of the repo
- **Failure (GitHub Actions, first "Build image" run, log via the deployment chat):** `download_sources.py`: 7 documents ok; **AIA: not a PDF** (EUR-Lex refused the GitHub runner, a bot check page); **FDA-WL CHANGED** (the warning letter is a web page converted to text; FDA's page changed, so the text no longer matches the pinned hash). Both would also break the freeze: the source map is pinned to corpus `e97079b5633b`.
- **Fix:** the 9 source files are versioned in `data/raw/` (with `data/raw/SOURCES.md`: publisher and reuse terms for each: EU documents reusable with acknowledgement, ICH with copyright acknowledgement, FDA documents public domain); stored byte-identical (`.gitattributes`: `data/raw/* -text`, so no line-ending conversion changes a hash); the Dockerfile copies them and `download_sources.py` only checks their SHA-256 hashes (it skips files that exist), so the build needs no network for the corpus and the image matches the tested corpus exactly. Hashes verified locally. Option chosen with the deployment chat's analysis (live download with a browser header would still leave the FDA text changed, not compatible with the freeze).
- **Published** as the second release snapshot on the public repository.

## W67 · 2026-11-24 · Live on Azure Container Apps
- **URL:** https://gxp-ai-screener.bluebeach-adbc15fa.northeurope.azurecontainerapps.io (image `ghcr.io/sirsirio/gxp-ai-usecase-screener`, built by GitHub Actions from the public snapshot; second build green after W66). The owner ran a keyword-baseline and a Gemini screening successfully.
- **Lessons from the portal steps (deployment chat):** a revision that activates with the wrong ingress port (80 instead of 8000) is not retried after the port is fixed: a new revision is needed; probes copied from the quickstart image do not fit; an HTTP probe on `/api/health` made the container crash-loop, because the health endpoint loads the index and embedding model on first call and `get_index()` has no lock, so each 1-second probe on 0.5 vCPU started another load. Running with TCP probes; details and settings in `docs/DEPLOYMENT.md`.
- **Proposed fix (owner to decide):** lock around the index/embedder load, a cheap `/api/live` probe endpoint, warm-up in the background at startup, gunicorn access log. It changes when the index loads, not what it contains, so screening results and the freeze are unaffected.
- **Still to confirm (owner, with the deployment chat):** budget alert at €1, scale-to-zero observed, a separate no-billing Gemini key, the GitHub "About" box.

## W68 · 2026-11-28 · Project paused: documentation checked and brought up to date
- **Owner:** the project is at a good enough point to pause; everything must be in order to resume in about a month.
- **Done:** README brought up to date (live demo link, "every label reviewed manually" instead of "SME", the W31 numbers marked as form-1.0 results with the frozen version's own test run still to do, How it works page, guard G1b, follow-up rounds, source map principle, documents in `data/raw`, Container Apps deployment); WALKTHROUGH says which later parts are documented elsewhere; VIDEO_SCRIPT marked outdated; duplicate entry number fixed (W61a); open items rewritten (current list on top, the earlier table kept below as an archive); `docs/DEPLOYMENT.md` gained the release-snapshot procedure; the "Where things stand" section below written for the restart.

---

## Where things stand (2026-11-28) and how to resume

**State**
- **Live demo:** https://gxp-ai-screener.bluebeach-adbc15fa.northeurope.azurecontainerapps.io (Azure Container Apps, North Europe, scale to zero, public-demo notice on). Image `ghcr.io/sirsirio/gxp-ai-usecase-screener`, built by the GitHub Actions workflow "Build image". Health probes are TCP (the HTTP-probe fix is proposed, not built; see open items).
- **Public repository:** https://github.com/SirSirio/gxp-ai-usecase-screener holds release snapshots only (W63). The full history is in this local repository (`main`); the local branch `public` is what gets pushed. How to publish: `docs/DEPLOYMENT.md`, "Publishing a release snapshot".
- **Frozen version for the held-out test run:** local tag `v1.0-freeze` (prompt-1.9, rules-1.10, source map map-1.3, form-1.2, corpus `e97079b5633b`, `gemini-3.5-flash-lite`). Changes since the tag are page texts, deployment and docs only (allowed by the freeze, W59). 316 tests pass.
- **Results so far:** held-out test (W31, form-1.0, prompt-1.3): 0 dangerous errors, accuracy 0.87. Latest full dev run (W51, prompt-1.7): 0 dangerous (8 cases lost to Google's 503). Smoke run (W58, prompt-1.9, 10 dev cases): 0 dangerous, citations from the approved list 100 %.
- **Not done:** the held-out test run on `v1.0-freeze`; the LinkedIn post (draft in `media/linkedin-post.md`; its "not a single unsafe call" line should be confirmed by that run first).

**Deadline: Azure free credit expires on 2026-12-20.** Before that date, upgrade the subscription to pay-as-you-go (no cost within the free Container Apps allowance; budget alert at €1) or delete the resource group `rg-gxp-ai`. Otherwise the subscription is disabled and the live demo stops.

**Kept only on this computer (not in any repository):** `.env` (Gemini key), `media/` (15-second video, poster, LinkedIn post draft, process-flow image), `data/audit/` and `data/results/` (audit log and saved results), `data/usage/` (Gemini counter), `.claude/paraphrase.md` (settings for the paraphrase skill), `qa/**/screenshots` and `qa/**/fixes` (feature-check screenshots). The local git history is the only full history: back up the project folder.

**How to resume**
1. Read this section and the open items below; `docs/DECISIONS.md` (D18-D27) for why things are as they are; `CLAUDE.md` for the rules.
2. Run locally: `start.bat` (press R to restart a running server) or `.venv/Scripts/python -m uvicorn app.main:app`; tests: `.venv/Scripts/python -m pytest -q`.
3. Held-out test run on the frozen version (on the owner's go): `git checkout v1.0-freeze` (or check that nothing frozen changed), then a dev check `.venv/Scripts/python -m eval.run_eval --set dev --provider gemini`, then `GEMINI_MAX_RPM=3 .venv/Scripts/python -m eval.run_eval --set test --provider gemini` in the Danish morning, then `--retry-unanswered <result file>` for cases lost to HTTP 503. Report totals only; record it as a re-use of the test set (validation note §8).
4. After the test run: README, validation note and the LinkedIn post with the final numbers.
5. Publishing a change: commit on `main`, build a snapshot on `public`, push it, run "Build image" on GitHub, create a new revision in the Azure portal (`docs/DEPLOYMENT.md`).

---

## Open items
| Item | Owner | Status |
|---|---|---|
| **Azure credit expires 2026-12-20:** upgrade to pay-as-you-go or delete `rg-gxp-ai`, otherwise the demo stops | Sirio | before 2026-12-20 |
| Held-out test run on `v1.0-freeze` (dev check first; slow; `--retry-unanswered` for 503 losses) | Claude, on the owner's go | open |
| README, validation note and LinkedIn post with the final numbers | Claude + Sirio | after the test run |
| Health-probe fix: lock around the index/embedder load, `/api/live` for probes, warm-up at startup, gunicorn access log (W67; results unaffected) | Sirio decides, Claude builds | proposed |
| Confirm in Azure: budget alert at €1, scale-to-zero observed, a separate no-billing Gemini key for the demo | Sirio | open |
| Confirm the labels written at the owner's request: D010, D041, D042, D043 | Sirio | open |
| `/paraphrase` pass on the How it works page (Gemini website failed, W58) | Claude | when Gemini is available |
| Ideas, not planned: citations outside the map as "related, not verified" (W46); guidance on next steps after an accepted use (W46); give the LLM the checklist suggestion to confirm (W23, experiment); improve out-of-scope refusal and retrieval (tuned on dev only); a 2-minute walkthrough video (script outdated) | Sirio | later |
| Watch in the next dev run: Gemini reads more models as "probabilistic" (D023, D024) | Claude | next dev run |

### Open-items archive (table as of 2026-11-24; superseded by the list above)
| Item | Owner | Status |
|---|---|---|
| Review test labels (3 open cases in `eval/TESTSET_NOTES.md`) | Sirio (SME) | open |
| Confirm the D043 label (strict sibling of D026, W51) | Sirio | open |
| Gemini evaluation on dev and test sets | Claude | done: test 0.87 vs baseline 0.57 (W14) |
| Improve out-of-scope refusal (0.67; 0.5 on the W21 form sample) and primary-source retrieval (0.79) | Claude | next, tuned on dev only |
| Prompt: human review does not make a critical use non-critical (D017, W21); trust described behaviour over ticks (D032); refusal of requests to the tool | Claude | prompt-1.3 measured (W24): dev 0.83; D017/D009/D031 fixed; still open D032 (lenient), D029 (over-refusal), D035 |
| Result page: "unclear" shown as "Unsupported": fixed (W32). "Key source cited" metric inflated by control citations (W21) | Claude | metric open |
| Review the v2 cases in `review/review_cases.html` | Sirio (SME) | done: dev (W18, W19), test (W30) |
| Review page: rename "Approve" / "Needs rewrite" to "Keep original" / "Use proposed change" when a proposal was imported (W30) | Claude | done (W34) |
| Test run (v2, 70 cases) | Claude | done (W31): 0 dangerous errors, accuracy 0.87 |
| Second test run for consistency on unseen data | Sirio | not now (W32): quota, no dangerous errors |
| Review page: status buttons toggle, so a second click resets a decision (W18) | Claude | done (W19) |
| D007 ML sibling (D042) and D032 change | Sirio / Claude | done (W19); Sirio to confirm D010, D041, D042, D032 on the review page |
| Outcome labels in plain words, all nine (D18) | Claude | done (W19) |
| Keyword baseline on forms: **decided option B** (2026-11-22): trust the ticked choices first (gmp_impact yes→critical, no→non_critical or not_gmp if only business areas; ai_type llm→generative, trained_fixed→static, self_learning→dynamic, rules→non_ml, vendor_unknown→unclear; output_use informs/person_approves/auto_monitored/auto_unchecked→informs/recommends/acts_with_oversight/acts_autonomously); keywords on the free-text answers only (never on question wording) where "not sure" or blank. It acts as a "static checklist" baseline and is expected to fail on contradiction cases. | Claude | done (W22): dev 0.32 → 0.63 |
| LLM efficiency for forms (discussed 2026-11-22): (1) send answers as structured fields; (2) always include core passages A22 §1, §3.3, §10.5 and skip the tool round when they suffice → 1 call instead of 2–4; (3) stable prompt prefix for caching; (4) **experiment, not decision:** give the LLM the checklist suggestion to confirm or correct + flag contradictions; run dev with vs without, judge on the 20 contradiction cases (anchoring risk). Never let ticks decide without the LLM (self-assessment bias). | Claude | ideas 1–3 done (W23); idea 4 still an experiment |
| Evaluation harness for v2 form cases: done (W20). Label-guide additions suggested by the test writer (code generation, bots answering for a department, GMP context vs office use) | Claude / Sirio | after review |
| Follow-up loop (SME idea): done (W33 backend, W34/W38 pages). Gap: follow-up answers are lost if a follow-up round fails form validation | Claude | done (W44) |
| Validation note: known limits not measurable without real users (same people wrote cases and rules; synthetic inputs; model updates by the provider, visible via the logged model version) | Claude | before the demo |
| **G1 extension: "received" is not a check** (D038, W39/W40) | Sirio decides, Claude builds | done (W41, D23) |
| Dev run after the G1 decision (form-1.2; ~45 requests within the QuotaGuard) | Claude | done (W41): 0 dangerous, 0.83 |
| Empty "who checks" with "person approves" ticked also gets the G1b question (caught D020 live) | Sirio | confirmed by the SME (2026-11-23) |
| Gemini reads more models as "probabilistic" since the new option (D023, D024; harmless so far) | Claude | watch in the next dev run |
| Guide wording: "provides input to a GMP decision" vs "provides the evidence a GMP decision rests on" (prompt uses the latter, D22) | Sirio | decide |
| Confirm D010, D041, D042 on the review page (written at the SME's request, still unconfirmed) | Sirio | open |
| Confirm today's Gemini count in AI Studio (QuotaGuard seeded with an estimate of 346) | Sirio | open |
| Validation note: results are from form-1.0 / prompt-1.3; form-1.2 changes listed, no new test run yet | Claude | noted (W40) |
| style.css has no version tag (browsers may show old styles; Ctrl+F5) | Claude | done (W42) |
| The keyword baseline reads ticks first, so it can never show a G2 contradiction; only an LLM can (W38) | Claude | document in WALKTHROUGH |
| 42 test records in the real audit log (W16) | Sirio | keep (W32) |
| Rotate the Gemini key after testing (it was pasted in chat) | Sirio | not rotating (owner decision, 2026-11-23); the key was never in the repo |
| Confirm the source map (`app/source_map.py`) (W46) | Sirio (SME) | done: map-1.1 after an independent review, 5 changes accepted (W47) |
| Gemini dev run with prompt-1.6 and the source map (W46) | Claude | done (W47): 0 dangerous, citations in map 96 %, 3 "nobody checks" judgments without a source |
| Citations outside the map shown as "related, not verified" (middle option, W46): needs its own check before use | Sirio | later |
| Guide the proposer on what has to be done next once a use is accepted (idea, W46) | Sirio | later, out of scope for now |
| Azure deployment | Sirio + Claude | dropped for now (no account, costs money); Hugging Face Spaces planned instead (W60) |
| Upgrade the Azure free account to pay-as-you-go before **2026-12-20** (credit expires; otherwise the app stops; no cost within the free allowance) | Sirio | before 2026-12-20 |
| Deploy on Azure Container Apps (D27) | Sirio + deployment chat (portal) + Claude (image, docs) | done (W67): live; probe fix proposed; budget alert, scale-to-zero, separate key to confirm |
| Held-out test run on `v1.0-freeze` (dev check first; slow; retry provider failures) | Claude, on the owner's go | morning |
| Docs with the final numbers (README: "reviewed manually" instead of "SME"; validation note; walkthrough) and the LinkedIn post | Claude + Sirio | after the test run |
| `/paraphrase` pass on the How it works page (Gemini website failed, W58) | Claude | when Gemini is available |
| 2-minute video | Sirio | script outdated by the redesign and form-1.2: update first (W32) |
| Install the Microsoft Visual C++ Redistributable (clean DLL fix) | Sirio | optional |
