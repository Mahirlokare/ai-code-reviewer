"""Typed settings loaded from environment variables and optional .env file."""
import secrets
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Code Reviewer"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = [
        "https://ai-code-reviewer-ui-eq6s.onrender.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    github_app_id: str | None = None
    github_private_key_path: str | None = None
    github_webhook_secret: str | None = None
    github_token: str | None = None
    database_url: str | None = None
    redis_url: str | None = None
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    encryption_key: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "notifications@reviewpilot.ai"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
