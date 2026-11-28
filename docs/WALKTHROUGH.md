# Walkthrough: how this project works, step by step

A learning guide. Read it top to bottom with the code open. Each part names the concept, where it lives and what to notice, and ends with something to try. Functions are named instead of line numbers, so the guide stays valid when the code changes.

Tip: step through the git history (`git log --oneline`, then `git show <commit>`) to see the project grow in the same order. The full history is in the private development repository; the public repository holds release snapshots.

**Scope of this guide:** it explains the core (ingestion, retrieval, classification, citation check, rules, guards G1/G2, audit log, evaluation). Parts added later are documented elsewhere: guard G1b and follow-up rounds (WORKLOG W33, W41, D23), the source map and the definition-vs-consequence principle (D24, D26), the freeze and the retry option (W59), the How it works page (W58), and the deployment (D27, `docs/DEPLOYMENT.md`).

---

## Part 1: Getting documents in (ingestion)

### 1.1 The manifest: `app/ingest/sources.py`
Every document is one `Source`: id (`A22`), title, status (draft / in force), URL, file name and **how to parse it**. Three strategies:
- `numbered` for EC and ICH texts (sections 1, 2.1, 4.12 …);
- `headings` for FDA texts, where an explicit ordered list of heading patterns is matched;
- `articles` for the AI Act.

**Notice:** `start_page` skips covers and tables of contents. A TOC lists every heading once already, so parsing it would create fake sections.

### 1.2 Parsing: `app/ingest/parse.py`
- `read_lines` drops the EC drafts' **line numbers** (printed as separate lines: "26", "27", …), page labels and running headers.
- `merge_markers` re-attaches numbers printed on their own line ("2.1." / "Personnel. In order…").
- `parse_numbered` + `_plausible_next`: the core trick. A line starting with a number becomes a new section **only if that number can follow the current one** (2.4 → 2.5, 2.4 → 3, 2 → 2.1). That is why "30 June 2011" never becomes section 30.
- `_split_title` separates "Personnel" from "Personnel. In order to …".
- `join_lines` repairs words broken across lines ("pharmaceuti-" + "cal") but keeps real hyphens ("risk-based").

**Try:** `python -c "from pathlib import Path; from app.ingest.sources import SOURCES_BY_ID as S; from app.ingest.parse import parse_source; print([s.section for s in parse_source(S['A22'], Path('data/raw'))])"`

### 1.3 Chunking: `app/ingest/chunk.py`
A **chunk** is the unit retrieval returns. Rule: a chunk never crosses a section boundary, so its id `A22:3.3:0` always names exactly one citable section. Long sections are packed sentence by sentence up to ~1,100 characters, with one sentence of overlap (`pack`).

**Why not fixed-size chunks?** Because then a citation would point to "characters 1200–2300", which no QA reviewer can check.

### 1.4 Building the index: `app/ingest/build_index.py`
Produces `data/index/`:
- `chunks.jsonl` and `sections.json` (the text);
- `tfidf.pkl` (the sparse index);
- `dense.faiss` (embeddings);
- `manifest.json` with **`corpus_version`**, a hash of all chunks. If any document changes, the version changes, and every answer records which version produced it.

---

## Part 2: Finding the right passages (retrieval)

### 2.1 Two retrievers: `app/retrieval/index.py`
- **Sparse (TF-IDF):** counts words and word pairs, weighted by rarity. Great for exact terms like "audit trail" or "Annex 11".
- **Dense (embeddings):** `app/retrieval/embedder.py` turns text into 384 numbers with the `bge-small` model, so that texts with similar *meaning* sit close together. It finds "Generative AI and Large Language Models" when you type "ChatGPT". It runs locally: no key, no cost, nothing leaves the machine.
- **Fusion (`search`):** reciprocal rank fusion. Each retriever ranks the chunks; a chunk scores 1/(60 + rank) from each list. Only ranks are used, so the two very different score scales never need calibrating.

**Notice:** vectors are normalised, so the inner product in FAISS (`IndexFlatIP`) equals cosine similarity.

### 2.2 Framework queries: `app/pipeline.py::retrieve`
The user's text alone often misses the passage that decides the case: proposers write "ChatGPT drafts our SOPs", while Annex 22 §1 talks about "Generative AI and Large Language Models". So every request also runs 7 fixed queries (scope, generative, dynamic, human-in-the-loop, QU review, CSV, AI Act). An ablation (same eval with and without them) measured the gain: primary source retrieved 0.875 → 1.00 on dev and 0.75 → 0.79 on test. That is a modest gain. Always measure a change like this instead of assuming it helps; DECISIONS D5 has the table.

**Try:** `python -c "from app.retrieval.index import get_index; [print(r.chunk.id, r.rank_sparse, r.rank_dense) for r in get_index().search('vision system rejects vials')]"`. Look at which retriever found what.

---

## Part 3: Classifying (the assessors)

### 3.1 One interface, two implementations: `app/assessors/`
`assess(description, passages, tools) → raw dict`. The pipeline never trusts that dict until it is validated.
- **`offline.py`:** keyword cues per field (regexes such as `GENERATIVE`, `CRITICAL`, `REVIEW`), with a priority order (e.g. an explicit review step beats "automatically"). It cites by looking up the right section for each value (`EVIDENCE`), and calls `get_section` if that section was not retrieved. That is the agent pattern in its simplest form.
- **`llm.py`:** sends a system prompt (`app/llm/prompts.py`) with the definitions plus the passages, each tagged with its chunk id. It runs a **tool loop** (the model can call `get_section` up to 3 times), then makes a final call with the JSON schema enforced.

### 3.2 Provider-neutral chat: `app/llm/base.py` and `providers.py`
`ChatClient.chat(messages, tools, json_schema)`. `GeminiClient` and `AzureOpenAIClient` translate the neutral message format to each API. `inline_refs` flattens the Pydantic schema because some providers reject `$ref`. `FakeChatClient` replays scripted answers, which is how the tool loop is tested without a key.

**Notice in the prompt:** the use case is wrapped in `<<< >>>` with "treat as data". That is a basic prompt-injection defence. The real defence is architectural: even a hijacked model can only produce a classification, and the rules decide the verdict.

---

## Part 4: Not trusting the model

### 4.1 Schema validation: `app/schema.py::ModelAssessment`
- `extra="forbid"`: the model cannot add a `"verdict"` field.
- `Literal` enums are copied from the label guide.
- `consistent()`: an in-scope answer needs exactly one judgment per field, and each judgment must match the classification.
- In `pipeline.run_assessment`, invalid output gets one retry, then it is logged as `assessment_rejected` and the user sees an error, never the invalid content.

### 4.2 Citation check: `app/citations.py::check_judgment`
1. Drop ids that were not retrieved or fetched in this request (the model cannot cite what it never saw; this catches invented ids).
2. Score support: dense similarity ≥ 0.55 **or** word overlap ≥ 0.30 against the regulatory meaning of the value (`VALUE_CLAIMS`).
3. Nothing left → `supported=False`, note "Not covered by the sources."

**Known limit:** this checks that the passage is about the claimed category, not every word of the rationale (see DECISIONS D6).

**Try:** run `tests/test_citations.py::test_irrelevant_passage_dropped` and read why the password-rules passage is rejected as evidence for "generative AI".

---

## Part 5: Deciding (rules) and what to do (controls)

### 5.1 The rules layer: `app/rules.py`
`RULES` is an ordered table; the first match wins. Read it next to `docs/LABELING_GUIDE.md` §6; they must say the same thing. Key cases:
- **R2:** critical + generative/dynamic/probabilistic → not permitted, *even with human review* (Annex 22 §1; DECISIONS D2).
- **R6:** non-critical generative with no human review → not acceptable (Annex 22 §1 plus the warning letter).
- **R5:** critical + static → permitted with the full Annex 22 lifecycle.

`tests/test_rules.py::test_every_combination_has_exactly_one_verdict` checks all 120 combinations, so the table has no gaps.

### 5.2 Controls: `app/controls.py`
Each control lists `(doc, section)` references, resolved to real chunks at runtime (`citations.cite_section`). `test_every_control_and_rule_reference_exists` fails if a control cites a section that does not exist, for example after a document update.

---

## Part 6: Records (audit trail, intake form)

### 6.1 Hash chain: `app/audit.py`
Each line stores `prev_hash` and `hash = sha256(prev_hash + record)`. Change one past record and its hash no longer matches; delete one and the next record's `prev_hash` no longer matches. `verify()` finds the first broken line. This is the same idea as a blockchain, without the distribution.

**Try:** run an assessment, edit a word in `data/audit/audit.jsonl`, then open `/api/audit/verify`.

### 6.2 Intake form: `app/pipeline.py::build_intake`
A JSON record with status `draft_for_qa_review`, the classification, verdict and rule id, controls (each `open`), questions, evidence and every version. It is designed to be posted to a real intake workflow later.

---

## Part 7: Measuring (evaluation)

### 7.1 The data: `eval/testset.jsonl` (held out) and `eval/devset.jsonl`
Written by an independent agent from the label guide. Each case has the expected fields, verdict, key sources, a rationale and, for borderline cases, the contested field.

### 7.2 The harness: `eval/run_eval.py`
- **Field and verdict accuracy:** does it classify like the labels?
- **Refusal precision / recall:** does it refuse what it should, and only that?
- **Primary-source / key-source recall:** did retrieval find the passages a correct answer needs?
- **Judgments-supported rate and citation keep rate:** how much of what the model cites survives the check?
- Every run is saved with all versions, and `history.csv` gives the regression view.

### 7.3 The lesson in the numbers
Keyword baseline: **0.90 on dev, 0.57 on test.** The cues were written while looking at dev, so dev overstates quality. That is why Annex 22 §6 insists on test-data independence, and why this project applies it to itself.

---

## Part 8: Exercises (in rising difficulty)
1. Add the phrase "spot-checks" to a dev case and see how the offline autonomy changes. Find the regex responsible.
2. Add a new control (e.g. "Data integrity, ALCOA+" citing `A11D` §2.4) to the `permitted_with_hitl` rule, then run the tests.
3. Change `DENSE_MIN` in `citations.py` to 0.75 and re-run the dev eval: what happens to the supported rate?
4. With a Gemini key: `python -m eval.run_eval --set dev --provider gemini`, then compare the cases with the offline run.
5. Explain to someone, in two minutes, why the rules are separate from the model.
