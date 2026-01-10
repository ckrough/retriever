"""Tracing utilities for instrumenting application code with OpenTelemetry."""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, overload

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Tracer

P = ParamSpec("P")
R = TypeVar("R")


def get_tracer(name: str) -> Tracer:
    """Get a tracer for the given module name.

    Args:
        name: Module name, typically __name__.

    Returns:
        A Tracer instance for creating spans.
    """
    return trace.get_tracer(name)


def add_span_attributes(attributes: dict[str, str | int | float | bool]) -> None:
    """Add attributes to the current span.

    Args:
        attributes: Key-value pairs to add to the span.
    """
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def get_current_trace_id() -> str | None:
    """Get the current trace ID as a hex string.

    Returns:
        The trace ID as a 32-character hex string, or None if no active trace.
    """
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if span_context.is_valid:
        return format(span_context.trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """Get the current span ID as a hex string.

    Returns:
        The span ID as a 16-character hex string, or None if no active span.
    """
    span = trace.get_current_span()
    span_context = span.get_span_context()
    if span_context.is_valid:
        return format(span_context.span_id, "016x")
    return None


@overload
def traced(  # noqa: UP047
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def traced(
    func: None = None,
    *,
    span_name: str | None = None,
    attributes: dict[str, str | int | float | bool] | None = None,
    record_exception: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def traced(  # noqa: UP047
    func: Callable[P, R] | None = None,
    *,
    span_name: str | None = None,
    attributes: dict[str, str | int | float | bool] | None = None,
    record_exception: bool = True,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to trace a function with OpenTelemetry.

    Works with both sync and async functions. Can be used with or without
    parentheses.

    Args:
        func: The function to trace (when used without parentheses).
        span_name: Name for the span (defaults to function name).
        attributes: Static attributes to add to the span.
        record_exception: Whether to record exceptions on the span.

    Returns:
        The decorated function.

    Examples:
        @traced
        def my_function():
            ...

        @traced(span_name="custom.name", attributes={"key": "value"})
        async def my_async_function():
            ...
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        tracer = get_tracer(fn.__module__)
        name = span_name or fn.__name__

        if asyncio.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                with tracer.start_as_current_span(name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    try:
                        result = await fn(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        if record_exception:
                            span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(fn)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                with tracer.start_as_current_span(name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    try:
                        result = fn(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        if record_exception:
                            span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise

            return sync_wrapper

    if func is not None:
        return decorator(func)
    return decorator
