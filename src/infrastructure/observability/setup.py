"""OpenTelemetry setup and initialization."""

import logging
from typing import TYPE_CHECKING

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

from src.infrastructure.observability.structlog_processor import add_trace_context

if TYPE_CHECKING:
    from fastapi import FastAPI

# Module-level state for cleanup
_tracer_provider: TracerProvider | None = None
_initialized: bool = False


def init_observability(
    service_name: str,
    service_version: str,
    *,
    otlp_endpoint: str | None = None,
    console_export: bool = False,
    enabled: bool = True,
    sample_rate: float = 1.0,
    app: "FastAPI | None" = None,
) -> None:
    """Initialize OpenTelemetry tracing and configure structlog integration.

    This function sets up the global tracer provider with the specified exporter,
    configures structlog to include trace context in logs, and optionally
    instruments FastAPI.

    Args:
        service_name: Name of the service for resource attribution.
        service_version: Version of the service.
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4318").
            If None and console_export is False, no exporter is configured.
        console_export: If True, export spans to console (for development).
        enabled: If False, tracing is completely disabled (no-op provider).
        sample_rate: Sampling rate between 0.0 and 1.0. Default is 1.0 (all traces).
        app: Optional FastAPI app instance to instrument.
    """
    global _tracer_provider, _initialized

    if _initialized:
        return

    if not enabled:
        # Set no-op tracer provider
        trace.set_tracer_provider(trace.NoOpTracerProvider())
        _initialized = True
        return

    # Create resource with service metadata
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
        }
    )

    # Configure sampler
    sampler = ParentBasedTraceIdRatio(sample_rate)

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource, sampler=sampler)

    # Add exporters
    if console_export:
        _tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Configure structlog with trace context processor
    _configure_structlog()

    # Instrument FastAPI if app provided
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)

    # Instrument httpx for outgoing HTTP calls
    HTTPXClientInstrumentor().instrument()

    _initialized = True


def shutdown_observability() -> None:
    """Shutdown the tracer provider and flush any pending spans.

    This should be called during application shutdown to ensure all
    spans are exported before the process exits.
    """
    global _tracer_provider, _initialized

    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None

    _initialized = False


def _configure_structlog() -> None:
    """Configure structlog with OpenTelemetry trace context injection.

    This adds the trace context processor to the structlog processing chain,
    ensuring that trace_id and span_id are included in all log events.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            add_trace_context,  # Inject trace context
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )
