"""Transparent baseline review heuristics; findings are advisory."""
from __future__ import annotations

import re

from app.schemas.review import Finding, ReviewRequest, ReviewResponse

HUNK_RE = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
CREDENTIAL_RE = re.compile(r"\b(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*['\"\w-]{8,}", re.I)


class ReviewEngine:
    """Analyze added diff lines with conservative, explainable rules."""

    def review(self, request: ReviewRequest) -> ReviewResponse:
        findings: list[Finding] = []
        changed_lines = 0
        current_line: int | None = None
        for raw in request.diff.splitlines():
            match = HUNK_RE.search(raw)
            if match:
                current_line = int(match.group(1))
                continue
            if raw.startswith("+++"):
                continue
            if raw.startswith("+"):
                code = raw[1:]
                changed_lines += 1
                if "TODO" in code or "FIXME" in code:
                    findings.append(Finding(severity="low", category="maintainability",
                        title="TODO/FIXME in changed code",
                        description="A TODO or FIXME marker was added. Confirm it is tracked and intentional.",
                        line=current_line, confidence=0.78,
                        suggestion="Link the marker to a tracked issue or remove it before merging."))
                if CREDENTIAL_RE.search(code):
                    findings.append(Finding(severity="high", category="security",
                        title="Possible hard-coded credential",
                        description="This added line resembles a credential assignment. Verify that no real secret is committed.",
                        line=current_line, confidence=0.58,
                        suggestion="Use environment variables or a secret manager; rotate any exposed credential."))
                if re.search(r"\bprint\s*\(", code):
                    findings.append(Finding(severity="low", category="debugging",
                        title="Debug print statement",
                        description="A print statement was added. It may be leftover debugging output.",
                        line=current_line, confidence=0.65,
                        suggestion="Remove it or replace it with appropriate structured logging."))
                if re.search(r"\bexcept\s*:\s*(?:pass)?$", code.strip()):
                    findings.append(Finding(severity="medium", category="correctness",
                        title="Broad exception handling",
                        description="A bare except can hide unrelated errors and make failures difficult to diagnose.",
                        line=current_line, confidence=0.7,
                        suggestion="Catch the specific exception types expected here and handle or log them."))
                if current_line is not None:
                    current_line += 1
            elif raw.startswith("-") or raw.startswith("\\"):
                continue
            elif raw.startswith(" "):
                if current_line is not None:
                    current_line += 1
        summary = f"Analyzed {changed_lines} added line(s) with transparent baseline rules."
        return ReviewResponse(summary=summary, findings=findings, analyzed_lines=changed_lines,
                             engine="heuristic-v1")
