"""Schemas for user authentication, registration, and confirmation emails."""
from __future__ import annotations

import time
from pydantic import BaseModel, Field


class SignUpRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)


class SignInRequest(BaseModel):
    username_or_email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1)


class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    full_name: str | None = None
    created_at: float
    last_login: float | None = None
    avatar_url: str | None = None


class SentEmailRecord(BaseModel):
    id: str
    recipient: str
    subject: str
    body_html: str
    body_text: str
    email_type: str
    status: str
    created_at: float = Field(default_factory=time.time)


class AuthResponse(BaseModel):
    status: str = "success"
    message: str
    token: str
    user: UserProfile
    email_confirmation_sent: bool = True
    email_preview: SentEmailRecord | None = None
