"""Structlog processor for OpenTelemetry trace context injection."""

from typing import Any

from opentelemetry import trace


def add_trace_context(
    logger: Any,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that adds trace_id and span_id to log events.

    This processor injects OpenTelemetry trace context into every log event,
    enabling correlation between logs and traces in observability backends.

    Args:
        logger: The logger instance (unused, required by structlog API).
        method_name: The log method name (unused, required by structlog API).
        event_dict: The log event dictionary to enrich.

    Returns:
        The enriched event dictionary with trace_id and span_id if available.
    """
    span = trace.get_current_span()
    span_context = span.get_span_context()

    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")

    return event_dict
