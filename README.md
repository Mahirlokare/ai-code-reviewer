# AI Code Reviewer

AI-assisted automated code review pipeline for GitHub pull requests, repositories, and direct code analysis. Combines a multi-agent FastAPI backend with a humanized React dashboard.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Mahirlokare/ai-code-reviewer)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Mahirlokare/ai-code-reviewer)

---

## 🚀 Live Cloud Deployment Options

### Option 1: One-Click Deploy on Render (Recommended for Full Stack Backend + UI)
Render automatically provisions both the Python FastAPI API and React Vite UI using `render.yaml`:
1. Click **[Deploy to Render](https://render.com/deploy?repo=https://github.com/Mahirlokare/ai-code-reviewer)**.
2. Sign in with GitHub (`Mahirlokare`).
3. Click **Apply Blueprint** — Render provisions and hosts:
   - **Backend API**: `https://ai-code-reviewer-api.onrender.com`
   - **Frontend UI**: `https://ai-code-reviewer-ui.onrender.com`

### Option 2: One-Click Deploy on Vercel
Deploy the frontend and serverless API instantly on Vercel:
1. Click **[Deploy with Vercel](https://vercel.com/new/clone?repository-url=https://github.com/Mahirlokare/ai-code-reviewer)**.
2. Sign in with GitHub (`Mahirlokare`).
3. Click **Deploy** — Vercel builds the React dashboard and serverless functions directly on `*.vercel.app`.

## Current implementation
- Responsive React/Vite dashboard with sample overview metrics and PR rows.
- Review Playground sends submitted code/diff text to the backend.
- FastAPI health endpoint and review API.
- Transparent baseline checks: TODO/FIXME, credential-like assignments, print debugging, and bare exception handlers.
- GitHub webhook SHA-256 signature validation and acknowledgement. It does not yet fetch PR diffs, enqueue reviews, or publish comments.

## Architecture Blueprint & Specifications
For the complete production engineering design and target architecture:
- **[Architecture Blueprint (Markdown)](docs/architecture_blueprint.md)**: Microservice decomposition, LangGraph 4-agent parallel pipeline, PostgreSQL RDS schemas, and AWS EKS deployment.
- **[Architecture Blueprint (PDF)](docs/AI_Code_Review_Pipeline_Blueprint.pdf)**: Publication-grade PDF specification document.
- **[Milestone Roadmap](docs/roadmap.md)**: Phased implementation checklist from MVP to production delivery.

## Stack
Python 3.11+, FastAPI, Pydantic Settings, React 18, Vite, Lucide, Pytest.

## One-Click Free Deployment (Render)

This repository includes a `render.yaml` blueprint to deploy both the FastAPI Backend and React Dashboard 100% free with automated HTTPS and GitHub CI:

1. Go to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** > **Blueprint**.
3. Select this repository: `Mahirlokare/ai-code-reviewer`.
4. Click **Apply**: Render automatically builds and hosts:
   - **Backend API**: `https://ai-code-reviewer-api.onrender.com` (public webhook URL for GitHub Apps)
   - **Frontend UI**: `https://ai-code-reviewer-ui.onrender.com`

---

## Run backend locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs

## Run frontend (separate terminal)
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Dashboard: http://localhost:5173

## Review endpoint
POST /api/v1/reviews accepts JSON containing diff and language and returns findings, added-line count, and engine identifier.

## Webhook endpoint
POST /api/v1/webhooks/github validates GitHub SHA-256 signatures using GITHUB_WEBHOOK_SECRET. It acknowledges events but does not trigger review processing yet.

## Safety
Dashboard cards and PR rows are demo data, not live GitHub results. Reviews are advisory. Never commit secrets.
