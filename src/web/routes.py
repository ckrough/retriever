"""Web routes for server-rendered pages."""

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, Response

from src.web.templates import templates

router = APIRouter()

# Input constraints
MAX_QUESTION_LENGTH = 2000


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    """Render the main chat page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@router.post("/ask", response_class=HTMLResponse)
async def ask(
    request: Request,
    question: Annotated[str, Form(min_length=1, max_length=MAX_QUESTION_LENGTH)],
) -> Response:
    """Handle a question submission and return the answer fragment."""
    # Hardcoded response for walking skeleton
    answer = "Hello! I'm GoodPuppy, the volunteer assistant. I'll be able to answer questions about shelter policies and procedures once I'm fully set up."

    return templates.TemplateResponse(
        request=request,
        name="partials/message_pair.html",
        context={"question": question, "answer": answer},
    )
