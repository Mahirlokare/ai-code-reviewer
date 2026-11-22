"""Typed settings loaded from environment variables and optional .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Code Reviewer"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    anthropic_api_key: str | None = None
    github_app_id: str | None = None
    github_private_key_path: str | None = None
    github_webhook_secret: str | None = None
    database_url: str | None = None
    redis_url: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
