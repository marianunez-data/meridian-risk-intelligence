# Deployment guide

Everything below is free and needs no credit card.

## 1. Publish the repository on GitHub

1. Create a new **public** repository on GitHub named `meridian-risk-intelligence` (no README, no licence; the project already has them).
2. In the project folder:

```bash
git init
git add .
git commit -m "Meridian Capital: Counterparty Risk Intelligence Platform"
git branch -M main
git remote add origin https://github.com/marianunez-data/meridian-risk-intelligence.git
git push -u origin main
```

Raw data, the full warehouse and features are excluded by `.gitignore`. What is committed: code, executed notebooks, trained models (about 22 MB) and the compact app warehouse (`app/data/meridian_app.duckdb`, about 27 MB). All files are under GitHub's 100 MB limit.

3. Open the **Actions** tab and confirm the CI workflow passes (lint, 44 tests, dbt parse, dashboard smoke test).

## 2. Deploy the dashboard on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **Create app**, then **Deploy a public app from GitHub**.
3. Repository: `marianunez-data/meridian-risk-intelligence`, branch `main`, main file path `app/streamlit_app.py`.
4. Open **Advanced settings**:
   - Python version: **3.13** (the trained models were saved with the pinned library versions in `requirements.txt`).
   - Secrets: paste the content of `.streamlit/secrets.toml.example` with your values (see step 3).
5. Click **Deploy**. The first build takes a few minutes. In **App URL**, set the custom subdomain to `meridian-risk-intelligence` so the address is `https://meridian-risk-intelligence.streamlit.app`, the link the README already uses. If that name is taken, pick another and update the three links at the top of the README.

Notes: free apps sleep after 12 hours without visits and wake on the next visit (about 30 seconds). The app uses well under the 1 GB memory limit.

## 3. Enable the AI Risk Analyst (optional, free)

The dashboard works fully without a key; the analyst page then shows the governed SQL console. To enable natural-language questions, add one free key to the app's secrets:

- **Google AI Studio (Gemini):** create a key at aistudio.google.com, then set `GEMINI_API_KEY`.
- **Groq:** create a key at console.groq.com, then set `GROQ_API_KEY`.

Model names change over time. If the default model is not available to your account, set `GEMINI_MODEL` or `GROQ_MODEL` to one that is.

To score the analyst on the 16-question evaluation set:

```bash
GEMINI_API_KEY=... make eval-agent      # writes reports/agent_eval_live.csv
```

## 4. Final touches

- In `README.md`, fill in the **Author** section with your name and links.
- In the Streamlit secrets, set `GITHUB_REPO_URL` so the Methodology page links to the repository.
- Pin the repository on your GitHub profile and add the topics: `credit-risk`, `data-science`, `dbt`, `duckdb`, `lightgbm`, `shap`, `streamlit`, `llm-agent`, `text-to-sql`, `fraud-detection`.

## Why not Google Cloud?

Google Cloud Run needs a billing account with a card, and the no-card Starter Tier only deploys apps built inside Google AI Studio. The project still ships production-ready: the app is a standard Python web app and can be containerised for Cloud Run later without code changes.
