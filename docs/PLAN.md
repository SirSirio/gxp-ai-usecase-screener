# Plan

A lightweight spec: what each step delivers and how it is checked. Status is updated as work lands.

| # | Step | Delivers | Done when | Status |
|---|---|---|---|---|
| 0 | Sources | 9 public documents downloaded, `scripts/download_sources.py` with URLs + SHA-256 | Script re-downloads and hashes match | ✅ |
| 1 | Core loop | Parse PDFs → section-aware chunks → hybrid index → retrieve → answer with a valid citation (offline assessor) | `pytest` green; a question returns a passage whose id resolves to the right section | ✅ |
| 2 | Classification + rules + intake | Pydantic schema, deterministic rules layer, controls catalogue, JSON intake form | Unit test per rule; schema rejects invalid output | ✅ |
| 3 | Evaluation | Test set (held out) + dev set, scoring script, stored results per version | `eval.run_eval` writes a report with all metrics | ✅ labels reviewed (W18, W30); test run once on form-1.0 (W31); final run on `v1.0-freeze` next (W59) |
| 4 | Tool call + audit | `get_section` tool (agent pattern), hash-chained audit log | Tool loop tested with a scripted fake LLM; audit chain verifies | ✅ |
| 5 | Front end | Web form → result page, JSON download | Manual run + API test | ✅ redesigned (landing, submit, follow-up rounds, source pages, How it works); feature check W50 |
| 6 | LLM providers | Gemini + Azure OpenAI clients behind one interface | Gemini run live and evaluated (0.87 on test); Azure OpenAI client still untested live | ✅ Gemini |
| 7 | Azure deployment | Azure Container Apps, scale to zero, budget alert (D27) | Needs the owner's personal Azure free account | ⏳ decided, after the test run |
| 8 | Docs | README (business first), validation note, walkthrough, decisions, architecture | Reviewed by an independent reader agent | ✅; final numbers after the test run; 15-s demo video made (W60) |

## Acceptance criteria
Superseded by the SME's decision D19 (zero dangerous errors first, accuracy secondary; `docs/VALIDATION_NOTE.md` §4). The first proposal is kept below for the record.

### First proposal (before D19)
Measured on the held-out test set:
- Schema-valid rate: 100 % (invalid output is never shown, so this is a reliability metric).
- Verdict accuracy ≥ 80 % for the LLM assessor; the offline baseline is reported for comparison, not held to the bar.
- Out-of-scope refusal: recall ≥ 90 %, no in-scope case refused that is labelled `clear`.
- Citation validity: 100 % of shown citations resolve to a real chunk and pass the support check.
- Key-source recall@k (retrieval): ≥ 85 %.

These are proposals. Final values are the SME's call (Annex 22 §4.2), recorded in `docs/VALIDATION_NOTE.md`.
