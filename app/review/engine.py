"""Multi-agent review engine orchestrating Static, Security, Style, and Architecture analysis."""
from __future__ import annotations

from app.review.agents import (
    ArchitectureAgent,
    BaseReviewAgent,
    MultiAgentReducer,
    SecurityAgent,
    StaticAnalysisAgent,
    StyleAgent,
)
from app.review.diff_parser import DiffParser
from app.schemas.review import Finding, ReviewRequest, ReviewResponse


class ReviewEngine:
    """Orchestrates multi-agent analysis on code diffs."""

    def __init__(self, agents: list[BaseReviewAgent] | None = None) -> None:
        self.agents = agents or [
            StaticAnalysisAgent(),
            SecurityAgent(),
            StyleAgent(),
            ArchitectureAgent(),
        ]

    def review(self, request: ReviewRequest, repo_rules: list[str] | None = None) -> ReviewResponse:
        parsed = DiffParser.parse(request.diff)
        total_added_lines = parsed.total_added_lines

        raw_findings: list[Finding] = []
        for diff_file in parsed.files:
            for agent in self.agents:
                agent_findings = agent.review_file(
                    diff_file=diff_file,
                    language=request.language,
                    repo_rules=repo_rules,
                )
                raw_findings.extend(agent_findings)

        # Apply reduction & deduplication
        final_findings, summary = MultiAgentReducer.reduce(raw_findings)

        # Format overall summary with line statistics
        full_summary = f"{summary}\n\n*Analyzed {total_added_lines} added line(s) across {len(parsed.files)} file(s).*"

        return ReviewResponse(
            summary=full_summary,
            findings=final_findings,
            analyzed_lines=total_added_lines,
            engine="heuristic-v1",
        )
