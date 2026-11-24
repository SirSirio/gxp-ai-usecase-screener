# Evaluation report: dev set, provider `gemini`

Run 2026-11-21T19:51:04+00:00 · model `gemini-3.5-flash-lite` · prompt `prompt-1.2` · rules `rules-1.1` · corpus `e97079b5633b` · app `0.1.0` · git `742d2ba-dirty`

| Metric | Value |
|---|---|
| n | 10 |
| schema valid rate | 1.0 |
| verdict accuracy | 1.0 |
| in scope accuracy | 1.0 |
| gmp relevance accuracy | 1.0 |
| model type accuracy | 1.0 |
| autonomy accuracy | 0.875 |
| verdict accuracy by category | borderline: 1.0, clear: 1.0, out_of_scope: 1.0 |
| refusal precision | 1.0 |
| refusal recall | 1.0 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.562 |
| key source recall cited | 0.688 |
| primary source recall retrieved | 1.0 |
| judgments supported rate | 0.917 |
| citation keep rate | 0.963 |
| mean latency ms | 6657 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | annex22_full | 1 |
| hitl_required | hitl_required | 1 |
| needs_more_information | needs_more_information | 1 |
| not_ai_annex11 | not_ai_annex11 | 1 |
| not_permitted_critical | not_permitted_critical | 1 |
| out_of_scope | out_of_scope | 2 |
| outside_gmp | outside_gmp | 1 |
| permitted_risk_based | permitted_risk_based | 1 |
| permitted_with_hitl | permitted_with_hitl | 1 |
