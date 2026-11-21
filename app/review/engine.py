"""Review engine coordinating deterministic checks.

Initial version deliberately uses simple transparent heuristics, not an LLM.
"""
from app.schemas.review import Finding, ReviewRequest, ReviewResponse


class ReviewEngine:
    """Produce actionable, evidence-oriented findings from diff text."""
    def review(self, request: ReviewRequest) -> ReviewResponse:
        diff_lines = request.diff.splitlines()
        findings: list[Finding] = []
        added_lines = [line[1:] for line in diff_lines if line.startswith("+") and not line.startswith("+++")]
        # Approximate diff line locations: track hunk line numbers where available.
        current_line: int | None = None
        for raw in diff_lines:
            if raw.startswith("@@"):
                try:
                    hunk = raw.split("+")[1].split(")[0].split(",")[0]
                    current_line = int(hunk)
                except (IndexError, ValueError):
                    current_line = None
                continue
            if raw.startswith("+") and not raw.startswith("+++"):
                code = raw[1:]
                if "TODO" in code or "FIXME" in code:
                    findings.append(Finding(severity="low", category="maintainability", title="TODO/FIXME left in changed code", description="A TODO or FIXME marker was added. Confirm it is intentional and tracked.", line=current_line, confidence=0.78))
                if any(token in code.lower() for token in ("password =", "api_key =", "secret =", "token =")):
                    findings.append(Finding(severity="high", category="security", title="Possible hard-coded credential", description="This changed line resembles a credential assignment. Verify that no real secret is committed; use environment-based secret management.", line=current_line, confidence=0.58))
                if "print(" in code:
                    findings.append(Finding(severity="low", category="debugging", title="Debug print statement", description="A print statement was added. Consider structured logging or remove it if it is temporary.", line=current_line, confidence=0.65))
                if current_line is not None:
                    current_line += 1
            elif not raw.startswith(("-", "\\")) and current_line is not None:
                current_line += 1
        summary = "Baseline heuristic review completed. Findings are advisory and require human validation."
        return ReviewResponse(summary=summary, findings=findings, analyzed_lines=len(added_lines), engine="heuristic-v0")
