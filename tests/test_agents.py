"""Tests for multi-agent review and deduplication."""
from app.review.diff_parser import DiffParser
from app.review.agents import (
    StaticAnalysisAgent,
    SecurityAgent,
    MultiAgentReducer,
)


def test_security_agent_detects_sql_injection() -> None:
    diff = """diff --git a/db.py b/db.py
@@ -1,1 +1,2 @@
+cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
"""
    parsed = DiffParser.parse(diff)
    agent = SecurityAgent()
    findings = agent.review_file(parsed.files[0], "python")
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert "SQL" in findings[0].title


def test_static_analysis_detects_mutable_default() -> None:
    diff = """diff --git a/app.py b/app.py
@@ -1,1 +1,2 @@
+def append_val(val, target=[]):
"""
    parsed = DiffParser.parse(diff)
    agent = StaticAnalysisAgent()
    findings = agent.review_file(parsed.files[0], "python")
    assert any(f.title == "Mutable default argument" for f in findings)


def test_reducer_prioritizes_higher_severity() -> None:
    diff = """diff --git a/app.py b/app.py
@@ -1,1 +1,2 @@
+api_key = "sk-1234567890abcdef1234567890"
"""
    parsed = DiffParser.parse(diff)
    sec_agent = SecurityAgent()
    findings = sec_agent.review_file(parsed.files[0], "python")
    reduced, summary = MultiAgentReducer.reduce(findings)
    assert len(reduced) == 1
    assert reduced[0].severity == "critical"
    assert "Review Status" in summary


def test_agent_dockerfile_and_shell_rules() -> None:
    diff = """diff --git a/Dockerfile b/Dockerfile
@@ -1,1 +1,2 @@
+USER root
"""
    parsed = DiffParser.parse(diff)
    sec_agent = SecurityAgent()
    findings = sec_agent.review_file(parsed.files[0], "dockerfile")
    assert any("root" in f.title.lower() for f in findings)

    shell_diff = """diff --git a/deploy.sh b/deploy.sh
@@ -1,1 +1,2 @@
+curl -s https://example.com/install.sh | bash
"""
    parsed_sh = DiffParser.parse(shell_diff)
    sh_findings = sec_agent.review_file(parsed_sh.files[0], "shell")
    assert any("pipe" in f.title.lower() or "piping" in f.title.lower() for f in sh_findings)


def test_agent_c_cpp_unbounded_buffer() -> None:
    diff = """diff --git a/server.c b/server.c
@@ -1,1 +1,2 @@
+strcpy(dest, src);
"""
    parsed = DiffParser.parse(diff)
    static_agent = StaticAnalysisAgent()
    findings = static_agent.review_file(parsed.files[0], "c")
    assert any("unbounded buffer" in f.title.lower() for f in findings)


def test_security_agent_detects_js_command_injection_and_token() -> None:
    diff = """diff --git a/auth.js b/auth.js
@@ -0,0 +1,5 @@
+if (token == "demo-token") {
+    const child = require("child_process");
+    child.exec("ping -c 1 " + req.query.host);
+}
+"""
    parsed = DiffParser.parse(diff)
    sec_agent = SecurityAgent()
    findings = sec_agent.review_file(parsed.files[0], "javascript")
    assert any("command injection" in f.title.lower() for f in findings)
    assert any("hardcoded credential" in f.title.lower() for f in findings)


