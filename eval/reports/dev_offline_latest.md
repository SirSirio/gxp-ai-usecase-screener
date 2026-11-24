# Evaluation report: dev, provider `offline`

Cases: v1, 10 evaluated, selection {'limit': None}

Run 2026-11-22T10:09:46+00:00 · model `keyword-rules` · prompt `offline-1.2` · rules `rules-1.2` · corpus `e97079b5633b` · app `0.1.0` · git `58cee07-dirty`

| Metric | Value |
|---|---|
| n | 10 |
| schema valid rate | 1.0 |
| verdict accuracy | 0.9 |
| in scope accuracy | 1.0 |
| gmp relevance accuracy | 0.875 |
| model type accuracy | 1.0 |
| autonomy accuracy | 0.875 |
| verdict accuracy by category | borderline: 0.75, clear: 1.0, out_of_scope: 1.0 |
| refusal precision | 1.0 |
| refusal recall | 1.0 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.562 |
| key source recall cited | 0.688 |
| primary source recall retrieved | 1.0 |
| judgments supported rate | 1.0 |
| citation keep rate | 1.0 |
| mean latency ms | 220 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | annex22_full | 1 |
| hitl_required | not_permitted_critical | 1 |
| needs_more_information | needs_more_information | 1 |
| not_ai_annex11 | not_ai_annex11 | 1 |
| not_permitted_critical | not_permitted_critical | 1 |
| out_of_scope | out_of_scope | 2 |
| outside_gmp | outside_gmp | 1 |
| permitted_risk_based | permitted_risk_based | 1 |
| permitted_with_hitl | permitted_with_hitl | 1 |
