# Evaluation report: dev_v2, provider `gemini`

Cases: v2, 42 evaluated, selection {'limit': None}

Run 2026-11-24T12:57:16+00:00 · model `gemini-3.5-flash-lite` · prompt `prompt-1.7` · rules `rules-1.7` · corpus `e97079b5633b` · source_map `map-1.1` · app `0.1.0` · git `ad729ae-dirty`

| Metric | Value |
|---|---|
| n | 42 |
| dangerous errors | 0 |
| dangerous errors on gmp critical | 0 |
| wrongly refused | 0 |
| wrongly refused dangerous | 0 |
| wrongly screened | 0 |
| stricter or not yet | 4 |
| dangerous cases | [] |
| forms rejected by validation | 0 |
| schema valid rate | 0.81 |
| verdict accuracy | 0.714 |
| in scope accuracy | 0.81 |
| gmp relevance accuracy | 0.735 |
| model type accuracy | 0.765 |
| autonomy accuracy | 0.647 |
| verdict accuracy by category | borderline: 0.611, clear: 0.688, out_of_scope: 1.0 |
| refusal precision | 1.0 |
| refusal recall | 1.0 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.638 |
| key source recall cited | 0.638 |
| primary source recall retrieved | 0.962 |
| judgments supported rate | 0.949 |
| citation keep rate | 0.959 |
| model citations in map rate | 0.959 |
| model citations known wrong | 0 |
| model citations outside map | 4 |
| judgments with source rate | 0.948 |
| mean latency ms | 31209 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | annex22_full | 4 |
| annex22_full | needs_more_information | 1 |
| hitl_required | INVALID | 1 |
| hitl_required | needs_more_information | 1 |
| needs_more_information | INVALID | 1 |
| needs_more_information | needs_more_information | 2 |
| not_ai_annex11 | not_ai_annex11 | 2 |
| not_permitted_critical | INVALID | 3 |
| not_permitted_critical | not_permitted_critical | 5 |
| out_of_scope | out_of_scope | 8 |
| outside_gmp | INVALID | 1 |
| outside_gmp | needs_more_information | 1 |
| outside_gmp | outside_gmp | 3 |
| permitted_risk_based | INVALID | 1 |
| permitted_risk_based | needs_more_information | 1 |
| permitted_risk_based | permitted_risk_based | 3 |
| permitted_with_hitl | INVALID | 1 |
| permitted_with_hitl | permitted_with_hitl | 3 |
