# Evaluation report: dev_v2_sample10, provider `gemini`

Cases: v2, 10 evaluated, selection {'sample': 10, 'seed': 1909}

Run 2026-11-24T18:05:51+00:00 · model `gemini-3.5-flash-lite` · prompt `prompt-1.9` · rules `rules-1.10` · corpus `e97079b5633b` · source_map `map-1.3` · app `0.1.0` · git `61d8d12-dirty`

| Metric | Value |
|---|---|
| n | 10 |
| dangerous errors | 0 |
| dangerous errors on gmp critical | 0 |
| wrongly refused | 0 |
| wrongly refused dangerous | 0 |
| wrongly screened | 0 |
| stricter or not yet | 1 |
| dangerous cases | [] |
| forms rejected by validation | 0 |
| schema valid rate | 0.8 |
| verdict accuracy | 0.7 |
| in scope accuracy | 0.8 |
| gmp relevance accuracy | 0.714 |
| model type accuracy | 0.714 |
| autonomy accuracy | 0.429 |
| verdict accuracy by category | borderline: 0.667, clear: 0.5, out_of_scope: 1.0 |
| refusal precision | 1.0 |
| refusal recall | 1.0 |
| clear cases wrongly refused | 0 |
| key source recall retrieved | 0.818 |
| key source recall cited | 0.545 |
| primary source recall retrieved | 1.0 |
| judgments supported rate | 1.0 |
| citation keep rate | 1.0 |
| model citations in map rate | 1.0 |
| model citations known wrong | 0 |
| model citations outside map | 0 |
| judgments with source rate | 1.0 |
| mean latency ms | 38223 |

## Verdict confusion (expected → got)

| expected | got | n |
|---|---|---|
| annex22_full | INVALID | 1 |
| annex22_full | needs_more_information | 1 |
| hitl_required | INVALID | 1 |
| not_permitted_critical | not_permitted_critical | 3 |
| out_of_scope | out_of_scope | 3 |
| outside_gmp | outside_gmp | 1 |
