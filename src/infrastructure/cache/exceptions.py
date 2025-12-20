"""Exceptions for semantic cache operations."""


class CacheError(Exception):
    """Base exception for cache operations."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CacheConfigurationError(CacheError):
    """Raised when cache configuration fails."""

    pass
