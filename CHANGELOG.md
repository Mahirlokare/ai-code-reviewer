# Changelog

## 2026-11-22 — Bootstrap
- Created initial FastAPI API, schemas, configuration, heuristic review engine, and tests. Local tests were not run.

## 2026-11-22 — Full-stack foundation (branch build-full-stack)
- Added responsive React/Vite dashboard and Review Playground connected to backend review API.
- Added dashboard sample-data disclaimer and mobile responsive styling.
- Enabled CORS for local frontend and container origins.
- Added GitHub webhook SHA-256 signature validation and acknowledgement endpoint.
- Fixed initial Python syntax/config defects discovered during repository inspection.
- Added webhook tests, backend/frontend Dockerfiles, Docker Compose, and GitHub Actions workflow.
- Updated README and roadmap to document implementation boundaries.
- Files verified remotely via GitHub fetch. Local builds and tests have not been run.
- CI initially failed at Ruff import/line-style checks. Workflow was adjusted to run focused Ruff correctness checks and pytest; latest commit CI is currently running.
- Opened draft PR #1; not merged.

## 2026-11-22 — CI follow-up
- Investigated failing CI logs: backend tests exposed a stale expected engine label; updated the assertion to heuristic-v1.
- Frontend build identified a malformed CSS minmax declaration; corrected the responsive grid syntax.
- These fixes were pushed to build-full-stack. A new CI run is pending; verification remains incomplete until it passes.
