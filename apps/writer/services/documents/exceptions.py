"""
Document exceptions.

Domain-specific exceptions for document operations.
"""


class DocumentError(Exception):
    """Base exception for document errors."""

    def __init__(self, message: str = "Document error"):
        self.message = message
        super().__init__(self.message)


class DocumentNotFoundError(DocumentError):
    """Raised when document is not found."""

    def __init__(self, document_id: str | None = None):
        msg = f"Document {document_id} not found" if document_id else "Document not found"
        super().__init__(msg)


class InvalidFilenameError(DocumentError):
    """Raised when filename is invalid."""

    def __init__(self):
        super().__init__("Invalid filename")


class UnsupportedFileTypeError(DocumentError):
    """Raised when file type is not supported."""

    def __init__(self, file_type: str, allowed: list[str] | None = None):
        msg = f"Unsupported file type: {file_type}"
        if allowed:
            msg += f". Allowed: {', '.join(allowed)}"
        super().__init__(msg)


class InvalidURLError(DocumentError):
    """Raised when URL is invalid."""

    def __init__(self):
        super().__init__("Invalid URL. Please provide a valid HTTP or HTTPS URL.")


class FileOperationError(DocumentError):
    """Raised when file operation fails."""

    def __init__(self, message: str = "File operation failed"):
        super().__init__(message)
