# Evaluation report: dev_v2_sample10, provider `offline`

Cases: v2, 10 evaluated, selection {'sample': 10, 'seed': 1}

Run 2026-11-22T09:56:34+00:00 · model `keyword-rules` · prompt `offline-1.1` · rules `rules-1.2` · corpus `e97079b5633b` · app `0.1.0` · git `3d5222a-dirty`

| Metric | Value |
|---|---|
| n | 10 |
| schema valid rate | 1.0 |
| verdict accuracy | 0.4 |
| in scope accuracy | 0.7 |
| gmp relevance accuracy | 0.5 |
| model type accuracy | 0.833 |
| autonomy accuracy | 0.667 |
| verdict accuracy by category | borderline: 0.4, clear: 1.0, out_of_scope: 0.25 |
| refusal precision | 1.0 |
| refusal recall | 0.25 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.615 |
| key source recall cited | 0.615 |
| primary source recall retrieved | 0.833 |
| judgments supported rate | 1.0 |
| citation keep rate | 1.0 |
| mean latency ms | 343 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| hitl_required | not_permitted_critical | 1 |
| needs_more_information | annex22_full | 1 |
| needs_more_information | needs_more_information | 1 |
| not_permitted_critical | not_permitted_critical | 2 |
| out_of_scope | needs_more_information | 3 |
| out_of_scope | out_of_scope | 1 |
| permitted_with_hitl | not_permitted_critical | 1 |
