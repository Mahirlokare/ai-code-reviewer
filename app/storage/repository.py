"""In-memory and persistent storage for PR audit history and learned patterns."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.schemas.review import Finding, ReviewResponse


@dataclass
class PullRequestRecord:
    id: str
    repo: str
    number: int
    title: str
    author: str
    head_sha: str
    status: str  # "reviewed" | "review_needed" | "in_progress"
    score: int
    summary: str
    findings: list[Finding] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    analyzed_lines: int = 0


@dataclass
class RepoPatternRecord:
    id: str
    repo: str
    pattern_type: str
    rule_description: str
    confidence: float
    occurrences: int = 1


class StorageRepository:
    """Thread-safe storage for pull requests, reviews, and repository pattern memory."""

    def __init__(self) -> None:
        self.pull_requests: dict[str, PullRequestRecord] = {}
        self.repo_patterns: dict[str, list[RepoPatternRecord]] = {}
        self.processed_shas: set[str] = set()

        # Seed initial sample data for clean dashboard demo out-of-the-box
        self._seed_initial_records()

    def _seed_initial_records(self) -> None:
        self.pull_requests["#284"] = PullRequestRecord(
            id="#284",
            repo="acme/platform-api",
            number=284,
            title="Refactor authentication middleware",
            author="sarahchen",
            head_sha="a1b2c3d4e5f67890",
            status="Action Required",
            score=76,
            summary="🚨 Critical security vulnerability detected in auth handler.",
            findings=[
                Finding(
                    severity="critical",
                    category="security",
                    title="Potential hard-coded credential",
                    description="Detected API token assignment in auth config.",
                    line=42,
                    file_path="config/auth.py",
                    suggestion="Move secret to os.environ.get('AUTH_SECRET')",
                ),
                Finding(
                    severity="medium",
                    category="correctness",
                    title="Broad exception handler",
                    description="Bare except clause catches all exceptions.",
                    line=108,
                    file_path="services/session.py",
                    suggestion="except AuthenticationError as err:\n    logger.warning(err)",
                ),
            ],
            analyzed_lines=146,
        )

        self.pull_requests["#283"] = PullRequestRecord(
            id="#283",
            repo="acme/platform-api",
            number=283,
            title="Add caching to user endpoints",
            author="marcus-dev",
            head_sha="f6e5d4c3b2a10987",
            status="Reviewed",
            score=94,
            summary="✅ Clean review. Minor maintainability suggestions.",
            findings=[
                Finding(
                    severity="low",
                    category="clean-code",
                    title="Leftover debug statement",
                    description="Found print statement in cache worker.",
                    line=16,
                    file_path="handlers/login.py",
                    suggestion="logger.debug('Cache populated')",
                ),
            ],
            analyzed_lines=89,
        )

    def is_sha_processed(self, sha: str) -> bool:
        return sha in self.processed_shas

    def mark_sha_processed(self, sha: str) -> None:
        self.processed_shas.add(sha)

    def save_pr_review(
        self,
        repo: str,
        number: int,
        title: str,
        author: str,
        head_sha: str,
        review_res: ReviewResponse,
    ) -> PullRequestRecord:
        crit_count = sum(1 for f in review_res.findings if f.severity == "critical")
        high_count = sum(1 for f in review_res.findings if f.severity == "high")

        # Calculate code quality score (100 base)
        score = max(0, 100 - (crit_count * 25) - (high_count * 10) - (len(review_res.findings) * 3))
        status = "Action Required" if crit_count > 0 else ("Reviewed" if score >= 80 else "Review Needed")

        pr_id = f"#{number}"
        record = PullRequestRecord(
            id=pr_id,
            repo=repo,
            number=number,
            title=title,
            author=author,
            head_sha=head_sha,
            status=status,
            score=score,
            summary=review_res.summary,
            findings=review_res.findings,
            analyzed_lines=review_res.analyzed_lines,
        )
        self.pull_requests[pr_id] = record
        self.mark_sha_processed(head_sha)
        return record

    def list_pull_requests(self) -> list[dict[str, Any]]:
        records = sorted(self.pull_requests.values(), key=lambda r: r.created_at, reverse=True)
        return [
            {
                "id": r.id,
                "title": r.title,
                "repo": r.repo,
                "author": r.author,
                "time": "Just now" if time.time() - r.created_at < 120 else f"{int((time.time() - r.created_at) // 60)} min ago",
                "status": r.status,
                "score": r.score,
                "files": len({f.file_path for f in r.findings if f.file_path}) or 1,
                "additions": r.analyzed_lines,
                "deletions": 0,
                "avatar": (r.author[:2] if r.author else "GH").upper(),
                "findings": [f.model_dump() for f in r.findings],
                "summary": r.summary,
            }
            for r in records
        ]

    def get_metrics(self) -> dict[str, Any]:
        total_prs = len(self.pull_requests)
        total_findings = sum(len(r.findings) for r in self.pull_requests.values())
        critical_issues = sum(
            sum(1 for f in r.findings if f.severity in ("critical", "high"))
            for r in self.pull_requests.values()
        )
        avg_score = (
            int(sum(r.score for r in self.pull_requests.values()) / total_prs)
            if total_prs > 0
            else 100
        )
        return {
            "total_pull_requests": total_prs,
            "total_findings": total_findings,
            "critical_issues_blocked": critical_issues,
            "average_quality_score": avg_score,
            "pipeline_status": "Healthy",
        }

    def add_learned_pattern(self, repo: str, pattern_type: str, description: str, confidence: float = 0.8) -> None:
        if repo not in self.repo_patterns:
            self.repo_patterns[repo] = []
        pattern_id = f"pat_{int(time.time() * 1000)}"
        self.repo_patterns[repo].append(
            RepoPatternRecord(
                id=pattern_id,
                repo=repo,
                pattern_type=pattern_type,
                rule_description=description,
                confidence=confidence,
            )
        )

    def get_repo_patterns(self, repo: str) -> list[str]:
        patterns = self.repo_patterns.get(repo, [])
        return [p.rule_description for p in patterns]


# Singleton instance across application
storage_repo = StorageRepository()
