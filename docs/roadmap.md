# Roadmap

## Milestone 1 — API foundation
- [x] FastAPI app, health endpoint, environment configuration
- [x] Review schemas and transparent heuristic checks
- [x] Tests authored
- [ ] Execute tests locally and resolve failures

## Milestone 2 — Dashboard
- [x] React/Vite responsive dashboard shell and overview
- [x] Demo KPI cards and PR list (sample content)
- [x] Review Playground wired to backend
- [ ] Replace sample PR content with live GitHub API data

## Milestone 3 — Webhook intake
- [x] SHA-256 signature validation
- [x] Event acknowledgement endpoint
- [x] Webhook unit/API tests authored
- [ ] Payload validation and idempotency
- [ ] Enqueue PR events for review

## Milestone 4 — Local container/CI foundation
- [x] Backend and frontend Dockerfiles
- [x] Docker Compose startup and backend health dependency
- [x] GitHub Actions backend/frontend jobs
- [ ] Confirm CI success and correct failures

## Milestone 5 — Static analysis
- [ ] Ruff full style enforcement
- [ ] Semgrep integration using safe subprocess boundaries
- [ ] Scanner finding normalization
- [ ] Robust unified diff parsing and changed-line mapping

## Milestone 6 — GitHub integration and worker
- [ ] GitHub App token flow
- [ ] Fetch PR diffs and repository context
- [ ] Queue, retry, deduplication, and worker lifecycle

## Milestone 7 — AI reviewer
- [ ] Provider abstraction and LLM integration
- [ ] Validated structured output
- [ ] Prompt-injection defenses and context budgeting
- [ ] Confidence/severity gating

## Milestone 8 — Publishing and persistence
- [ ] Inline review comments restricted to valid changed lines
- [ ] Review summary and check status
- [ ] PostgreSQL storage and audit history

## Milestone 9 — Evaluation and delivery
- [ ] Labeled benchmark and false-positive metrics
- [ ] Deployment, monitoring, security review, final QA
