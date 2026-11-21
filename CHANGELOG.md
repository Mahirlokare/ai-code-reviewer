# Changelog

All notable project changes are recorded here.

## 2026-11-22 — Project bootstrap (Phase 1, foundation)
- Confirmed the target repository is `Mahirlokare/ai-code-reviewer` and was empty before initialization.
- Added the initial documentation, API foundation, deterministic review logic, configuration, and test scaffolding.
- This bootstrap does not yet implement live GitHub webhook handling, queue workers, LLM provider calls, or comment publishing.
- Tests are included but have not yet been executed in a local environment during this GitHub-only setup.

## 2026-11-22 — Test scaffolding and roadmap
- Added unit tests for baseline review heuristics and API smoke tests.
- Added a roadmap covering planned review quality, static analysis, GitHub App/webhooks, async processing, AI review, publishing/persistence, and evaluation/deployment.
- Retrieved selected files from GitHub to confirm file contents were present.
- Tests have not been executed locally; implementation remains unverified until a local checkout and test run.
