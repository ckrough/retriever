"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from src.api.health import router as health_router
from src.api.rate_limit import limiter, rate_limit_exceeded_handler
from src.config import get_settings
from src.infrastructure.database import Database, init_database
from src.modules.auth.repository import UserRepository
from src.modules.auth.routes import router as auth_api_router
from src.modules.auth.routes import set_auth_service as set_api_auth_service
from src.modules.auth.service import AuthService
from src.web.admin_routes import router as admin_router
from src.web.auth_routes import router as auth_web_router
from src.web.auth_routes import set_auth_service as set_web_auth_service
from src.web.dependencies import AuthenticationRequired, auth_exception_handler
from src.web.routes import router as web_router

logger = structlog.get_logger()
settings = get_settings()

# Database instance (initialized on startup)
_database: Database | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler for startup/shutdown."""
    global _database

    # Initialize database (sets global in connection module)
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _database = await init_database(db_path)
    logger.info("database_connected", path=str(db_path))

    # Initialize auth service if enabled
    if settings.auth_enabled and settings.jwt_secret_key:
        repository = UserRepository(_database)
        auth_service = AuthService(
            repository,
            jwt_secret=settings.jwt_secret_key.get_secret_value(),
            jwt_algorithm=settings.jwt_algorithm,
            jwt_expire_hours=settings.jwt_expire_hours,
        )
        set_api_auth_service(auth_service)
        set_web_auth_service(auth_service)
        logger.info("auth_service_initialized")
    else:
        logger.warning(
            "auth_disabled", reason="auth_enabled=False or jwt_secret_key not set"
        )

    yield

    # Cleanup on shutdown
    if _database:
        await _database.disconnect()
        logger.info("database_disconnected")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    rate_limit_exceeded_handler,  # type: ignore[arg-type]
)

# Authentication redirect
app.add_exception_handler(
    AuthenticationRequired,
    auth_exception_handler,  # type: ignore[arg-type]
)

# Static files (optional - only mount if directory exists)
static_path = Path(__file__).parent / "web" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Register routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(auth_api_router, tags=["authentication"])
app.include_router(auth_web_router, tags=["auth-web"])
app.include_router(admin_router, tags=["admin"])
app.include_router(web_router, tags=["web"])
