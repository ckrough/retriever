"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic import SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: SecretStr = SecretStr("")
    supabase_service_role_key: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("")

    # OpenRouter
    openrouter_api_key: SecretStr = SecretStr("")

    # OpenAI
    openai_api_key: SecretStr = SecretStr("")

    # Langfuse
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_public_key: str = ""
    langfuse_host: str = "https://us.cloud.langfuse.com"

    # Cloudflare AI Gateway
    cloudflare_account_id: str = ""
    cloudflare_gateway_id: str = ""

    # GCP
    gcp_project_id: str = ""

    # App
    debug: bool = False
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("allowed_origins")
    @classmethod
    def no_wildcard_origins(cls, v: list[str]) -> list[str]:
        """Reject wildcard CORS origins — unsafe with allow_credentials=True."""
        if "*" in v:
            raise ValueError(
                "Wildcard '*' is not allowed in ALLOWED_ORIGINS. "
                "Enumerate specific origins instead."
            )
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ai_gateway_base_url(self) -> str:
        """Cloudflare AI Gateway base URL for OpenAI-compatible calls."""
        if self.cloudflare_account_id and self.cloudflare_gateway_id:
            return (
                f"https://gateway.ai.cloudflare.com/v1/"
                f"{self.cloudflare_account_id}/{self.cloudflare_gateway_id}/openai"
            )
        return "https://openrouter.ai/api/v1"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
