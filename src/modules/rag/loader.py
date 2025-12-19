"""Document loaders for different file formats."""

import re
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()

# Regex to match markdown H1 heading: # Title (at start of line)
_MARKDOWN_H1_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass
class LoadedDocument:
    """A loaded document with its content and metadata."""

    content: str
    source: str  # Filename
    file_path: Path
    title: str  # Document title (first # heading or filename)
    document_type: str  # "markdown" or "text"


class DocumentLoadError(Exception):
    """Raised when a document cannot be loaded."""

    def __init__(self, message: str, file_path: Path) -> None:
        self.file_path = file_path
        super().__init__(message)


def load_document(file_path: Path) -> LoadedDocument:
    """Load a document from a file path.

    Supports markdown (.md) and text (.txt) files.

    Args:
        file_path: Path to the document file.

    Returns:
        LoadedDocument with content and metadata.

    Raises:
        DocumentLoadError: If the file cannot be loaded.
    """
    if not file_path.exists():
        raise DocumentLoadError(f"File not found: {file_path}", file_path)

    suffix = file_path.suffix.lower()

    if suffix in (".md", ".txt"):
        return _load_text_file(file_path)
    else:
        raise DocumentLoadError(
            f"Unsupported file format: {suffix}. Supported: .md, .txt",
            file_path,
        )


def _extract_title(content: str, file_path: Path, is_markdown: bool) -> str:
    """Extract document title from content or filename.

    For markdown files, looks for the first H1 heading (# Title).
    For text files, uses the filename without extension.

    Args:
        content: Document content.
        file_path: Path to the file (used as fallback).
        is_markdown: Whether the file is markdown format.

    Returns:
        Extracted or derived title.
    """
    if is_markdown:
        match = _MARKDOWN_H1_PATTERN.search(content)
        if match:
            return match.group(1).strip()

    # Fallback: use filename without extension
    return file_path.stem


def _load_text_file(file_path: Path) -> LoadedDocument:
    """Load a text or markdown file.

    Args:
        file_path: Path to the file.

    Returns:
        LoadedDocument with content.

    Raises:
        DocumentLoadError: If reading fails.
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        # Determine document type based on extension
        suffix = file_path.suffix.lower()
        is_markdown = suffix == ".md"
        document_type = "markdown" if is_markdown else "text"

        # Extract title
        title = _extract_title(content, file_path, is_markdown)

        logger.debug(
            "document_loaded",
            file_path=str(file_path),
            source=file_path.name,
            title=title,
            document_type=document_type,
            content_length=len(content),
        )

        return LoadedDocument(
            content=content,
            source=file_path.name,
            file_path=file_path,
            title=title,
            document_type=document_type,
        )

    except UnicodeDecodeError as e:
        raise DocumentLoadError(
            f"Failed to decode file as UTF-8: {e}",
            file_path,
        ) from e
    except OSError as e:
        raise DocumentLoadError(
            f"Failed to read file: {e}",
            file_path,
        ) from e


def list_documents(documents_path: Path) -> list[Path]:
    """List all supported documents in a directory.

    Args:
        documents_path: Directory to search.

    Returns:
        List of paths to supported documents.
    """
    if not documents_path.exists():
        return []

    supported_extensions = {".md", ".txt"}
    documents: list[Path] = []

    for ext in supported_extensions:
        documents.extend(documents_path.glob(f"*{ext}"))

    # Sort by name for consistent ordering
    return sorted(documents, key=lambda p: p.name.lower())
