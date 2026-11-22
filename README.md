# AI Code Reviewer

AI-assisted automated feedback for GitHub Pull Requests. This evolving prototype combines a FastAPI backend with a React dashboard.

## Current implementation
- Responsive React/Vite dashboard with sample overview metrics and PR rows.
- Review Playground sends submitted code/diff text to the backend.
- FastAPI health endpoint and review API.
- Transparent baseline checks: TODO/FIXME, credential-like assignments, print debugging, and bare exception handlers.
- GitHub webhook SHA-256 signature validation and acknowledgement. It does not yet fetch PR diffs, enqueue reviews, or publish comments.

## Stack
Python 3.11+, FastAPI, Pydantic Settings, React 18, Vite, Lucide, Pytest.

## Run backend
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
