# Roadmap

## Milestone 1 — API foundation
- [x] FastAPI app, health endpoint, environment configuration
- [x] Review schemas and transparent heuristic checks
- [x] Tests authored
- [ ] Run tests locally and resolve failures

## Milestone 2 — Dashboard
- [x] React/Vite responsive dashboard shell and overview
- [x] Demo KPI cards and PR list (sample content)
- [x] Review Playground wired to backend
- [ ] Replace sample PR content with live GitHub API data

## Milestone 3 — Webhook intake
- [x] SHA-256 signature validation
- [x] Event acknowledgement endpoint
- [ ] Payload validation and idempotency
- [ ] Enqueue PR events for review

## Milestone 4 — Static analysis
- [ ] Ruff and Semgrep integration using safe subprocess boundaries
- [ ] Scanner finding normalization
- [ ] Robust unified diff parsing and changed-line mapping

## Milestone 5 — GitHub and worker
- [ ] GitHub App token flow
- [ ] Fetch pull request diffs and repository context
- [ ] Redis queue, retry, deduplication, and worker lifecycle

## Milestone 6 — AI reviewer
- [ ] Provider abstraction and LLM integration
- [ ] Validated structured output
- [ ] Prompt-injection defenses and context budgeting
- [ ] Confidence/severity gating

## Milestone 7 — Publishing and persistence
- [ ] Inline comments restricted to valid changed lines
- [ ] Review summary and check status
- [ ] PostgreSQL storage and audit history

## Milestone 8 — Evaluation and deployment
- [ ] Labeled benchmark and false-positive metrics
- [ ] Docker and CI workflows
- [ ] Deployment, monitoring, security review, final QA
