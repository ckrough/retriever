"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retriever.config import get_settings
from retriever.infrastructure.observability.logging import configure_logging
from retriever.infrastructure.observability.tracing import configure_tracing

health_router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "unhealthy"]
    version: str


@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="2.0.0")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan: startup and shutdown."""
    logger = structlog.get_logger(__name__)
    logger.info("retriever.startup")
    yield
    logger.info("retriever.shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(debug=settings.debug)
    configure_tracing(service_name="retriever", debug=settings.debug)

    app = FastAPI(
        title="Retriever",
        description="AI-powered Q&A system for shelter volunteers",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(health_router)

    return app


app = create_app()
