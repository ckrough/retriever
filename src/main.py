"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from src.api.health import router as health_router
from src.api.rate_limit import limiter, rate_limit_exceeded_handler
from src.config import get_settings
from src.web.admin_routes import router as admin_router
from src.web.routes import router as web_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    rate_limit_exceeded_handler,  # type: ignore[arg-type]
)

# Static files (optional - only mount if directory exists)
static_path = Path(__file__).parent / "web" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Register routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(admin_router, tags=["admin"])
app.include_router(web_router, tags=["web"])
