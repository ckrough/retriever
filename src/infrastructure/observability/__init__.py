"""Observability module providing OpenTelemetry tracing and structlog integration."""

from src.infrastructure.observability.setup import (
    init_observability,
    shutdown_observability,
)
from src.infrastructure.observability.structlog_processor import add_trace_context
from src.infrastructure.observability.tracing import (
    add_span_attributes,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    traced,
)

__all__ = [
    "add_span_attributes",
    "add_trace_context",
    "get_current_span_id",
    "get_current_trace_id",
    "get_tracer",
    "init_observability",
    "shutdown_observability",
    "traced",
]
