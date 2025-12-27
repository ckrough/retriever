"""Document management module.

Provides functionality for uploading, managing, and indexing documents
for the RAG pipeline.
"""

from src.modules.documents.exceptions import (
    DocumentAlreadyExistsError,
    DocumentError,
    DocumentIndexingError,
    DocumentNotFoundError,
    DocumentValidationError,
)
from src.modules.documents.models import Document
from src.modules.documents.repository import DocumentRepository
from src.modules.documents.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadRequest,
)
from src.modules.documents.service import DocumentService

__all__ = [
    "Document",
    "DocumentAlreadyExistsError",
    "DocumentError",
    "DocumentIndexingError",
    "DocumentListResponse",
    "DocumentNotFoundError",
    "DocumentRepository",
    "DocumentResponse",
    "DocumentService",
    "DocumentUploadRequest",
    "DocumentValidationError",
]
