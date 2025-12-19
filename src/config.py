"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "GoodPuppy"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM Provider (OpenRouter)
    openrouter_api_key: SecretStr | None = None
    llm_model: str = "anthropic/claude-sonnet-4"
    llm_fallback_model: str = "anthropic/claude-haiku"
    llm_timeout_seconds: float = 30.0

    # Rate limiting
    rate_limit_requests: int = 10
    rate_limit_window: str = "minute"

    # Circuit breaker
    circuit_breaker_fail_max: int = 5
    circuit_breaker_timeout: float = 60.0


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
