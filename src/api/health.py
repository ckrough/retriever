"""Health check endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.config import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: Literal["healthy", "unhealthy"]
    version: str


@router.get("", response_model=HealthResponse)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(status="healthy", version=settings.app_version)
