"""Document loading and validation for the RAG pipeline.

Parses text and markdown documents into structured representations.
The old loader read from the filesystem; this version accepts content
as strings so the upload handler can read the file.
"""

from __future__ import annotations

import re

import structlog

from retriever.modules.rag.schemas import DocumentParser, ParsedDocument

logger = structlog.get_logger()

# Regex to match markdown H1 heading: # Title (at start of line)
_MARKDOWN_H1_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# Supported file extensions
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".md", ".txt"})

# Maximum file size: 1 MB
MAX_FILE_SIZE: int = 1_048_576


class FileValidationError(Exception):
    """Raised when a file fails upload validation."""


class TextDocumentParser:
    """Parser for plain-text and markdown documents.

    Implements the DocumentParser protocol. Extracts title from the first
    ``#`` heading for markdown files or uses the source as the title.
    """

    def parse(self, content: str, source: str) -> ParsedDocument:
        """Parse raw document content into a structured representation.

        Args:
            content: Raw document text.
            source: Source filename or identifier.

        Returns:
            Parsed document with extracted metadata.
        """
        is_markdown = source.lower().endswith(".md")
        document_type = "markdown" if is_markdown else "text"
        title = _extract_title(content, source, is_markdown=is_markdown)

        logger.debug(
            "document_parsed",
            source=source,
            title=title,
            document_type=document_type,
            content_length=len(content),
        )

        return ParsedDocument(
            content=content,
            source=source,
            title=title,
            document_type=document_type,
        )


# Verify TextDocumentParser satisfies the DocumentParser protocol
_parser_check: DocumentParser = TextDocumentParser()


def _extract_title(content: str, source: str, *, is_markdown: bool) -> str:
    """Extract document title from content or source name.

    For markdown files, looks for the first H1 heading (# Title).
    Falls back to the source filename without extension.

    Args:
        content: Document content.
        source: Source filename (used as fallback).
        is_markdown: Whether the file is markdown format.

    Returns:
        Extracted or derived title.
    """
    if is_markdown:
        match = _MARKDOWN_H1_PATTERN.search(content)
        if match:
            return match.group(1).strip()

    # Fallback: strip the extension from the source filename
    dot_pos = source.rfind(".")
    if dot_pos > 0:
        return source[:dot_pos]
    return source


def validate_file(filename: str, content_length: int) -> None:
    """Validate a file for upload.

    Checks filename extension, size, and hidden-file rules.

    Args:
        filename: The name of the file to validate.
        content_length: Size of the file content in bytes.

    Raises:
        FileValidationError: If validation fails.
    """
    # No hidden files (starting with .)
    if filename.startswith("."):
        raise FileValidationError(f"Hidden files are not allowed: {filename}")

    # Check extension
    dot_pos = filename.rfind(".")
    if dot_pos < 0:
        raise FileValidationError(
            f"File has no extension: {filename}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    extension = filename[dot_pos:].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file format: {extension}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Check size
    if content_length > MAX_FILE_SIZE:
        raise FileValidationError(
            f"File too large: {content_length} bytes (max {MAX_FILE_SIZE} bytes)"
        )

    if content_length == 0:
        raise FileValidationError("File is empty")
