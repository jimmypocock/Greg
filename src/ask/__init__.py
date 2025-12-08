"""
Document Q&A module.

Provides schemas, exceptions, and handlers for ask endpoints.
"""

from src.ask.exceptions import (
    AskError,
    EmptyQuestionError,
    InvalidDocumentIdError,
    QueryError,
)
from src.ask.handlers import register_ask_exception_handlers
from src.ask.schemas import QuestionRequest

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
