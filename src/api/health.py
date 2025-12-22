"""Health check endpoints."""

from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.config import Settings, get_settings
from src.infrastructure.database import get_database

logger = structlog.get_logger()
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: Literal["healthy", "unhealthy"]
    version: str


@router.get("", response_model=HealthResponse)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Health check endpoint with dependency verification.

    Verifies:
    - Database connectivity (SQLite)
    - Vector database availability would be checked here if needed

    Returns:
        HealthResponse with status and version.

    Raises:
        HTTPException: 503 if any critical dependency is unavailable.
    """
    try:
        # Verify database connectivity with a simple query
        db = get_database()
        await db.execute("SELECT 1")

        # Note: We don't check ChromaDB here because:
        # 1. It's lazy-loaded and not always initialized
        # 2. Health checks should be lightweight and fast
        # 3. Database check is sufficient for container orchestration

        return HealthResponse(status="healthy", version=settings.app_version)
    except Exception as e:
        logger.error("health_check_failed", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {type(e).__name__}",
        ) from e
