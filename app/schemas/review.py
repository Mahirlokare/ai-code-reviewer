"""Pydantic schemas for review requests and findings."""
from typing import Literal

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    diff: str = Field(min_length=1, description="Unified diff or code excerpt")
    language: str = Field(default="unknown", max_length=40)
    repository: str | None = Field(default=None, max_length=200)
    pull_request_number: int | None = Field(default=None, ge=1)


class Finding(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: str
    title: str
    description: str
    line: int | None = Field(default=None, ge=1)
    confidence: float = Field(ge=0.0, le=1.0)
    suggestion: str | None = None


class ReviewResponse(BaseModel):
    summary: str
    findings: list[Finding]
    analyzed_lines: int = Field(ge=0)
    engine: str
