# Feature check, 2026-11-24

> Screenshots (`screenshots/`, `fixes/`) are kept on the owner's machine and are not in the repository (size); the links below work locally. Fixes for the fail and the flags: WORKLOG W50.

Functional end-to-end check of the GxP AI Use-Case Assistant (not a model evaluation). Scratch servers only; inputs are dev cases from `eval/v2/dev_cases.jsonl` or synthetic forms written for this check. Held-out test sets were not opened. No app code, tests or docs were changed.

## Summary

**32 checks:** 21 pass, 1 fail, 7 flag, 3 info.

Every assessment that was run is saved in `responses/` (one JSON per request id, plus the two scratch audit logs). `results.json` holds one record per check and an index of all responses.

## Flagged for the owner

- **F02b (FLAG)** Question count: landing says nine questions, form counts ten. Screenshot: [screenshots/F01_landing.png](screenshots/F01_landing.png)
- **F03k (FLAG)** 'Pending clarification' explanation names both GMP relevance and model type even when only one is unclear. Screenshot: [screenshots/F03_D004_result.png](screenshots/F03_D004_result.png) · request c84b9cfea94c
- **F04b (FLAG)** Run details do not show the source map version (map-1.1) or the rules version. Screenshot: [screenshots/F04_run_details.png](screenshots/F04_run_details.png) · request 35d94d20d75d
- **F06b (FLAG)** After the last round: label still says "update ... details below" and "Screen again with Gemini" is still offered. Screenshot: [screenshots/F06_round3.png](screenshots/F06_round3.png) · request 84ad504473f8
- **F08b (FLAG)** daily_budget and auth messages do not say that the answers are kept. Screenshot: [screenshots/F08_daily_budget_collapsed.png](screenshots/F08_daily_budget_collapsed.png) · request c1bc3cb0613e, a64964316ec3
- **F10e (FAIL)** Valid citations dropped when Gemini writes chunk ids in square brackets: every judgment shows 'Unsupported / Not covered by the sources'. Screenshot: [screenshots/F10b_gemini_G1b.png](screenshots/F10b_gemini_G1b.png) · request 8253096661bb, 18516db9a909
- **F11b (FLAG)** 375 px: the adaptiveness/autonomy grid scrolls sideways and the position mark starts off-screen. Screenshot: [screenshots/F11_grid_375.png](screenshots/F11_grid_375.png)
- **F11c (FLAG)** Section pages repeat the subsection title at the start of the body text. Screenshot: [screenshots/F11_section_dark_375.png](screenshots/F11_section_dark_375.png)

## All checks

| ID | Area | Check | Provider | Status | Expected / got | Screenshot |
|---|---|---|---|---|---|---|
| F01 | 1 Landing and navigation | Landing page, navigation landing -> submit -> sources -> back, skip link, page titles | offline | pass |  | [png](screenshots/F01_landing.png) |
| F02 | 2 Form | Fill example buttons, Clear form, answered counters, inline validation, required hint | offline | pass |  | [png](screenshots/F02_example_1.png) |
| F02b | 2 Form | Question count: landing says nine questions, form counts ten | offline | flag |  | [png](screenshots/F01_landing.png) |
| F03a | 3 Outcome types (offline) | Full assessment, outcome type 'should not proceed' with dev case D003 | offline | pass | not_permitted_critical / not_permitted_critical | [png](screenshots/F03_D003_result.png) |
| F03b | 3 Outcome types (offline) | Full assessment, outcome type 'add human review' with dev case D013 | offline | info | not_permitted_critical / hitl_required | [png](screenshots/F03_D013_result.png) |
| F03c | 3 Outcome types (offline) | Full assessment, outcome type 'full Annex 22 controls' with dev case D001 | offline | pass | annex22_full / annex22_full | [png](screenshots/F03_D001_result.png) |
| F03d | 3 Outcome types (offline) | Full assessment, outcome type 'generative AI with a person approving' with dev case D005 | offline | pass | permitted_with_hitl / permitted_with_hitl | [png](screenshots/F03_D005_result.png) |
| F03e | 3 Outcome types (offline) | Full assessment, outcome type 'risk-based' with dev case D006 | offline | pass | permitted_risk_based / permitted_risk_based | [png](screenshots/F03_D006_result.png) |
| F03f | 3 Outcome types (offline) | Full assessment, outcome type 'not ML / Annex 11' with dev case D007 | offline | pass | not_ai_annex11 / not_ai_annex11 | [png](screenshots/F03_D007_result.png) |
| F03g | 3 Outcome types (offline) | Full assessment, outcome type 'not GMP' with dev case D002 | offline | pass | outside_gmp / outside_gmp | [png](screenshots/F03_D002_result.png) |
| F03h | 3 Outcome types (offline) | Full assessment, outcome type 'not assessed (out of scope)' with dev case D009 | offline | pass | out_of_scope / out_of_scope | [png](screenshots/F03_D009_result.png) |
| F03i | 3 Outcome types (offline) | Full assessment, outcome type 'pending clarification' with dev case D004 | offline | pass | needs_more_information / needs_more_information | [png](screenshots/F03_D004_result.png) |
| F03j | 3 Outcome types (offline) | Offline scan of all 41 dev cases through POST /api/assess (to choose the browser cases) | offline | info |  |  |
| F03k | 3 Outcome types (offline) | 'Pending clarification' explanation names both GMP relevance and model type even when only one is unclear | offline | flag |  | [png](screenshots/F03_D004_result.png) |
| F04 | 4 Result page content | Outcome label + tone, decided by rule, judgments with sources, controls, draft notice, JSON download, intake record, run details | offline | pass |  | [png](screenshots/F04_result_top.png) |
| F04b | 4 Result page content | Run details do not show the source map version (map-1.1) or the rules version | offline | flag |  | [png](screenshots/F04_run_details.png) |
| F05 | 5 Source pages | Citation links open /section pages with highlight, Go to the passage, official link; unknown section 404; /sources links | offline | pass |  | [png](screenshots/F05_section_page_top.png) |
| F06 | 6 Follow-up loop (offline) | Pending clarification -> answer follow-up -> round 2 -> round 3 -> no further round + new-proposal message | offline | pass |  | [png](screenshots/F06_round1.png) |
| F06b | 6 Follow-up loop (offline) | After the last round: label still says "update ... details below" and "Screen again with Gemini" is still offered | offline | flag |  | [png](screenshots/F06_round3.png) |
| F07 | 7 Follow-up error path | Follow-up round with a too-short description -> error page keeps answers, shows round N of 3, hidden round/parent; fix -> round N linked to parent | offline | pass |  | [png](screenshots/F07_round1_followup_filled.png) |
| F08 | 8 API error display | Plain message, collapsed technical details, answers kept: kinds overloaded, daily_budget, auth, timeout | fake Gemini client (scratch server 8011, no real API call) | pass |  | [png](screenshots/F08_overloaded_collapsed.png) |
| F08b | 8 API error display | daily_budget and auth messages do not say that the answers are kept | fake Gemini client | flag |  | [png](screenshots/F08_daily_budget_collapsed.png) |
| F09 | 9 Quick mode and JSON API | /quick works; POST /api/assess returns a result (offline) | offline | pass |  | [png](screenshots/F09_quick_result.png) |
| F10a | 10 Gemini | Gemini, normal clear case (dev D001, label annex22_full) | gemini | pass | annex22_full / annex22_full | [png](screenshots/F10a_gemini_D001.png) |
| F10b | 10 Gemini | Guard G1b: 'person approves' ticked, who checks = 'QA receives it', non-critical LLM use | gemini | pass | needs_more_information / needs_more_information | [png](screenshots/F10b_gemini_G1b.png) |
| F10c | 10 Gemini | Guard G2 contradiction ('Yes, directly' vs ideas through change control), then 'No, only indirectly' in round 2 | gemini | pass | needs_more_information -> proceed / needs_more_information -> permitted_with_hitl | [png](screenshots/F10c_gemini_G2_round1.png) |
| F10d | 10 Gemini | Gemini follow-up question with a free-text answer box, answered (plus error path with the free-text answer kept) | gemini | pass | permitted_with_hitl / permitted_with_hitl | [png](screenshots/F10d_error_page_keeps_free_text_answer.png) |
| F10e | 10 Gemini | Valid citations dropped when Gemini writes chunk ids in square brackets: every judgment shows 'Unsupported / Not covered by the sources' | gemini | fail |  | [png](screenshots/F10b_gemini_G1b.png) |
| F10f | 10 Gemini | Real Gemini timeout during a follow-up round: plain message, round and all answers kept | gemini | info |  | [png](screenshots/F10d_real_gemini_timeout_round2_kept.png) |
| F11 | 11 Visual and accessibility | Landing, form, result, section page: light and dark, 1280 and 375 px, keyboard focus, console errors | offline | pass |  | [png](screenshots/F11_landing_light_1280.png) |
| F11b | 11 Visual and accessibility | 375 px: the adaptiveness/autonomy grid scrolls sideways and the position mark starts off-screen | offline | flag |  | [png](screenshots/F11_grid_375.png) |
| F11c | 11 Visual and accessibility | Section pages repeat the subsection title at the start of the body text | offline | flag |  | [png](screenshots/F11_section_dark_375.png) |

## Details of fail and flag items

### F02b · FLAG · Question count: landing says nine questions, form counts ten

- **What I did (inputs):** Open / and /submit
- **Expected:** The landing page and the form give the same number of questions
- **Observed:** The landing page says "Describe your idea in nine questions", "Nine short questions..." and "Nine questions, and only the task description is required" (README also says 9 questions). The form counter says "0 of 10 questions answered" (title, what, AI type, areas, GMP impact, output use, who checks, replaces check, data, source = 10).
- **Why flagged:** Copy inconsistency the owner should decide on: either title is not counted as a question in the copy, or the copy is out of date since form-1.2.
- **Request ids:** none
- **Screenshots:** [screenshots/F01_landing.png](screenshots/F01_landing.png), [screenshots/F02_example_1.png](screenshots/F02_example_1.png)

### F03k · FLAG · 'Pending clarification' explanation names both GMP relevance and model type even when only one is unclear

- **What I did (inputs):** Dev case D004 (CDS AI peak integration add-on), offline; GMP question ticked 'Yes, directly', AI type 'A supplier's AI feature, details unknown'
- **Expected:** The outcome text names what is actually missing (here: the model type only)
- **Observed:** Outcome text: 'The description does not say enough to decide whether the use is GMP-critical or what kind of model it is. Both change the verdict.' while the Classification panel shows GMP relevance = GMP-critical (supported, sourced) and only Model type = Unclear. The follow-up correctly asks only about the model type. The text is fixed in rule R3-unclear (app/rules.py line 110) for both causes.
- **Why flagged:** Wording may confuse a proposer who already answered the GMP question clearly; owner to decide whether R3 should name only the unclear field.
- **Request ids:** c84b9cfea94c
- **Screenshots:** [screenshots/F03_D004_result.png](screenshots/F03_D004_result.png)

### F04b · FLAG · Run details do not show the source map version (map-1.1) or the rules version

- **What I did (inputs):** Any result page, open "Run details" (request 35d94d20d75d)
- **Expected:** Versions shown in the app: prompt, rules-1.6 and the source map version
- **Observed:** Run details list Prompt offline-1.4 and Corpus e97079b5633b, but no Rules and no Source map entry. rules-1.6 appears only in the outcome line ("Decided by rule ... (rules-1.6)"). map-1.1 appears nowhere on the page; it is in the saved result, the audit record and the downloaded intake JSON (generated_by.source_map_version).
- **Why flagged:** The checklist expects the source map version to be visible in the app; owner to decide whether Run details should add Rules and Source map rows (D24 says the map version is recorded with every result).
- **Request ids:** 35d94d20d75d
- **Screenshots:** [screenshots/F04_run_details.png](screenshots/F04_run_details.png)

### F06b · FLAG · After the last round: label still says "update ... details below" and "Screen again with Gemini" is still offered

- **What I did (inputs):** Round 3 result of the F06 chain (84ad504473f8)
- **Expected:** At the end of the loop the page gives one clear next step (start a new proposal)
- **Observed:** Outcome label: "Pending clarification: update any missing or conflicting details below", but below there is nothing to update (only the open question and "Start a new proposal"). The "Compare with another classifier" form is still shown with "Screen again with: Gemini gemini-3.5-flash-lite"; it re-posts the form with round=3, so a further screening of the same proposal is possible after the 3-round limit (not tried, to save Gemini quota).
- **Why flagged:** Mixed message at the end of the loop; owner to decide whether the label wording and the compare button should change at round 3 of 3.
- **Request ids:** 84ad504473f8
- **Screenshots:** [screenshots/F06_round3.png](screenshots/F06_round3.png)

### F08b · FLAG · daily_budget and auth messages do not say that the answers are kept

- **What I did (inputs):** F08 runs with kinds daily_budget (c1bc3cb0613e) and auth (a64964316ec3)
- **Expected:** Every API error message reassures the proposer the same way (the answers are kept)
- **Observed:** overloaded, timeout (and rate_limit, network, invalid_output in FAILURE_MESSAGES) say "Your answers are kept"; daily_budget ("Today's Gemini budget for this app is used up...") and auth ("Gemini did not accept the app's API key...") do not, although the answers are kept on the page. After any error the classifier select stays on Gemini, while the daily_budget/auth messages tell the user to choose the keyword baseline.
- **Why flagged:** Minor wording consistency; owner to decide whether all failure messages should share the reassurance and whether the selector should switch to the baseline for non-retryable kinds.
- **Request ids:** c1bc3cb0613e, a64964316ec3
- **Screenshots:** [screenshots/F08_daily_budget_collapsed.png](screenshots/F08_daily_budget_collapsed.png), [screenshots/F08_auth_collapsed.png](screenshots/F08_auth_collapsed.png)

### F10e · FAIL · Valid citations dropped when Gemini writes chunk ids in square brackets: every judgment shows 'Unsupported / Not covered by the sources'

- **What I did (inputs):** F10b form (LLM training quiz, who checks 'QA receives it'), Gemini; and its round 2 (F10d)
- **Expected:** Citations to map paragraphs are kept and shown as sources
- **Observed:** In both results (8253096661bb, 18516db9a909) Gemini returned citations as "[A22:1:1]" and "[A22:3.3:0]" (raw_output in the audit record, proposed_ids in the saved result). The citation check compares the raw string with the allowed ids, so all were dropped: GMP relevance, Model type and Autonomy each show the badge 'Unsupported' and 'Not covered by the sources', plus the warning 'No supporting passage found for: gmp_relevance, model_type, autonomy'. Without the brackets these ids are in the retrieved set and in the source map for those answers (source_map.describe returns an entry for non_critical/generative/recommends + A22:1:1 and recommends + A22:3.3:0). The other Gemini results cite the same ids without brackets and show sources. Likely cause: the prompt tags passages and the map list as "[<chunk id>]" (app/llm/prompts.py lines 82 and 102) and app/citations.py check_judgment does not strip brackets.
- **Why flagged:** Clear wrong behaviour: correct, map-approved citations are hidden and the page tells the proposer the judgments are not backed by any source. Outcome unaffected (rules do not depend on citations).
- **Request ids:** 8253096661bb, 18516db9a909
- **Screenshots:** [screenshots/F10b_gemini_G1b.png](screenshots/F10b_gemini_G1b.png), [screenshots/F10d_round2_after_free_text_answer.png](screenshots/F10d_round2_after_free_text_answer.png)

### F11b · FLAG · 375 px: the adaptiveness/autonomy grid scrolls sideways and the position mark starts off-screen

- **What I did (inputs):** Result 'Unchecked deviation summary' (offline) at 375x812, light
- **Expected:** The marked grid cell is visible without sideways scrolling, or the scroll is obvious
- **Observed:** The grid sits in .table-scroll (294 px visible, 520 px wide). The marked cell (Locked, AI acts alone) is at x=490-552 in a 360 px viewport, so it is hidden until the user swipes the table; the 'AI recommends' header is cut ('A recomm'). No scroll hint; the wrapper has no tabindex/label. The position is also written in text above the grid ('Position: Locked (frozen in use), AI acts alone.'), so no information is lost.
- **Why flagged:** Visual/mobile polish for the owner to judge (low impact).
- **Request ids:** none
- **Screenshots:** [screenshots/F11_grid_375.png](screenshots/F11_grid_375.png), [screenshots/F11_result_light_375.png](screenshots/F11_result_light_375.png)

### F11c · FLAG · Section pages repeat the subsection title at the start of the body text

- **What I did (inputs):** /section?doc=A22&section=3 (dark, 375 px) and other A22 sections
- **Expected:** Heading once, then the text
- **Observed:** Heading '§3.1 Intended use' is followed by a paragraph starting 'Intended use. The intended use of a model...'; '§3.2 Subgroups' by 'Subgroups. Where applicable...'. The repeated words come from the PDF text (run-in headings), not from the template.
- **Why flagged:** Reads like a duplicate; owner to decide whether the reader page should strip a leading run-in title that equals the heading (the page already says paragraph breaks were added for reading).
- **Request ids:** none
- **Screenshots:** [screenshots/F11_section_dark_375.png](screenshots/F11_section_dark_375.png)

## Setup

- **Git commit:** `4cc0d5f Open items: Gemini key not rotated (owner decision)` (working tree clean apart from this `qa/` folder)
- **Versions shown in the app:** app 0.1.0; offline prompt `offline-1.4`; Gemini prompt `prompt-1.6`; rules `rules-1.6` (in the outcome line); corpus `e97079b5633b`; Gemini model `gemini-3.5-flash-lite`. Source map `map-1.1` is in the saved result, audit record and intake JSON, not on the page (F04b).
- **Scratch server 8010:** `uvicorn` started from a small launcher that calls `app.config.use_settings(Settings(provider='offline', audit_dir=<temp>, results_dir=<temp>))` (audit and results folders are not env vars in `app/config.py`). Gemini was offered because `.env` holds the key.
- **Scratch server 8011:** same launcher plus `app.main.get_assessor = lambda p: LLMAssessor(FailingClient(), use_tools=False)`; the fake client raised `ProviderError(..., kind=<kind>)` read from a file, kinds overloaded, daily_budget, auth, timeout. No real API call, no quota use.
- **Owner's server on port 8000:** not touched. Both scratch servers stopped at the end.
- **Gemini requests:** usage file `data/usage/gemini_requests.json` before `{"2026-11-23": 100}`, after `{"2026-11-23": 108}`: **8 requests** (6 assessments, one of which ended in a real timeout; the guard counts every HTTP attempt). Cap 15.
- **Real audit log** `data/audit/audit.jsonl`: **78 lines before, 78 after** (unchanged). `data/results/`: 72 files before and after.
- **Browser:** Playwright (Chromium) via MCP; viewport 1280x900 and 375x812; light and dark via emulated `prefers-color-scheme`. Helper scripts were placed in the git-ignored `.playwright-mcp/` folder.
- **Skills loaded before the visual pass:** ui-ux-pro-max, design-taste-frontend.

## Files

- `results.json`: setup, counts, one record per check (inputs, expected, observed, status, screenshots, request ids), and `responses` index (request id, provider, round, parent, verdict, rule, checks that used it).
- `responses/`: 75 saved result JSONs (offline scan of all 41 dev cases, browser runs, API runs, 5 Gemini results; the timed-out Gemini request has no result, only an audit record), two `F04_downloaded_ai-intake-*.json` files (what the Download JSON button produced; 3e1f57fae3a7 is from a first F04 attempt whose script stopped after the download), `scratch_audit_8010.jsonl`, `scratch_audit_8011_fake_errors.jsonl`.
- `screenshots/`: PNGs named by check id.
