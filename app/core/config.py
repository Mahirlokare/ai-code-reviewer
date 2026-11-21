"""Typed settings loaded from environment variables and optional .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Code Reviewer"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    anthropic_api_key: str | None = None
    github_app_id: str | None = None
    github_private_key_path: str | None = None
    github_webhook_secret: str | None = None
    database_url: str = "postgresql+psycopg://reviewer:reviewer@localhost:5432/reviewer"
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
