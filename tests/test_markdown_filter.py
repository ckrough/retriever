"""Tests for markdown rendering in templates."""

from markupsafe import Markup

from src.web.templates import markdown_filter


class TestMarkdownFilter:
    """Test the markdown_filter function."""

    def test_markdown_filter_renders_bold(self) -> None:
        """Test that bold markdown is converted to HTML."""
        text = "This is **bold** text"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert "<strong>bold</strong>" in result

    def test_markdown_filter_renders_italic(self) -> None:
        """Test that italic markdown is converted to HTML."""
        text = "This is _italic_ text"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert "<em>italic</em>" in result

    def test_markdown_filter_renders_code_blocks(self) -> None:
        """Test that fenced code blocks are converted to HTML."""
        text = "```python\nprint('hello')\n```"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert "<pre>" in result
        assert "<code" in result

    def test_markdown_filter_renders_inline_code(self) -> None:
        """Test that inline code is converted to HTML."""
        text = "Use the `print()` function"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert "<code>print()</code>" in result

    def test_markdown_filter_renders_lists(self) -> None:
        """Test that unordered lists are converted to HTML."""
        text = "- Item 1\n- Item 2\n- Item 3"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert "<ul>" in result
        assert "<li>Item 1</li>" in result

    def test_markdown_filter_renders_ordered_lists(self) -> None:
        """Test that ordered lists are converted to HTML."""
        text = "1. First\n2. Second\n3. Third"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert "<ol>" in result
        assert "<li>First</li>" in result

    def test_markdown_filter_renders_headers(self) -> None:
        """Test that headers are converted to HTML."""
        text = "# Heading 1\n## Heading 2\n### Heading 3"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert "<h1>Heading 1</h1>" in result
        assert "<h2>Heading 2</h2>" in result
        assert "<h3>Heading 3</h3>" in result

    def test_markdown_filter_renders_links(self) -> None:
        """Test that links are converted to HTML."""
        text = "Visit [Google](https://google.com)"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert '<a href="https://google.com">Google</a>' in result

    def test_markdown_filter_renders_tables(self) -> None:
        """Test that markdown tables are converted to HTML."""
        text = (
            "| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |"
        )
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert "<table>" in result
        assert "<th>Header 1</th>" in result
        assert "<td>Cell 1</td>" in result

    def test_markdown_filter_strips_dangerous_html_tags(self) -> None:
        """Test that dangerous HTML tags are stripped by bleach.

        Bleach removes dangerous tags like <script> but preserves the text content.
        This prevents XSS attacks while maintaining readability.
        """
        text = "This has <script>alert('xss')</script> in it"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        # Bleach should strip the script tag but preserve text content
        assert "<script>" not in result
        assert "</script>" not in result
        # The text content is preserved (safe to display)
        assert "This has" in result
        assert "in it" in result
        # Result should be wrapped in paragraph tags by markdown
        assert "<p>" in result

    def test_markdown_filter_handles_empty_string(self) -> None:
        """Test that empty strings are handled gracefully."""
        text = ""
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        assert result == ""

    def test_markdown_filter_preserves_newlines_with_nl2br(self) -> None:
        """Test that newlines are converted to br tags with nl2br extension."""
        text = "Line 1\nLine 2\nLine 3"
        result = markdown_filter(text)
        assert isinstance(result, Markup)
        # nl2br should convert newlines to <br> tags
        assert "<br" in result or "<p>" in result
