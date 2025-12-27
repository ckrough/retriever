"""Document domain models."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass
class Document:
    """Document domain model representing an uploaded document."""

    id: UUID
    filename: str
    title: str
    description: str | None
    file_path: Path
    file_type: str  # 'markdown' or 'text'
    file_size_bytes: int
    uploaded_by: UUID | None
    is_indexed: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Document":
        """Create a Document from a database row.

        Args:
            row: Dictionary containing database row data.

        Returns:
            Document instance.
        """
        return cls(
            id=UUID(str(row["id"])),
            filename=str(row["filename"]),
            title=str(row["title"]),
            description=str(row["description"]) if row["description"] else None,
            file_path=Path(str(row["file_path"])),
            file_type=str(row["file_type"]),
            file_size_bytes=int(row["file_size_bytes"]),
            uploaded_by=UUID(str(row["uploaded_by"])) if row["uploaded_by"] else None,
            is_indexed=bool(row["is_indexed"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )
