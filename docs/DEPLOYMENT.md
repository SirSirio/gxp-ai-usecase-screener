# Deployment

Status: **decided, not yet run** (D27): Azure Container Apps on a personal Azure free account. The App Service guide below is kept as the alternative. Data policy as in `CLAUDE.md`: personal account, secrets only in Azure settings, never in the repo.

## Plan: Azure Container Apps (free within the monthly allowance)
- **What runs:** one container with the app (Python, FastAPI). The image installs the app, downloads the 9 public documents (hash-checked) and builds the search index at build time, so the container starts without network downloads.
- **Where the image lives:** GitHub container registry (`ghcr.io`), free for public images.
- **Cost control:** consumption plan, **minimum replicas 0** (scale to zero after a few idle minutes: no charge while scaled to zero), maximum replicas 1, 0.5 vCPU and 1 GiB; a **budget alert at €1** on the subscription. Free per subscription per calendar month (checked 2026-11-24): 180,000 vCPU-seconds, 360,000 GiB-seconds, 2 million requests. Estimate: about 1,200 separate visits a month fit (each visit keeps the app awake about 5 minutes).
- **Settings (secrets as Container Apps secrets):** `GXP_PROVIDER=gemini` (or `offline`), `GEMINI_API_KEY` (a separate key for the demo is recommended), `GEMINI_MODEL=gemini-3.5-flash-lite`, a lower `GEMINI_DAILY_BUDGET` for the public demo (e.g. 100), `GEMINI_MAX_RPM`.
- **Public-demo notices:** the form says not to enter confidential or company information; the audit log and results are demo-only, because the container file system is not kept (production: durable storage, e.g. Blob Storage, and user identity).
- **Cold start:** after idle, the first visit waits about 10-30 s while the container starts and loads the embedding model.
- **Azure resources (created by the owner in the portal, 2026-11-24, guided by a separate deployment chat):** subscription "Azure subscription 1" (personal), resource group `rg-gxp-ai`, Container Apps environment `cae-gxp-ai` (Consumption only, no zone redundancy, public network access, no own VNet; logs to Azure Monitor with no diagnostic setting yet, so nothing is stored or billed), container app `gxp-ai-screener` (container `gxp-ai`), region **North Europe** (closest to Denmark). No Azure Container Registry.
- **Image:** `Dockerfile` (python:3.10-slim; at build time it downloads and hash-checks the 9 documents, builds the index, bakes in the embedding model and checks the corpus version against the source map; runs as a non-root user; `startup.sh` serves on `$PORT`, default 8000). Built and pushed by the GitHub Actions workflow `.github/workflows/image.yml` ("Build image", run by hand or on a `v*` tag) to `ghcr.io/sirsirio/gxp-ai-usecase-screener:latest` and `:<commit>`; the workflow also starts the image and runs a smoke test (health, home page, one keyword-baseline screening). The owner has no local Docker or Azure CLI, so the build runs on GitHub.
- **Portal steps (owner, guided by the deployment chat):** make the ghcr package public; edit and deploy the container app: image as above, port 8000, 0.5 CPU / 1 GiB, min replicas 0, max 1; secret `gemini-api-key` and env `GXP_PROVIDER=gemini`, `GEMINI_DAILY_BUDGET=100`, `GEMINI_MAX_RPM=10`, `GXP_PUBLIC_DEMO=1`; budget alert at €1; smoke test (`/api/health`, one keyword-baseline and one Gemini screening; log stream; memory working set).
- **Account deadline:** the free account's credit (€179.54 left) expires on **2026-12-20**. Before then the subscription must be upgraded to pay-as-you-go to keep the always-free Container Apps allowance; otherwise the subscription is disabled and the app stops. Within the free allowance the cost stays at zero (budget alert at €1).
- **Known limit:** the daily Gemini counter lives in the container's file system, so it resets whenever the app scales to zero: the app's cap is per wake-up. A separate AI Studio key without billing makes Google's free quota the real ceiling.
- **Fallback:** Hugging Face Spaces (free, no card, Docker), same Dockerfile and settings.

---

# Alternative: Azure App Service (not chosen)

## What gets deployed
- One Linux App Service (Python 3.11, B1 plan: about €12/month, cheapest plan with "always on"). The Free tier (F1: 60 CPU minutes a day, 1 GB memory) is too tight for the embedding model and index (D27).
- On first start, `startup.sh` downloads the 9 public documents, checks their hashes and builds the index, including the embedding model (about 130 MB).
- Secrets (LLM keys) live in App Service *application settings*, never in the repo.
- The audit log and results go to `data/` on the app's file system. For anything beyond a demo, move them to Azure Blob Storage or a database, because the App Service file system is not a durable record store.

## Steps (Azure CLI)
```bash
az login
az group create -n rg-gxp-ai -l westeurope

# 1. Budget alert first (Spec: "budget alert on the subscription")
az consumption budget create --budget-name gxp-ai-monthly --amount 20 --time-grain Monthly \
  --start-date 2026-12-01 --end-date 2027-12-01 --category cost \
  --notifications '{"Actual_GT_80":{"enabled":true,"operator":"GreaterThan","threshold":80,"contactEmails":["<your email>"]}}'

# 2. Create and deploy the web app from the repo folder
az webapp up -n <unique-app-name> -g rg-gxp-ai --runtime "PYTHON:3.11" --sku B1 --location westeurope

# 3. Startup command and settings
az webapp config set -n <unique-app-name> -g rg-gxp-ai --startup-file "bash startup.sh"
az webapp config appsettings set -n <unique-app-name> -g rg-gxp-ai --settings \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true GXP_PROVIDER=offline WEB_CONCURRENCY=1
# when a key is available, e.g. Azure OpenAI:
# az webapp config appsettings set ... --settings GXP_PROVIDER=azure_openai AZURE_OPENAI_ENDPOINT=... AZURE_OPENAI_API_KEY=... AZURE_OPENAI_DEPLOYMENT=...

# 4. Check
curl https://<unique-app-name>.azurewebsites.net/api/health
```

## Hardening before showing it to anyone
- Restrict access (App Service authentication with Entra ID, or IP restrictions): the tool has no login of its own.
- Use Key Vault references for the API keys instead of plain app settings.
- Turn on HTTPS only and minimum TLS 1.2 (default on new apps; check).
- Keep the free/low budget alert; delete the resource group after the demo: `az group delete -n rg-gxp-ai`.
