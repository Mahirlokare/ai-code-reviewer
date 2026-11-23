"""GitHub API client for GitHub Apps, diff retrieval, and batch review comments."""
from __future__ import annotations

import time
from typing import Any
import httpx

from app.review.diff_parser import ParsedDiff
from app.schemas.review import Finding, ReviewResponse


class GitHubClient:
    """Handles GitHub App JWT authentication, token exchange, and PR reviews."""

    def __init__(
        self,
        app_id: str | None = None,
        private_key: str | None = None,
        base_url: str = "https://api.github.com",
    ) -> None:
        self.app_id = app_id
        self.private_key = private_key
        self.base_url = base_url.rstrip("/")

    def _generate_jwt(self) -> str:
        if not self.app_id or not self.private_key:
            raise ValueError("GitHub app_id and private_key are required for JWT generation.")

        # Lazy import PyJWT so app starts even if not installed in lightweight mode
        try:
            import jwt  # type: ignore
        except ImportError as err:
            raise RuntimeError("PyJWT with cryptography is required for GitHub App JWT auth.") from err

        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + 600,
            "iss": str(self.app_id),
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> str:
        """Obtain an installation access token using the GitHub App JWT."""
        app_jwt = self._generate_jwt()
        url = f"{self.base_url}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return str(data["token"])

    async def fetch_pr_diff(self, owner: str, repo: str, pull_number: int, token: str) -> str:
        """Fetch the unified git diff for a pull request."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.diff",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    def format_inline_comment(self, finding: Finding) -> str:
        """Format an inline finding with GitHub markdown and suggestion block."""
        badge = {
            "critical": "🚨 **[CRITICAL]**",
            "high": "⚠️ **[HIGH]**",
            "medium": "🟡 **[MEDIUM]**",
            "low": "🔵 **[LOW]**",
            "info": "ℹ️ **[INFO]**",
        }.get(finding.severity, "🔍")

        body_parts = [
            f"{badge} **{finding.title}** (`{finding.category}`)",
            "",
            finding.description,
        ]

        if finding.suggestion:
            body_parts.extend([
                "",
                "```suggestion",
                finding.suggestion,
                "```",
            ])

        return "\n".join(body_parts)

    def prepare_review_payload(
        self,
        commit_sha: str,
        review_res: ReviewResponse,
        parsed_diff: ParsedDiff,
    ) -> dict[str, Any]:
        """Construct a validated GitHub Pull Request Review payload."""
        inline_comments: list[dict[str, Any]] = []

        for f in review_res.findings:
            if not f.file_path or f.line is None:
                continue

            # Ensure the line was actually added in the diff to prevent GitHub API 422 errors
            valid_lines = parsed_diff.get_valid_new_lines(f.file_path)
            if valid_lines and f.line not in valid_lines:
                continue

            inline_comments.append({
                "path": f.file_path,
                "line": f.line,
                "side": "RIGHT",
                "body": self.format_inline_comment(f),
            })

        has_critical = any(f.severity == "critical" for f in review_res.findings)
        event = "REQUEST_CHANGES" if has_critical else "COMMENT"

        return {
            "commit_id": commit_sha,
            "body": review_res.summary,
            "event": event,
            "comments": inline_comments,
        }

    async def submit_pr_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        token: str,
        review_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit the batch review via the GitHub Pull Request Review API."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=review_payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
