"""Tests for observability configuration (logging and tracing)."""

import structlog

from retriever.infrastructure.observability.logging import configure_logging
from retriever.infrastructure.observability.tracing import configure_tracing


def test_configure_logging_production_mode() -> None:
    """configure_logging sets up structlog without errors in production mode."""
    configure_logging(debug=False)
    logger = structlog.get_logger("test")
    # Should not raise
    assert logger is not None


def test_configure_logging_debug_mode() -> None:
    """configure_logging sets up structlog without errors in debug mode."""
    configure_logging(debug=True)
    # structlog configured successfully — just verify it doesn't raise
    logger = structlog.get_logger("test_debug")
    assert logger is not None


def test_configure_tracing_no_debug() -> None:
    """configure_tracing completes without errors in non-debug mode."""
    # Should not raise; no exporter attached
    configure_tracing(service_name="test-service", debug=False)


def test_configure_tracing_debug_mode() -> None:
    """configure_tracing attaches console exporter in debug mode."""
    # Should not raise; console exporter attached
    configure_tracing(service_name="test-service", debug=True)
