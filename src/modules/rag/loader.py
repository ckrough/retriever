"""Document loaders for different file formats."""

from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class LoadedDocument:
    """A loaded document with its content and metadata."""

    content: str
    source: str  # Filename
    file_path: Path


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

        logger.debug(
            "document_loaded",
            file_path=str(file_path),
            source=file_path.name,
            content_length=len(content),
        )

        return LoadedDocument(
            content=content,
            source=file_path.name,
            file_path=file_path,
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
