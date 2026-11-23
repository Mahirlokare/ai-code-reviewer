"""Specialized review agents and reducer for multi-agent code analysis."""
from __future__ import annotations

import re
from typing import ClassVar

from app.review.diff_parser import DiffFile, LineType
from app.schemas.review import Finding


class BaseReviewAgent:
    agent_name: str = "base"

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        raise NotImplementedError


class StaticAnalysisAgent(BaseReviewAgent):
    agent_name: str = "static_analysis"

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        findings: list[Finding] = []
        for hunk in diff_file.hunks:
            for line in hunk.lines:
                if line.line_type != LineType.ADD:
                    continue
                code = line.content.strip()
                line_no = line.new_line_no

                # Bare except check
                if re.search(r"\bexcept\s*:\s*(?:pass)?$", code):
                    findings.append(Finding(
                        severity="medium",
                        category="correctness",
                        agent=self.agent_name,
                        title="Broad bare exception handler",
                        description="A bare 'except:' catches SystemExit and KeyboardInterrupt and masks bugs.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.88,
                        suggestion="except Exception as err:\n    logger.error('Failed: %s', err)",
                    ))

                # Mutable default argument in Python
                if re.search(r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|set\(\))", code):
                    findings.append(Finding(
                        severity="high",
                        category="correctness",
                        agent=self.agent_name,
                        title="Mutable default argument",
                        description="Default argument values are shared across calls when mutable in Python.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.92,
                        suggestion="Use None as default: def func(param=None):\n    param = param if param is not None else []",
                    ))

                # Unclosed file handle
                if re.search(r"\b\w+\s*=\s*open\(", code) and not code.startswith("with "):
                    findings.append(Finding(
                        severity="medium",
                        category="resource-leak",
                        agent=self.agent_name,
                        title="Resource opened outside context manager",
                        description="Opening files or sockets without 'with' can leak file descriptors on exceptions.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.82,
                        suggestion="with open(...) as f:\n    ...",
                    ))

                # Loose equality in JavaScript/TypeScript
                if ("javascript" in language or "typescript" in language or diff_file.path.endswith((".js", ".ts", ".jsx", ".tsx"))) and re.search(r"\b(?<!=)==(?!=)\b", code):
                    findings.append(Finding(
                        severity="low",
                        category="type-safety",
                        agent=self.agent_name,
                        title="Loose equality (==) detected",
                        description="Loose equality performs unexpected type coercion in JavaScript.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.85,
                        suggestion="Use strict equality (===) instead.",
                    ))

        return findings


class SecurityAgent(BaseReviewAgent):
    agent_name: str = "security"

    SECRET_PATTERNS: ClassVar[list[tuple[str, re.Pattern]]] = [
        ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("GitHub Personal Access Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b")),
        ("OpenAI / Anthropic API Key", re.compile(r"\b(sk-[a-zA-Z0-9_-]{24,}|sk-ant-[a-zA-Z0-9_-]{32,})\b")),
        ("Generic Hardcoded Secret", re.compile(r"\b(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9+/=._-]{8,}['\"]", re.I)),
    ]

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        findings: list[Finding] = []
        for hunk in diff_file.hunks:
            for line in hunk.lines:
                if line.line_type != LineType.ADD:
                    continue
                code = line.content.strip()
                line_no = line.new_line_no

                # Secret scanning
                for secret_name, pat in self.SECRET_PATTERNS:
                    if pat.search(code):
                        findings.append(Finding(
                            severity="critical",
                            category="security",
                            agent=self.agent_name,
                            title=f"Potential {secret_name} exposed",
                            description="A secret or credential token appears hard-coded in the source code.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.95,
                            suggestion="Move the secret to an environment variable or secrets manager.",
                        ))
                        break

                # SQL Injection via string formatting
                if re.search(r"\b(execute|cursor\.execute|raw_sql)\s*\(\s*(f['\"]|['\"].*%\s*\(|['\"].*\+\s*\w+)", code, re.I):
                    findings.append(Finding(
                        severity="critical",
                        category="security",
                        agent=self.agent_name,
                        title="Potential SQL Injection vulnerability",
                        description="Query constructed via string formatting rather than parameterized statements.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.90,
                        suggestion="cursor.execute('SELECT * FROM table WHERE id = %s', (val,))",
                    ))

                # Command Injection
                if re.search(r"\b(os\.system|subprocess\.Popen|subprocess\.run|subprocess\.call)\s*\([^)]*shell\s*=\s*True", code):
                    findings.append(Finding(
                        severity="high",
                        category="security",
                        agent=self.agent_name,
                        title="Subprocess execution with shell=True",
                        description="Executing shell commands with shell=True permits command injection from untrusted input.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.91,
                        suggestion="Pass command arguments as a list without shell=True: subprocess.run(['cmd', arg1])",
                    ))

                # Unsafe deserialization
                if re.search(r"\b(pickle\.loads|yaml\.load\([^,)]*\))", code):
                    findings.append(Finding(
                        severity="high",
                        category="security",
                        agent=self.agent_name,
                        title="Insecure deserialization",
                        description="Arbitrary code execution risk with unverified pickle or unsafe yaml loading.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.89,
                        suggestion="Use yaml.safe_load(data) or json.loads(data).",
                    ))

        return findings


class StyleAgent(BaseReviewAgent):
    agent_name: str = "style"

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        findings: list[Finding] = []
        for hunk in diff_file.hunks:
            for line in hunk.lines:
                if line.line_type != LineType.ADD:
                    continue
                code = line.content.strip()
                line_no = line.new_line_no

                # Debug print statements
                if re.search(r"\b(print|console\.log|debugger;)\s*\(?", code) and not diff_file.path.startswith("test"):
                    findings.append(Finding(
                        severity="low",
                        category="debugging",
                        agent=self.agent_name,
                        title="Leftover debug statement",
                        description="Print or console.log statement found in production code.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.75,
                        suggestion="Remove the debug statement or use structured logging.",
                    ))

                # Unreferenced TODO
                if re.search(r"\b(TODO|FIXME)\b", code) and not re.search(r"#\d+|issue|\([A-Za-z0-9_-]+\)", code, re.I):
                    findings.append(Finding(
                        severity="info",
                        category="maintainability",
                        agent=self.agent_name,
                        title="Untracked TODO/FIXME marker",
                        description="TODO without an issue reference or tracking ticket.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.70,
                        suggestion="Attach a ticket reference: # TODO(#123): ...",
                    ))

        return findings


class ArchitectureAgent(BaseReviewAgent):
    agent_name: str = "architecture"

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        findings: list[Finding] = []

        # Check for layer boundary violation: direct database import in API controllers / frontend
        if "api" in diff_file.path or "routes" in diff_file.path:
            for hunk in diff_file.hunks:
                for line in hunk.lines:
                    if line.line_type == LineType.ADD:
                        code = line.content.strip()
                        if re.search(r"from\s+(?:psycopg2|sqlalchemy\.orm\.session|asyncpg)\s+import", code):
                            findings.append(Finding(
                                severity="medium",
                                category="architecture",
                                agent=self.agent_name,
                                title="Layer boundary leak in API route",
                                description="Direct database session driver imported in route handler rather than repository/service layer.",
                                line=line.new_line_no,
                                file_path=diff_file.path,
                                confidence=0.80,
                                suggestion="Inject the database dependency via the service layer.",
                            ))

        # Check for overly complex additions in single hunk
        for hunk in diff_file.hunks:
            added_in_hunk = [l for l in hunk.lines if l.line_type == LineType.ADD]
            if len(added_in_hunk) > 60:
                first_line = added_in_hunk[0].new_line_no
                findings.append(Finding(
                    severity="low",
                    category="architecture",
                    agent=self.agent_name,
                    title="High hunk complexity (>60 added lines)",
                    description="Consider decomposing this large block into smaller modular helper functions.",
                    line=first_line,
                    file_path=diff_file.path,
                    confidence=0.68,
                    suggestion="Refactor into smaller, single-responsibility functions.",
                ))

        return findings


class MultiAgentReducer:
    """Combines findings, eliminates duplicates, and formats executive summary."""

    SEVERITY_ORDER: ClassVar[dict[str, int]] = {
        "critical": 5,
        "high": 4,
        "medium": 3,
        "low": 2,
        "info": 1,
    }

    @classmethod
    def reduce(cls, raw_findings: list[Finding], min_confidence: float = 0.60) -> tuple[list[Finding], str]:
        # Filter low confidence
        filtered = [f for f in raw_findings if f.confidence >= min_confidence]

        # Deduplicate on (file_path, line)
        dedup_map: dict[tuple[str | None, int | None], Finding] = {}
        for f in filtered:
            key = (f.file_path, f.line)
            if key not in dedup_map:
                dedup_map[key] = f
            else:
                existing = dedup_map[key]
                # Prioritize higher severity
                if cls.SEVERITY_ORDER.get(f.severity, 0) > cls.SEVERITY_ORDER.get(existing.severity, 0):
                    dedup_map[key] = f

        final_findings = sorted(
            dedup_map.values(),
            key=lambda x: cls.SEVERITY_ORDER.get(x.severity, 0),
            reverse=True,
        )

        # Build executive summary markdown
        crit_count = sum(1 for f in final_findings if f.severity == "critical")
        high_count = sum(1 for f in final_findings if f.severity == "high")
        med_count = sum(1 for f in final_findings if f.severity == "medium")
        low_count = sum(1 for f in final_findings if f.severity in ("low", "info"))

        if crit_count > 0:
            status = "🚨 **Review Status: Action Required (Critical Vulnerabilities Detected)**"
        elif high_count > 0:
            status = "⚠️ **Review Status: Warning (High-Severity Issues Found)**"
        elif med_count > 0:
            status = "🔍 **Review Status: Observations (Improvements Recommended)**"
        else:
            status = "✅ **Review Status: Passed (Clean Pull Request)**"

        summary = (
            f"{status}\n\n"
            f"**Multi-Agent Findings Breakdown:**\n"
            f"- 🔴 Critical: {crit_count}\n"
            f"- 🟠 High: {high_count}\n"
            f"- 🟡 Medium: {med_count}\n"
            f"- 🔵 Low / Info: {low_count}\n\n"
            f"All findings have been synthesized across the Static Analysis, Security, Style, and Architecture agents."
        )

        return final_findings, summary
