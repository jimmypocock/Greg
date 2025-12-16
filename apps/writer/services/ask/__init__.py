"""
Document Q&A module.

Provides schemas, exceptions, and handlers for ask endpoints.
"""

from apps.writer.services.ask.exceptions import (
    AskError,
    EmptyQuestionError,
    InvalidDocumentIdError,
    QueryError,
)
from apps.writer.services.ask.handlers import register_ask_exception_handlers
from apps.writer.services.ask.schemas import QuestionRequest

__all__ = [
    # Exceptions
    "AskError",
    "EmptyQuestionError",
    "InvalidDocumentIdError",
    "QueryError",
    # Handlers
    "register_ask_exception_handlers",
    # Schemas
    "QuestionRequest",
]
