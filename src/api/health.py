"""Health check endpoints."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: Literal["healthy", "unhealthy"]
    version: str


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    from src.config import get_settings

    settings = get_settings()
    return HealthResponse(status="healthy", version=settings.app_version)
