"""Web routes for server-rendered pages."""

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_path)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main chat page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@router.post("/ask", response_class=HTMLResponse)
async def ask(request: Request, question: str = Form(...)) -> HTMLResponse:
    """Handle a question submission and return the answer fragment."""
    # Hardcoded response for walking skeleton
    answer = "Hello! I'm GoodPuppy, the volunteer assistant. I'll be able to answer questions about shelter policies and procedures once I'm fully set up."

    return templates.TemplateResponse(
        request=request,
        name="partials/message_pair.html",
        context={"question": question, "answer": answer},
    )
