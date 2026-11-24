# Gemini API limits (free tier)

Snapshot of the quota page in Google AI Studio on **2026-11-22**, personal account. Limits change; re-check the AI Studio "Rate limits" page before planning a large run.

## Reading the quota page
- **RPM:** requests per minute
- **TPM:** tokens per minute (input + output)
- **RPD:** requests per day. Quotas are per project and reset at 09:00 Danish time (W14).

## Models relevant to this project

| Model | RPM | TPM | RPD | Use here |
|---|---|---|---|---|
| **Gemini 3.5 Flash Lite** | 15 | 250K | **500** | Current default (`GEMINI_MODEL`). A full test run fits in one day. |
| Gemini 3.1 Flash Lite | 15 | 250K | 500 | Fallback; also accepts the schema (W13). |
| Gemini 3.6 Flash · 3.8 Flash · 4 Hydrogen · 3 Flash · 2.5 Flash | 5 | 250K | 20 | Stronger, but 20/day does not fit an evaluation. Needs paid credits. |
| Gemma 4 26B / 31B | 30 | **16K** | 14,400 | TPM is the bottleneck: one request is ~6–8K tokens, so about 2 per minute. Structured output and tool calls untested. |
| Pro models (2.5 Pro, 3.1 Pro, Gemini 4 Argon / Neon / Carbon) | 0 | 0 | 0 | Not available on the free tier. |

## What a run costs in requests
- One assessment = 1 to 4 calls (optional `get_section` tool rounds, then the final schema-enforced call).
- Dev set (10 cases): about 20–40 calls. Test set (30 cases): about 60–120 calls.
- At 15 RPM a test run takes 10–15 minutes. Per-minute 429s are retried automatically (`providers._post_with_rate_limit_retry`); the daily quota is not retried and becomes a logged rejection.

## Paid tier: cost per request (researched 2026-11-22, [pricing page](https://aistudio.google.com/docs/pricing))
- Gemini 3.5 Flash-Lite: $0.30 per 1M input tokens, $2.50 per 1M output tokens (thinking tokens count as output; default thinking "minimal"). Batch API: half price.
- Our request: about 4,300 input tokens plus 400–3,000 output tokens = **about $0.002–$0.009 per request**. Dev run (41): $0.16–$0.36. Test run (70): $0.27–$0.62. Ten test runs a month: $2.70–$6.20 (double with "ask twice").
- Failed requests (4xx/5xx, e.g. our 503 retries) are not billed, but count against quota.
- Switching: AI Studio → Set up billing on the project → Cloud Billing account → Prepay, minimum $5 (credits expire after 12 months; at $0 requests fail with HTTP 402, so prepay is a hard cap). AI Studio also has an experimental monthly spend cap per project.
- Google AI Pro includes **$10 a month of API credits** (claim in AI Studio; needs the billing account and a positive prepaid balance). That covers this project's workload. It does not raise API rate limits.
- Paid rate limits are no longer published per model; they are shown in AI Studio after upgrading (Tier 1 = billing linked).
- EEA clause in the terms: an API client offered to *other users* in the EEA must use paid services only. Relevant if the app is shared beyond personal testing.
- Comparison: Claude Haiku 5.5 would be about $0.001–$0.002 per request (needs a new `ChatClient` adapter).

## Beyond the free tier
- Google AI Pro includes monthly Google Cloud credits usable for the Gemini API. The subscription's own quotas apply only inside the AI Studio website, not to API keys. Using the credits needs a Cloud project with billing enabled and a $5 prepayment. Sources: [Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/google-cloud-credits-gdp-ai-studio/), [AI plans](https://ai.google.dev/gemini-api/docs/google-ai-plans).
- Paid Flash-Lite costs roughly $0.50–0.75 per full evaluation run (W14). Set a budget alert.
- A Claude subscription does not include API access; the Claude API is billed separately and would need a new `ChatClient` adapter.

## Data terms
For users in the EEA, Google applies its paid-tier data terms to the free tier too, so prompts are not used to improve Google's products (W14). Only public documents and synthetic test cases are sent here. In a company setting, use a paid or company-tenant service regardless.

## Test-set reminder
The held-out test set has been run once with Gemini (prompt 1.2, commit `89ccc97`, 0.87). Another test run must be reported as a re-use of the test set; tune on dev only.
