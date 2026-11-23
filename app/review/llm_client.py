"""LLM client abstraction for AI-powered multi-agent code analysis with fallback."""
from __future__ import annotations

import json
import logging
import re
from typing import Any
import httpx

from app.core.config import settings
from app.schemas.review import Finding

logger = logging.getLogger(__name__)


def redact_secrets(content: str) -> str:
    """Redact hardcoded credentials before transmitting code to external models."""
    redacted = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_KEY]", content)
    redacted = re.sub(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b", "[REDACTED_GITHUB_TOKEN]", redacted)
    redacted = re.sub(r"\b(sk-[a-zA-Z0-9_-]{24,}|sk-ant-[a-zA-Z0-9_-]{32,})\b", "[REDACTED_API_KEY]", redacted)
    redacted = re.sub(
        r"\b(password|secret|token|api_key|passwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]",
        r"\1 = '[REDACTED_SECRET]'",
        redacted,
        flags=re.I,
    )
    return redacted


class LLMReviewClient:
    """Invokes LLM providers (Anthropic, OpenAI, Gemini) with fallback to deterministic agents."""

    def __init__(self) -> None:
        self.anthropic_key = settings.anthropic_api_key
        self.openai_key = settings.openai_api_key
        self.gemini_key = settings.gemini_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.anthropic_key or self.openai_key or self.gemini_key)

    async def review_diff_chunk(
        self,
        file_path: str,
        diff_content: str,
        language: str,
        repo_rules: list[str] | None = None,
    ) -> list[Finding]:
        if not self.is_configured:
            return []

        prompt = self._build_prompt(file_path, diff_content, language, repo_rules)

        try:
            if self.anthropic_key:
                return await self._call_anthropic(prompt)
            if self.openai_key:
                return await self._call_openai(prompt)
            if self.gemini_key:
                return await self._call_gemini(prompt)
        except Exception as exc:
            logger.warning("LLM review call failed; falling back to deterministic agents: %s", exc)

        return []

    def _build_prompt(
        self,
        file_path: str,
        diff_content: str,
        language: str,
        repo_rules: list[str] | None = None,
    ) -> str:
        rules_text = "\n".join(f"- {r}" for r in (repo_rules or []))
        safe_diff = redact_secrets(diff_content)
        return f"""You are an elite automated code review agent.
Analyze the following code diff for file '{file_path}' (language: {language}).

Identify critical vulnerabilities, security risks (OWASP), runtime bugs, off-by-one errors, resource leaks, and architectural flaws.
Rules to enforce:
{rules_text or '- Standard industry best practices and safe memory/type usage'}

<diff>
{safe_diff}
</diff>

Respond ONLY with a valid JSON array of findings adhering to this schema:
[
  {{
    "severity": "critical" | "high" | "medium" | "low" | "info",
    "category": "security" | "correctness" | "architecture" | "maintainability",
    "agent": "llm_agent",
    "title": "Short title",
    "description": "Clear explanation of the problem and failure scenario",
    "line": <line_number_in_new_file_or_null>,
    "confidence": 0.85,
    "suggestion": "Exact replacement code fix"
  }}
]
If there are no issues, return []."""

    async def _call_anthropic(self, prompt: str) -> list[Finding]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["content"][0]["text"]
            return self._parse_json_findings(text)

    async def _call_openai(self, prompt: str) -> list[Finding]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a code review assistant that responds only in JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return self._parse_json_findings(text)

    async def _call_gemini(self, prompt: str) -> list[Finding]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_json_findings(text)

    def _parse_json_findings(self, raw_text: str) -> list[Finding]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        parsed: Any = json.loads(cleaned)
        if isinstance(parsed, dict) and "findings" in parsed:
            parsed = parsed["findings"]

        if not isinstance(parsed, list):
            return []

        findings: list[Finding] = []
        for item in parsed:
            try:
                findings.append(Finding(
                    severity=item.get("severity", "medium"),
                    category=item.get("category", "correctness"),
                    agent="llm_agent",
                    title=item.get("title", "Review Finding"),
                    description=item.get("description", ""),
                    line=item.get("line"),
                    file_path=item.get("file_path"),
                    confidence=float(item.get("confidence", 0.85)),
                    suggestion=item.get("suggestion"),
                ))
            except Exception:
                continue
        return findings


llm_client = LLMReviewClient()
