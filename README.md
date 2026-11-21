# AI Code Reviewer

Automated, context-aware feedback for GitHub Pull Requests. The project is being built incrementally with a FastAPI backend, deterministic review checks, optional LLM review, and GitHub integration.

## Current scope

The initial foundation provides a health endpoint and a local review API for submitted diffs. GitHub webhook ingestion, background processing, static-analysis integrations, AI review, inline publishing, persistence, and evaluation will be added in staged modules.

## Stack
- Python 3.11+
- FastAPI + Uvicorn
- Pydantic settings
- Pytest

## Setup

1. Create and activate a virtual environment: `python -m venv .venv` then `source .venv/bin/activate`.
2. Install: `pip install -e ".[dev]"`
3. Copy `.env.example` to `.env` and adjust values as needed.
4. Run: `uvicorn app.main:app --reload`
5. Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Review API
`POST /api/v1/reviews` accepts a JSON payload containing a diff and returns structured findings. It currently uses deterministic heuristics; no external AI provider is called and no comments are posted to GitHub.

## Safety
This tool is advisory. Always validate findings manually before merging. Secrets should be provided via environment variables and never committed.

## Development
Run tests using `pytest`. See `CHANGELOG.md` for recorded changes and `docs/roadmap.md` for milestones.