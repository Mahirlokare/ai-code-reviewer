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
