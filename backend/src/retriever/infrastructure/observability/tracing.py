"""OpenTelemetry tracing configuration."""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.resource import ResourceAttributes


def configure_tracing(*, service_name: str, debug: bool = False) -> None:
    """Configure OTel tracing with console exporter (Phase 1 bootstrap)."""
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: service_name,
        }
    )

    provider = TracerProvider(resource=resource)

    if debug:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
