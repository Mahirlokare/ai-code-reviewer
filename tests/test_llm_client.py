"""Tests for LLM review client and fallback behavior."""
from app.review.llm_client import LLMReviewClient


def test_llm_client_unconfigured_fallback() -> None:
    client = LLMReviewClient()
    # When keys are absent, is_configured should reflect that
    if not (client.anthropic_key or client.openai_key or client.gemini_key):
        assert client.is_configured is False


def test_llm_client_json_parser() -> None:
    client = LLMReviewClient()
    raw_markdown_json = """```json
[
  {
    "severity": "critical",
    "category": "security",
    "title": "SQL Injection",
    "description": "Tainted input in query",
    "line": 42,
    "file_path": "db.py",
    "confidence": 0.95,
    "suggestion": "cursor.execute(query, (id,))"
  }
]
```"""
    findings = client._parse_json_findings(raw_markdown_json)
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert findings[0].title == "SQL Injection"
    assert findings[0].line == 42


def test_secret_redaction_before_llm() -> None:
    from app.review.llm_client import redact_secrets
    raw_code = "api_key = 'sk-ant-api03-abcdef1234567890abcdef1234567890'\naws = 'AKIA1234567890ABCDEF'"
    redacted = redact_secrets(raw_code)
    assert "sk-ant" not in redacted
    assert "AKIA1234567890ABCDEF" not in redacted
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "[REDACTED_SECRET]" in redacted or "[REDACTED_API_KEY]" in redacted
