# Evaluation report: test_v2, provider `offline`

Cases: v2, 70 evaluated, selection {'limit': None}

Run 2026-11-22T12:17:34+00:00 · model `keyword-rules` · prompt `offline-1.2` · rules `rules-1.3` · corpus `e97079b5633b` · app `0.1.0` · git `0f9f242-dirty`

| Metric | Value |
|---|---|
| n | 70 |
| dangerous errors | 13 |
| dangerous errors on gmp critical | 9 |
| wrongly refused | 2 |
| wrongly refused dangerous | 1 |
| wrongly screened | 7 |
| stricter or not yet | 8 |
| forms rejected by validation | 1 |
| schema valid rate | 1.0 |
| verdict accuracy | 0.586 |
| in scope accuracy | 0.871 |
| gmp relevance accuracy | 0.729 |
| model type accuracy | 0.898 |
| autonomy accuracy | 0.712 |
| verdict accuracy by category | borderline: 0.429, clear: 0.917, out_of_scope: 0.364 |
| refusal precision | 0.667 |
| refusal recall | 0.364 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.669 |
| key source recall cited | 0.789 |
| primary source recall retrieved | 1.0 |
| judgments supported rate | 1.0 |
| citation keep rate | 1.0 |
| mean latency ms | 196 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | annex22_full | 5 |
| annex22_full | permitted_risk_based | 2 |
| hitl_required | hitl_required | 4 |
| hitl_required | permitted_with_hitl | 3 |
| needs_more_information | hitl_required | 1 |
| needs_more_information | needs_more_information | 5 |
| needs_more_information | out_of_scope | 1 |
| needs_more_information | permitted_with_hitl | 1 |
| not_ai_annex11 | annex22_full | 1 |
| not_ai_annex11 | needs_more_information | 1 |
| not_ai_annex11 | not_ai_annex11 | 3 |
| not_permitted_critical | annex22_full | 1 |
| not_permitted_critical | hitl_required | 1 |
| not_permitted_critical | not_permitted_critical | 4 |
| not_permitted_critical | permitted_with_hitl | 4 |
| out_of_scope | annex22_full | 1 |
| out_of_scope | hitl_required | 1 |
| out_of_scope | needs_more_information | 3 |
| out_of_scope | not_permitted_critical | 1 |
| out_of_scope | out_of_scope | 4 |
| out_of_scope | permitted_with_hitl | 1 |
| outside_gmp | out_of_scope | 1 |
| outside_gmp | outside_gmp | 4 |
| outside_gmp | permitted_risk_based | 2 |
| permitted_risk_based | annex22_full | 1 |
| permitted_risk_based | permitted_risk_based | 6 |
| permitted_with_hitl | hitl_required | 1 |
| permitted_with_hitl | not_permitted_critical | 1 |
| permitted_with_hitl | permitted_with_hitl | 6 |
