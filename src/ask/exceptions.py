"""
Ask module exceptions.

Domain-specific exceptions for Q&A operations.
"""


class AskError(Exception):
    """Base exception for ask errors."""

    def __init__(self, message: str = "Q&A error"):
        self.message = message
        super().__init__(self.message)


class EmptyQuestionError(AskError):
    """Raised when question is empty."""

    def __init__(self):
        super().__init__("Question cannot be empty")


class InvalidDocumentIdError(AskError):
    """Raised when document_id format is invalid."""

    def __init__(self, document_id: str):
        super().__init__(f"Invalid document_id format: {document_id}")


class QueryError(AskError):
    """Raised when query processing fails."""

    def __init__(self, message: str = "Failed to process query"):
        super().__init__(message)
