"""Jinja2 templates configuration."""

from pathlib import Path

import bleach
import markdown as md
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

_templates_path = Path(__file__).parent / "templates"
templates: Jinja2Templates = Jinja2Templates(directory=_templates_path)

# Allowed HTML tags for markdown output (safe subset)
ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "code",
    "pre",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "a",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "hr",
    "div",
    "span",
]

# Allowed attributes for HTML tags
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "code": ["class"],  # For syntax highlighting
    "pre": ["class"],  # For code blocks
    "div": ["class"],  # For code blocks
    "span": ["class"],  # For inline formatting
}


def markdown_filter(text: str) -> Markup:
    """Convert markdown text to HTML with sanitization.

    Uses Python-Markdown with extensions for:
    - Fenced code blocks with syntax highlighting
    - Tables
    - Code blocks with language specification
    - Newline-to-br conversion for better formatting

    Security: HTML output is sanitized with bleach to allow only safe tags
    and attributes, preventing XSS attacks from any malicious content.

    Args:
        text: The markdown text to convert.

    Returns:
        Sanitized HTML markup safe for rendering in Jinja2 templates.
    """
    # Convert markdown to HTML
    html = md.markdown(
        text,
        extensions=[
            "fenced_code",  # Support ```language blocks
            "tables",  # Support markdown tables
            "nl2br",  # Convert newlines to <br> tags
            "codehilite",  # Syntax highlighting for code blocks
        ],
        output_format="html",
        extension_configs={
            "codehilite": {
                "css_class": "highlight",
                "use_pygments": False,  # Use CSS classes instead
            }
        },
    )

    # Sanitize HTML to prevent XSS attacks
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,  # Strip disallowed tags instead of escaping them
    )

    return Markup(clean_html)  # nosec B704 - sanitized by bleach.clean()


# Register the markdown filter
templates.env.filters["markdown"] = markdown_filter
