"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.health import router as health_router
from src.config import get_settings
from src.web.routes import router as web_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Static files and templates
static_path = Path(__file__).parent / "web" / "static"
templates_path = Path(__file__).parent / "web" / "templates"

if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

templates = Jinja2Templates(directory=templates_path)

# Register routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(web_router, tags=["web"])
