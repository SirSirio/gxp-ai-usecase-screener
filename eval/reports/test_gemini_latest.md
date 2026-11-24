# Evaluation report: test set, provider `gemini`

Run 2026-11-21T19:55:01+00:00 · model `gemini-3.5-flash-lite` · prompt `prompt-1.2` · rules `rules-1.1` · corpus `e97079b5633b` · app `0.1.0` · git `742d2ba-dirty`

| Metric | Value |
|---|---|
| n | 30 |
| schema valid rate | 1.0 |
| verdict accuracy | 0.867 |
| in scope accuracy | 0.933 |
| gmp relevance accuracy | 0.917 |
| model type accuracy | 1.0 |
| autonomy accuracy | 0.75 |
| verdict accuracy by category | borderline: 0.833, clear: 1.0, out_of_scope: 0.667 |
| refusal precision | 1.0 |
| refusal recall | 0.667 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.585 |
| key source recall cited | 0.679 |
| primary source recall retrieved | 0.792 |
| judgments supported rate | 0.897 |
| citation keep rate | 1.0 |
| mean latency ms | 7563 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | annex22_full | 4 |
| hitl_required | hitl_required | 2 |
| needs_more_information | needs_more_information | 1 |
| needs_more_information | permitted_with_hitl | 1 |
| not_ai_annex11 | not_ai_annex11 | 2 |
| not_permitted_critical | not_permitted_critical | 5 |
| out_of_scope | out_of_scope | 4 |
| out_of_scope | outside_gmp | 1 |
| out_of_scope | permitted_with_hitl | 1 |
| outside_gmp | outside_gmp | 2 |
| outside_gmp | permitted_with_hitl | 1 |
| permitted_risk_based | permitted_risk_based | 3 |
| permitted_with_hitl | permitted_with_hitl | 3 |
