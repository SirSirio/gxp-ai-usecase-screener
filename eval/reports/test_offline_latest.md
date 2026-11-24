# Evaluation report: test set, provider `offline`

Run 2026-11-22T06:32:25+00:00 · model `keyword-rules` · prompt `offline-1.1` · rules `rules-1.1` · corpus `e97079b5633b` · app `0.1.0` · git `a6a1498-dirty`

| Metric | Value |
|---|---|
| n | 30 |
| schema valid rate | 1.0 |
| verdict accuracy | 0.567 |
| in scope accuracy | 0.933 |
| gmp relevance accuracy | 0.5 |
| model type accuracy | 0.875 |
| autonomy accuracy | 0.458 |
| verdict accuracy by category | borderline: 0.5, clear: 0.583, out_of_scope: 0.667 |
| refusal precision | 1.0 |
| refusal recall | 0.667 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.585 |
| key source recall cited | 0.604 |
| primary source recall retrieved | 0.792 |
| judgments supported rate | 1.0 |
| citation keep rate | 1.0 |
| mean latency ms | 163 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | annex22_full | 2 |
| annex22_full | permitted_risk_based | 2 |
| hitl_required | hitl_required | 2 |
| needs_more_information | needs_more_information | 2 |
| not_ai_annex11 | needs_more_information | 1 |
| not_ai_annex11 | not_ai_annex11 | 1 |
| not_permitted_critical | hitl_required | 1 |
| not_permitted_critical | needs_more_information | 2 |
| not_permitted_critical | not_permitted_critical | 2 |
| out_of_scope | needs_more_information | 1 |
| out_of_scope | out_of_scope | 4 |
| out_of_scope | permitted_with_hitl | 1 |
| outside_gmp | needs_more_information | 2 |
| outside_gmp | not_permitted_critical | 1 |
| permitted_risk_based | needs_more_information | 2 |
| permitted_risk_based | permitted_risk_based | 1 |
| permitted_with_hitl | permitted_with_hitl | 3 |
