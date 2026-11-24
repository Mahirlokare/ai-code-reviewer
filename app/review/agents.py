"""Comprehensive multi-language review agents and reducer for universal code analysis."""
from __future__ import annotations

import re
from typing import ClassVar

from app.review.diff_parser import DiffFile, LineType
from app.schemas.review import Finding


class BaseReviewAgent:
    agent_name: str = "base"

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        raise NotImplementedError

    @staticmethod
    def detect_language(diff_file: DiffFile, fallback: str = "unknown") -> str:
        path = diff_file.path.lower()
        if path.endswith((".py", ".pyw")):
            return "python"
        if path.endswith((".js", ".jsx", ".mjs")):
            return "javascript"
        if path.endswith((".ts", ".tsx")):
            return "typescript"
        if path.endswith(".go"):
            return "go"
        if path.endswith(".rs"):
            return "rust"
        if path.endswith((".java", ".kt", ".kts")):
            return "java"
        if path.endswith((".c", ".cpp", ".cc", ".cxx", ".h", ".hpp")):
            return "c_cpp"
        if path.endswith(".cs"):
            return "csharp"
        if path.endswith((".php", ".phtml")):
            return "php"
        if path.endswith((".rb", ".rake")):
            return "ruby"
        if path.endswith((".sh", ".bash", ".zsh")):
            return "shell"
        if path.endswith((".sql",)):
            return "sql"
        if "dockerfile" in path:
            return "dockerfile"
        if path.endswith((".yaml", ".yml")):
            return "yaml"
        return fallback.lower()


class StaticAnalysisAgent(BaseReviewAgent):
    agent_name: str = "static_analysis"

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        findings: list[Finding] = []
        lang = self.detect_language(diff_file, language)

        for hunk in diff_file.hunks:
            for line in hunk.lines:
                if line.line_type != LineType.ADD:
                    continue
                code = line.content.strip()
                line_no = line.new_line_no

                # --- 1. Python Rules ---
                if lang == "python":
                    if re.search(r"\bexcept\s*:\s*(?:pass)?$", code):
                        findings.append(Finding(
                            severity="medium",
                            category="correctness",
                            agent=self.agent_name,
                            title="Broad bare exception handler",
                            description="Catching bare 'except:' intercepts SystemExit, KeyboardInterrupt, and masks runtime errors.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.90,
                            suggestion="except Exception as err:\n    logger.error('Operation failed: %s', err)",
                        ))
                    if re.search(r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|set\(\))", code):
                        findings.append(Finding(
                            severity="high",
                            category="correctness",
                            agent=self.agent_name,
                            title="Mutable default argument",
                            description="Default argument values are evaluated once at definition time and shared across invocations.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.94,
                            suggestion="def func(param=None):\n    param = param if param is not None else []",
                        ))
                    if re.search(r"\b\w+\s*=\s*open\(", code) and not code.startswith("with "):
                        findings.append(Finding(
                            severity="medium",
                            category="resource-leak",
                            agent=self.agent_name,
                            title="Unmanaged file resource",
                            description="Opening files outside a 'with' context manager risks file descriptor leaks if exceptions occur.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.85,
                            suggestion="with open(...) as f:\n    content = f.read()",
                        ))

                # --- 2. JavaScript & TypeScript Rules ---
                elif lang in ("javascript", "typescript"):
                    if re.search(r"\b(?<!=)==(?!=)\b", code):
                        findings.append(Finding(
                            severity="low",
                            category="type-safety",
                            agent=self.agent_name,
                            title="Loose equality (==) detected",
                            description="Loose equality performs implicit type coercion which frequently causes subtle logic bugs.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.88,
                            suggestion="Use strict equality (===) to ensure value and type consistency.",
                        ))
                    if lang == "typescript" and re.search(r":\s*any\b", code):
                        findings.append(Finding(
                            severity="low",
                            category="type-safety",
                            agent=self.agent_name,
                            title="Explicit 'any' type annotation",
                            description="Using 'any' disables TypeScript compiler type-safety guarantees.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.75,
                            suggestion="Use a specific type, interface, or 'unknown' with type-narrowing.",
                        ))

                # --- 3. Go (Golang) Rules ---
                elif lang == "go":
                    if re.search(r"\b_\s*,\s*_\s*=\s*\w+\(", code):
                        findings.append(Finding(
                            severity="medium",
                            category="correctness",
                            agent=self.agent_name,
                            title="Ignored error return in Go",
                            description="Discarding error returns with blank identifiers hides critical failure states.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.85,
                            suggestion="val, err := func()\nif err != nil {\n    return fmt.Errorf(\"failed: %w\", err)\n}",
                        ))
                    if re.search(r"^\s*defer\s+", code) and "for " in code:
                        findings.append(Finding(
                            severity="high",
                            category="resource-leak",
                            agent=self.agent_name,
                            title="Defer statement inside loop",
                            description="Defer inside a loop only executes when the surrounding function returns, potentially exhausting file descriptors or memory.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.88,
                            suggestion="Wrap the loop body in an anonymous function or close resources explicitly.",
                        ))

                # --- 4. Rust Rules ---
                elif lang == "rust":
                    if re.search(r"\.(unwrap|expect)\s*\(", code) and not diff_file.path.startswith("tests"):
                        findings.append(Finding(
                            severity="medium",
                            category="reliability",
                            agent=self.agent_name,
                            title="Direct unwrap/expect in production Rust code",
                            description="Calling .unwrap() will trigger a thread panic if the Result or Option contains Err/None.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.82,
                            suggestion="Use the '?' operator or handle the error with match/if let.",
                        ))

                # --- 5. Java & Kotlin Rules ---
                elif lang == "java":
                    if re.search(r'"[^"]*"\s*==\s*\w+|\w+\s*==\s*"[^"]*"', code):
                        findings.append(Finding(
                            severity="high",
                            category="correctness",
                            agent=self.agent_name,
                            title="String reference comparison with ==",
                            description="Comparing Strings with '==' checks reference identity rather than content equality in Java.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.92,
                            suggestion="Use str1.equals(str2) or Objects.equals(str1, str2).",
                        ))

                # --- 6. C & C++ Rules ---
                elif lang == "c_cpp":
                    if re.search(r"\b(strcpy|strcat|sprintf|gets)\s*\(", code):
                        findings.append(Finding(
                            severity="critical",
                            category="security",
                            agent=self.agent_name,
                            title="Unbounded buffer operation",
                            description="Unsafe C library function susceptible to stack buffer overflows.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.96,
                            suggestion="Use bounded alternatives: strncpy(), snprintf(), or std::string.",
                        ))

                # --- 7. C# (.NET) Rules ---
                elif lang == "csharp":
                    if re.search(r"\.Result\b|\.Wait\(\)", code):
                        findings.append(Finding(
                            severity="medium",
                            category="performance",
                            agent=self.agent_name,
                            title="Synchronous wait on async Task",
                            description="Accessing .Result or calling .Wait() causes thread pool starvation and potential deadlocks.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.86,
                            suggestion="Use async/await: await task;",
                        ))

                # --- 8. Shell / Bash Rules ---
                elif lang == "shell":
                    if re.search(r'\b(rm|cp|mv)\s+-[rf]*\s+\$[A-Za-z0-9_]+', code) and '"' not in code:
                        findings.append(Finding(
                            severity="high",
                            category="correctness",
                            agent=self.agent_name,
                            title="Unquoted variable in filesystem command",
                            description="Unquoted variables undergo word splitting and globbing, which can delete unexpected paths if whitespace exists.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.88,
                            suggestion='Quote the variable: rm -rf "$VAR"',
                        ))

        return findings


class SecurityAgent(BaseReviewAgent):
    agent_name: str = "security"

    SECRET_PATTERNS: ClassVar[list[tuple[str, re.Pattern]]] = [
        ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("GitHub Personal Access Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b")),
        ("OpenAI / Anthropic API Key", re.compile(r"\b(sk-[a-zA-Z0-9_-]{24,}|sk-ant-[a-zA-Z0-9_-]{32,})\b")),
        ("Private Encryption Key", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
        ("Generic Hardcoded Secret", re.compile(r"\b(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9+/=._-]{8,}['\"]", re.I)),
    ]

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        findings: list[Finding] = []
        lang = self.detect_language(diff_file, language)

        for hunk in diff_file.hunks:
            for line in hunk.lines:
                if line.line_type != LineType.ADD:
                    continue
                code = line.content.strip()
                line_no = line.new_line_no

                # 1. Universal Secret Scanning
                for secret_name, pat in self.SECRET_PATTERNS:
                    if pat.search(code):
                        findings.append(Finding(
                            severity="critical",
                            category="security",
                            agent=self.agent_name,
                            title=f"Potential {secret_name} committed",
                            description="A secret token or private credential appears directly in source code.",
                            line=line_no,
                            file_path=diff_file.path,
                            confidence=0.96,
                            suggestion="Extract credentials into environment variables or a vault manager.",
                        ))
                        break

                # 2. SQL Injection (Cross-Language)
                if (
                    re.search(r"\b(execute|cursor\.execute|raw_sql|query|db\.query)\s*\(\s*(f['\"]|['\"].*%\s*\(|['\"].*\+\s*\w+|\$query|\"[^\"]*\$\w+)", code, re.I)
                    or re.search(r"\b(query|sql|stmt|command)\s*=\s*(f['\"].*(?:SELECT|INSERT|UPDATE|DELETE|DROP)|['\"].*(?:SELECT|INSERT|UPDATE|DELETE|DROP).*['\"]\s*\+)", code, re.I)
                    or re.search(r"\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\b.*(?:\{[a-zA-Z0-9_]+\}|\'\s*\+|\$\w+)", code, re.I)
                ):
                    findings.append(Finding(
                        severity="critical",
                        category="security",
                        agent=self.agent_name,
                        title="Potential SQL Injection vulnerability",
                        description="Query string constructed via concatenation or string formatting rather than parameterized placeholders.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.92,
                        suggestion="Use parameterized queries: db.execute('SELECT * FROM users WHERE id = ?', [user_id])",
                    ))

                # 3. Command Injection
                if (
                    re.search(r"\b(os\.system|subprocess\.Popen|subprocess\.run|subprocess\.call)\s*\([^)]*shell\s*=\s*True", code)
                    or re.search(r"\b(child_process|child|sh|shell)\.(exec|execSync|spawn|spawnSync)\s*\(", code)
                    or re.search(r"\b(exec|system|passthru|shell_exec)\s*\(.*(?:\+|\$|req\.)", code)
                ):
                    findings.append(Finding(
                        severity="critical",
                        category="security",
                        agent=self.agent_name,
                        title="Command Injection / Unsafe Shell Execution",
                        description="Invoking system shells with untrusted input permits arbitrary remote command execution.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.94,
                        suggestion="Pass arguments as a structured array without shell interpretation, or validate input against an allowlist.",
                    ))

                # 4. Insecure Authentication / Hardcoded Token Check
                if re.search(r"\b(token|secret|password|api_key)\s*={2,3}\s*['\"][A-Za-z0-9_-]{4,}['\"]", code, re.I):
                    findings.append(Finding(
                        severity="high",
                        category="security",
                        agent=self.agent_name,
                        title="Hardcoded credential comparison",
                        description="Authentication token or secret verified against hardcoded string; susceptible to credential exposure and timing attacks.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.90,
                        suggestion="Compare securely with crypto.timingSafeEqual() against a secret stored in process.env.AUTH_TOKEN",
                    ))

                # 5. Insecure Deserialization & Evaluation
                if (
                    re.search(r"\b(pickle\.loads|yaml\.load\([^,)]*\))", code)
                    or re.search(r"\beval\s*\(", code)
                ):
                    findings.append(Finding(
                        severity="high",
                        category="security",
                        agent=self.agent_name,
                        title="Dangerous dynamic evaluation / deserialization",
                        description="Dynamic evaluation or unverified deserialization allows arbitrary code execution.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.90,
                        suggestion="Use safe formats like json.loads() or yaml.safe_load().",
                    ))

                # 6. Dangerous Remote Execution in Shell
                if lang == "shell" and re.search(r"(curl|wget)\s+.*\|\s*(bash|sh|zsh)", code):
                    findings.append(Finding(
                        severity="critical",
                        category="security",
                        agent=self.agent_name,
                        title="Piping unverified remote script to shell",
                        description="Executing remote scripts directly via pipe exposes systems to man-in-the-middle tampering.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.95,
                        suggestion="Download script to disk, verify checksum/GPG signature, then execute.",
                    ))

                # 7. Dockerfile Root Execution
                if lang == "dockerfile" and re.search(r"^\s*USER\s+root\b", code):
                    findings.append(Finding(
                        severity="medium",
                        category="security",
                        agent=self.agent_name,
                        title="Container running as root user",
                        description="Containers running as root increase host compromise risk if container breakout occurs.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.85,
                        suggestion="Switch to a non-privileged user: USER appuser",
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

                # Cross-language debug print statements
                if (
                    re.search(r"\b(print|console\.log|debugger;|fmt\.Println|System\.out\.println|var_dump|dd)\s*\(?", code)
                    and not any(diff_file.path.startswith(prefix) for prefix in ("test", "spec", "__test__"))
                ):
                    findings.append(Finding(
                        severity="low",
                        category="debugging",
                        agent=self.agent_name,
                        title="Leftover debug statement",
                        description="Debug logging statement detected in production code path.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.78,
                        suggestion="Remove temporary debug output or replace with structured logging.",
                    ))

                # Untracked TODO / FIXME
                if re.search(r"\b(TODO|FIXME)\b", code) and not re.search(r"#\d+|issue|\([A-Za-z0-9_-]+\)", code, re.I):
                    findings.append(Finding(
                        severity="info",
                        category="maintainability",
                        agent=self.agent_name,
                        title="Untracked TODO marker",
                        description="TODO without an issue reference or tracking ticket.",
                        line=line_no,
                        file_path=diff_file.path,
                        confidence=0.70,
                        suggestion="Link the marker to a tracking ticket: // TODO(#456): ...",
                    ))

        return findings


class ArchitectureAgent(BaseReviewAgent):
    agent_name: str = "architecture"

    def review_file(self, diff_file: DiffFile, language: str, repo_rules: list[str] | None = None) -> list[Finding]:
        findings: list[Finding] = []

        # Layer boundary violation: direct database import in API controllers / frontend
        if any(term in diff_file.path.lower() for term in ("api", "routes", "controllers", "handlers")):
            for hunk in diff_file.hunks:
                for line in hunk.lines:
                    if line.line_type == LineType.ADD:
                        code = line.content.strip()
                        if re.search(r"from\s+(?:psycopg2|sqlalchemy\.orm\.session|asyncpg)\s+import|import\s+(?:mysql|pg|sqlite3)\b", code):
                            findings.append(Finding(
                                severity="medium",
                                category="architecture",
                                agent=self.agent_name,
                                title="Layer boundary leak in API controller",
                                description="Direct database session driver imported in route handler rather than repository/service layer.",
                                line=line.new_line_no,
                                file_path=diff_file.path,
                                confidence=0.82,
                                suggestion="Inject the database dependency via the service layer.",
                            ))

        # Check for oversized hunk complexity
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
    """Combines findings, eliminates duplicates, and formats humanized executive summaries."""

    SEVERITY_ORDER: ClassVar[dict[str, int]] = {
        "critical": 5,
        "high": 4,
        "medium": 3,
        "low": 2,
        "info": 1,
    }

    @classmethod
    def reduce(
        cls,
        raw_findings: list[Finding],
        min_confidence: float = 0.60,
        max_comments: int = 10,
    ) -> tuple[list[Finding], str]:
        filtered = [f for f in raw_findings if f.confidence >= min_confidence]

        dedup_map: dict[tuple[str | None, int | None], Finding] = {}
        for f in filtered:
            key = (f.file_path, f.line)
            if key not in dedup_map:
                dedup_map[key] = f
            else:
                existing = dedup_map[key]
                if cls.SEVERITY_ORDER.get(f.severity, 0) > cls.SEVERITY_ORDER.get(existing.severity, 0):
                    dedup_map[key] = f

        all_deduped = sorted(
            dedup_map.values(),
            key=lambda x: cls.SEVERITY_ORDER.get(x.severity, 0),
            reverse=True,
        )

        total_findings_count = len(all_deduped)
        final_findings = all_deduped[:max_comments]

        crit_count = sum(1 for f in all_deduped if f.severity == "critical")
        high_count = sum(1 for f in all_deduped if f.severity == "high")
        med_count = sum(1 for f in all_deduped if f.severity == "medium")
        low_count = sum(1 for f in all_deduped if f.severity in ("low", "info"))

        if crit_count > 0:
            status = "🚨 **Review Status: Action Required**\nCritical vulnerabilities detected that should be addressed before merging."
        elif high_count > 0:
            status = "⚠️ **Review Status: Review Advised**\nHigh-priority issues detected in changed code paths."
        elif med_count > 0:
            status = "🔍 **Review Status: Improvements Recommended**\nSolid foundation with a few correctness or maintainability suggestions."
        else:
            status = "✅ **Review Status: Approved**\nCode looks clean, idiomatic, and adheres to safety best practices!"

        cap_note = ""
        if total_findings_count > max_comments:
            cap_note = f"\n*Displaying top {max_comments} most impactful findings out of {total_findings_count} total detected.*\n"

        summary = (
            f"{status}\n\n"
            f"**Findings Breakdown:**\n"
            f"- 🔴 Critical: {crit_count}\n"
            f"- 🟠 High: {high_count}\n"
            f"- 🟡 Medium: {med_count}\n"
            f"- 🔵 Low / Info: {low_count}\n"
            f"{cap_note}\n"
            f"All findings synthesized across Static Analysis, Security, Style, and Architecture reviewers."
        )

        return final_findings, summary
