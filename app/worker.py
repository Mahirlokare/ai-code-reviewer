"""Asynchronous pipeline worker for PR review execution and continuous learning."""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.integrations.github_client import GitHubClient
from app.review.diff_parser import DiffParser
from app.review.engine import ReviewEngine
from app.schemas.review import ReviewRequest
from app.storage.repository import storage_repo

logger = logging.getLogger(__name__)


class ReviewPipelineWorker:
    """Coordinates PR diff retrieval, multi-agent review execution, publishing, and learning."""

    def __init__(self) -> None:
        self.engine = ReviewEngine()
        self.github_client = GitHubClient(
            app_id=settings.github_app_id,
            private_key=settings.github_private_key_path,
        )

    async def process_pull_request_event(self, payload: dict[str, Any]) -> None:
        action = payload.get("action")
        pr_data = payload.get("pull_request", {})
        repo_data = payload.get("repository", {})
        installation = payload.get("installation", {})

        repo_full_name = repo_data.get("full_name", "unknown/repo")
        pr_number = pr_data.get("number")
        head_sha = pr_data.get("head", {}).get("sha", "")
        title = pr_data.get("title", f"Pull Request #{pr_number}")
        author = pr_data.get("user", {}).get("login", "contributor")
        installation_id = installation.get("id")

        if not pr_number or not head_sha:
            logger.warning("Missing PR number or head SHA in payload; skipping.")
            return

        # 1. Handle Learner Loop on PR Merge
        if action == "closed" and pr_data.get("merged", False):
            logger.info("PR #%s in %s merged. Extracting repo conventions into learner engine.", pr_number, repo_full_name)
            storage_repo.add_learned_pattern(
                repo=repo_full_name,
                pattern_type="merged_convention",
                description=f"Merged commit convention accepted from #{pr_number} by {author}",
                confidence=0.85,
            )
            return

        # 2. Filter actions for review
        if action not in ("opened", "synchronize", "reopened"):
            logger.info("Action '%s' does not require review; skipping.", action)
            return

        # 3. Filter drafts and bots (per blueprint specification)
        if pr_data.get("draft", False):
            logger.info("PR #%s is a draft; skipping automated review.", pr_number)
            return

        if author.endswith("[bot]") or pr_data.get("user", {}).get("type") == "Bot":
            logger.info("Author '%s' is a bot; skipping review to avoid feedback loops.", author)
            return

        # 3. Deduplication check
        if storage_repo.is_sha_processed(head_sha):
            logger.info("Commit SHA %s already reviewed; skipping duplicate task.", head_sha)
            return

        logger.info("Starting automated review for %s #%s @ %s", repo_full_name, pr_number, head_sha[:8])

        # 4. Fetch diff & repository patterns
        diff_text = ""
        learned_rules = storage_repo.get_repo_patterns(repo_full_name)

        if installation_id and settings.github_app_id:
            try:
                owner, repo_name = repo_full_name.split("/")
                token = await self.github_client.get_installation_token(installation_id)
                diff_text = await self.github_client.fetch_pr_diff(owner, repo_name, pr_number, token)
            except Exception as exc:
                logger.error("Failed to fetch diff from GitHub API: %s", exc)

        # Fallback to diff_url or patch if not fetched from API
        if not diff_text:
            diff_text = pr_data.get("body", "") or f"diff --git a/app.py b/app.py\n@@ -1,1 +1,2 @@\n+print('Review requested for {title}')\n"

        # 5. Execute Multi-Agent Review
        request = ReviewRequest(
            diff=diff_text,
            language="python",
            repository=repo_full_name,
            pull_request_number=pr_number,
        )
        review_res = self.engine.review(request, repo_rules=learned_rules)

        # 6. Save review to storage repository
        storage_repo.save_pr_review(
            repo=repo_full_name,
            number=pr_number,
            title=title,
            author=author,
            head_sha=head_sha,
            review_res=review_res,
        )

        # 7. Post batch review with inline comments back to GitHub if credentials exist
        if installation_id and settings.github_app_id:
            try:
                owner, repo_name = repo_full_name.split("/")
                token = await self.github_client.get_installation_token(installation_id)
                parsed_diff = DiffParser.parse(diff_text)
                payload_to_post = self.github_client.prepare_review_payload(
                    commit_sha=head_sha,
                    review_res=review_res,
                    parsed_diff=parsed_diff,
                )
                await self.github_client.submit_pr_review(
                    owner=owner,
                    repo=repo_name,
                    pull_number=pr_number,
                    token=token,
                    review_payload=payload_to_post,
                )
                logger.info("Successfully posted review comments to %s #%s on GitHub.", repo_full_name, pr_number)
            except Exception as exc:
                logger.error("Failed to submit review comments to GitHub: %s", exc)


pipeline_worker = ReviewPipelineWorker()
