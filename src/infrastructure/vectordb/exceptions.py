"""Exceptions for vector store providers."""


class VectorStoreError(Exception):
    """Base exception for vector store errors."""

    def __init__(self, message: str, *, provider: str = "unknown") -> None:
        self.provider = provider
        super().__init__(message)


class VectorStoreConnectionError(VectorStoreError):
    """Raised when unable to connect to the vector store."""


class VectorStoreConfigurationError(VectorStoreError):
    """Raised when there's a configuration issue."""
