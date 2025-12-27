"""Document management exceptions."""


class DocumentError(Exception):
    """Base exception for document operations."""

    pass


class DocumentNotFoundError(DocumentError):
    """Raised when a document is not found."""

    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"Document not found: {identifier}")


class DocumentAlreadyExistsError(DocumentError):
    """Raised when a document with the same filename already exists."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(f"Document already exists: {filename}")


class DocumentValidationError(DocumentError):
    """Raised when document validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DocumentIndexingError(DocumentError):
    """Raised when document indexing fails."""

    def __init__(self, filename: str, reason: str) -> None:
        self.filename = filename
        self.reason = reason
        super().__init__(f"Failed to index document '{filename}': {reason}")
