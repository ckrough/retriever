"""Document Pydantic schemas for API validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    """Request schema for document upload.

    Note: The file itself is handled via FastAPI's UploadFile,
    not through this schema.
    """

    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional description of the document",
    )


class DocumentResponse(BaseModel):
    """Response schema for a single document."""

    id: UUID
    filename: str
    title: str
    description: str | None
    file_type: str
    file_size_bytes: int
    uploaded_by: UUID | None
    is_indexed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response schema for document list."""

    documents: list[DocumentResponse]
    total_count: int
