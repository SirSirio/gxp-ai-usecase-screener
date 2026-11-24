# 2-minute screen recording: script

Record at 1080p with the app running locally (`uvicorn app.main:app`) or on Azure. Speak slowly; about 280 words in total.

| Time | Show | Say |
|---|---|---|
| 0:00–0:15 | Home page | "Every pharma company is now asking which AI uses are acceptable under GMP, and with which controls. Draft Annex 22 and an April 2026 FDA warning letter about unreviewed AI-drafted documents made it urgent. This tool is a consistent first screen for AI proposals, and QA still decides." |
| 0:15–0:45 | Click the *no review* example → result page: red verdict, both quotes | "Here an AI agent writes the weekly deviation summary and emails it out with nobody checking. The verdict is 'Not as described: add human review of each output'. Each judgment shows the exact passage behind it: Annex 22 section 1, and the warning letter, where FDA says AI output must be reviewed and cleared by the quality unit." |
| 0:45–1:05 | Scroll: classification, grid, rule id | "The model only classifies: GMP relevance, model type, autonomy. The verdict comes from a deterministic rules layer. This is rule R6, so the same input always gets the same verdict, and QA can review the rules line by line." |
| 1:05–1:20 | Open the controls, click *Download JSON* | "It lists the required controls with their sources, and drafts an intake form as JSON for the IT/QA process." |
| 1:20–1:45 | Terminal: `pytest -q`, then `eval.run_eval --set test`, and `history.csv` | "I treated the tool like a GxP system. There is a held-out test set that I never looked at while tuning. The keyword baseline gets 90 percent of outcomes right on the dev set but 57 percent on the held-out set, and that gap is why test-data independence matters. Every run is stored with its prompt, rules and corpus versions." |
| 1:45–2:00 | `docs/VALIDATION_NOTE.md` or the audit verify endpoint | "Every request goes to a hash-chained audit trail, and there is a one-page validation note: intended use, risk, acceptance criteria, change control. The same pattern fits a corporate intake process on the Microsoft stack." |

Before recording: the script predates the redesign and the v2 results. Update it after the redesign (current headline: 0 dangerous errors and 87 % on 70 held-out cases, keyword checklist 13 dangerous and 59 %). Do not show any company data.
