# Evaluation report: test_v2, provider `gemini`

Cases: v2, 70 evaluated, selection {'limit': None}

Run 2026-11-22T12:17:12+00:00 · model `gemini-3.5-flash-lite` · prompt `prompt-1.3` · rules `rules-1.3` · corpus `e97079b5633b` · app `0.1.0` · git `0f9f242`

| Metric | Value |
|---|---|
| n | 70 |
| dangerous errors | 0 |
| dangerous errors on gmp critical | 0 |
| wrongly refused | 0 |
| wrongly refused dangerous | 0 |
| wrongly screened | 0 |
| stricter or not yet | 9 |
| forms rejected by validation | 1 |
| schema valid rate | 1.0 |
| verdict accuracy | 0.871 |
| in scope accuracy | 1.0 |
| gmp relevance accuracy | 0.932 |
| model type accuracy | 0.949 |
| autonomy accuracy | 0.864 |
| verdict accuracy by category | borderline: 0.8, clear: 0.917, out_of_scope: 1.0 |
| refusal precision | 1.0 |
| refusal recall | 1.0 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.669 |
| key source recall cited | 0.714 |
| primary source recall retrieved | 1.0 |
| judgments supported rate | 0.966 |
| citation keep rate | 0.985 |
| mean latency ms | 6064 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | annex22_full | 6 |
| annex22_full | not_permitted_critical | 1 |
| hitl_required | hitl_required | 6 |
| hitl_required | needs_more_information | 1 |
| needs_more_information | needs_more_information | 8 |
| not_ai_annex11 | needs_more_information | 1 |
| not_ai_annex11 | not_ai_annex11 | 4 |
| not_permitted_critical | not_permitted_critical | 10 |
| out_of_scope | out_of_scope | 11 |
| outside_gmp | needs_more_information | 2 |
| outside_gmp | outside_gmp | 5 |
| permitted_risk_based | annex22_full | 1 |
| permitted_risk_based | permitted_risk_based | 6 |
| permitted_with_hitl | needs_more_information | 3 |
| permitted_with_hitl | permitted_with_hitl | 5 |
