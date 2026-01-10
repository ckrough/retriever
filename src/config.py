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
    app_name: str = "Retriever"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server - bind to all interfaces for container deployment
    host: str = "0.0.0.0"  # nosec B104
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

    # Prompt caching (Anthropic models via OpenRouter)
    llm_enable_prompt_caching: bool = True

    # Embeddings (via OpenRouter)
    embedding_api_key: SecretStr | None = None
    embedding_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_timeout_seconds: float = 30.0

    # Chroma Vector Database
    chroma_persist_path: str = "./data/chroma"
    chroma_collection_name: str = "retriever_documents"

    # RAG Settings
    rag_chunk_size: int = 1500  # Characters
    rag_chunk_overlap: int = 800  # Characters
    rag_top_k: int = 5  # Number of chunks to retrieve
    documents_path: str = "./documents"
    uploads_path: str = "./uploads"  # Directory for user-uploaded documents

    # Semantic Cache
    cache_enabled: bool = True  # Enable semantic caching for faster responses
    cache_similarity_threshold: float = 0.95  # Minimum similarity for cache hit (0-1)
    cache_ttl_hours: int = 24  # Time-to-live for cached entries

    # Hybrid Retrieval
    hybrid_retrieval_enabled: bool = True  # Enable hybrid (semantic + keyword) search
    hybrid_semantic_weight: float = 0.5  # Weight for semantic search (0-1)
    hybrid_keyword_weight: float = 0.5  # Weight for keyword search (0-1)
    hybrid_rrf_k: int = 60  # RRF constant (higher = more uniform ranking)

    # Content Safety
    safety_enabled: bool = True  # Enable content safety checks
    openai_api_key: SecretStr | None = None  # For moderation API (free)
    moderation_timeout_seconds: float = 10.0  # Moderation API timeout
    hallucination_threshold: float = 0.8  # Min claim support ratio (0-1)

    # Database
    database_path: str = "./data/retriever.db"

    # Authentication
    auth_enabled: bool = True  # Enable authentication
    jwt_secret_key: SecretStr | None = None  # Secret for JWT signing
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24  # Token expiration in hours

    # Conversation History
    conversation_max_messages: int = 20  # Max messages to include in context


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
