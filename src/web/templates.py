"""Jinja2 templates configuration."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

_templates_path = Path(__file__).parent / "templates"
templates: Jinja2Templates = Jinja2Templates(directory=_templates_path)
