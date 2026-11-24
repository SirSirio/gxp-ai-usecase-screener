# Evaluation report: dev_v2, provider `offline`

Cases: v2, 41 evaluated, selection {'limit': None}

Run 2026-11-24T11:48:37+00:00 · model `keyword-rules` · prompt `offline-1.4` · rules `rules-1.7` · corpus `e97079b5633b` · source_map `map-1.1` · app `0.1.0` · git `633781a`

| Metric | Value |
|---|---|
| n | 41 |
| dangerous errors | 6 |
| dangerous errors on gmp critical | 5 |
| wrongly refused | 1 |
| wrongly refused dangerous | 0 |
| wrongly screened | 3 |
| stricter or not yet | 6 |
| dangerous cases | ['D008', 'D013', 'D014', 'D017', 'D032', 'D034'] |
| forms rejected by validation | 0 |
| schema valid rate | 1.0 |
| verdict accuracy | 0.61 |
| in scope accuracy | 0.902 |
| gmp relevance accuracy | 0.727 |
| model type accuracy | 0.879 |
| autonomy accuracy | 0.848 |
| verdict accuracy by category | borderline: 0.471, clear: 0.75, out_of_scope: 0.625 |
| refusal precision | 0.833 |
| refusal recall | 0.625 |
| clear cases wrongly refused | 1 |
| key source recall retrieved | 0.653 |
| key source recall cited | 0.653 |
| primary source recall retrieved | 0.939 |
| judgments supported rate | 1.0 |
| citation keep rate | 1.0 |
| model citations in map rate | 1.0 |
| model citations known wrong | 0 |
| model citations outside map | 0 |
| judgments with source rate | 1.0 |
| mean latency ms | 357 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | annex22_full | 4 |
| annex22_full | not_permitted_critical | 1 |
| hitl_required | needs_more_information | 1 |
| hitl_required | permitted_with_hitl | 1 |
| needs_more_information | annex22_full | 1 |
| needs_more_information | needs_more_information | 2 |
| not_ai_annex11 | not_ai_annex11 | 2 |
| not_permitted_critical | hitl_required | 2 |
| not_permitted_critical | needs_more_information | 1 |
| not_permitted_critical | not_permitted_critical | 2 |
| not_permitted_critical | permitted_risk_based | 1 |
| not_permitted_critical | permitted_with_hitl | 1 |
| out_of_scope | needs_more_information | 3 |
| out_of_scope | out_of_scope | 5 |
| outside_gmp | not_permitted_critical | 1 |
| outside_gmp | out_of_scope | 1 |
| outside_gmp | outside_gmp | 2 |
| outside_gmp | permitted_with_hitl | 1 |
| permitted_risk_based | annex22_full | 1 |
| permitted_risk_based | permitted_risk_based | 4 |
| permitted_with_hitl | permitted_with_hitl | 4 |
