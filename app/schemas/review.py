"""Pydantic schemas for review requests and findings."""
from typing import Literal

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    diff: str = Field(min_length=1, max_length=150_000, description="Unified diff or code excerpt")
    language: str = Field(default="unknown", max_length=40)
    repository: str | None = Field(default=None, max_length=200)
    pull_request_number: int | None = Field(default=None, ge=1)


class RemoteReviewRequest(BaseModel):
    repo_url_or_slug: str = Field(min_length=3, max_length=300, description="GitHub repo URL (e.g. https://github.com/owner/repo), PR URL, commit URL, or slug 'owner/repo'")
    pr_number: int | None = Field(default=None, ge=1)


class DirectCodeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=150_000, description="Raw source code in any language")
    language: str = Field(default="python", max_length=40)
    filename: str = Field(default="snippet.py", max_length=100)


class Finding(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: str
    title: str
    description: str
    line: int | None = Field(default=None, ge=1)
    file_path: str | None = None
    agent: str | None = None
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    suggestion: str | None = None


class ReviewResponse(BaseModel):
    summary: str
    findings: list[Finding]
    analyzed_lines: int = Field(ge=0)
    engine: str
