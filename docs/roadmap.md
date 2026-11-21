# Roadmap

## Milestone 1 — API foundation (scaffold)
- [x] FastAPI app and liveness endpoint
- [x] Typed configuration via environment
- [x] Diff-review request/response schemas
- [x] Baseline deterministic heuristics
- [x] Initial automated tests authored
- [ ] Run tests locally and address failures

## Milestone 2 — Review quality
- [ ] Parse unified diff hunks robustly and validate line locations
- [ ] Improve rule coverage and confidence calibration
- [ ] Add test fixtures for tricky diffs and false-positive cases
- [ ] Add JSON output schema versioning

## Milestone 3 — Static analysis
- [ ] Ruff invocation integration
- [ ] Semgrep integration with safe subprocess handling and configurable rules
- [ ] Normalize scanner findings to shared Finding model

## Milestone 4 — GitHub App/webhook
- [ ] Signature verification
- [ ] PR opened/synchronize event validation
- [ ] Fetch changed files/diffs via GitHub API
- [ ] Permission scopes and installation-token flow

## Milestone 5 — Async pipeline
- [ ] Queue and worker with retry/idempotency
- [ ] Redis-backed job processing
- [ ] Job lifecycle and observability

## Milestone 6 — AI reviewer
- [ ] LLM integration behind provider interface
- [ ] Strict structured output validation
- [ ] Context window budgeting and prompt injection boundaries
- [ ] Human-review requirement and confidence-based gating

## Milestone 7 — Publishing and persistence
- [ ] Deduplicate, rank, and cap findings
- [ ] Inline comments only on valid diff lines
- [ ] Review summary and check status
- [ ] PostgreSQL persistence and audit trail

## Milestone 8 — Evaluation and deployment
- [ ] Benchmark against labeled/historical PRs
- [ ] Measure precision, false positives, latency, and cost
- [ ] Docker and CI workflow
- [ ] Security and deployment review
