"""Tests for application configuration."""

from retriever.config import Settings, get_settings


def test_settings_defaults() -> None:
    """Settings load with sensible defaults when no env vars present."""
    settings = Settings()
    assert settings.debug is False
    assert settings.langfuse_host == "https://us.cloud.langfuse.com"
    assert "http://localhost:5173" in settings.allowed_origins


def test_ai_gateway_base_url_fallback() -> None:
    """ai_gateway_base_url falls back to OpenRouter when CF not configured."""
    settings = Settings()
    assert settings.ai_gateway_base_url == "https://openrouter.ai/api/v1"


def test_ai_gateway_base_url_with_cloudflare() -> None:
    """ai_gateway_base_url returns CF gateway URL when both IDs are set."""
    settings = Settings(
        cloudflare_account_id="acct123",
        cloudflare_gateway_id="gw456",
    )
    url = settings.ai_gateway_base_url
    assert "gateway.ai.cloudflare.com" in url
    assert "acct123" in url
    assert "gw456" in url


def test_get_settings_returns_cached_instance() -> None:
    """get_settings returns the same instance on repeated calls."""
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_wildcard_origin_rejected() -> None:
    """Settings rejects wildcard '*' in allowed_origins."""
    import pytest

    with pytest.raises(Exception, match="Wildcard"):
        Settings(allowed_origins=["*"])
