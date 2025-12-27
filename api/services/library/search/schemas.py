"""
Pydantic schemas for web search.

Defines request/response schemas for search endpoints.
"""

from pydantic import BaseModel, field_validator

from api.services.library.search.exceptions import EmptyQueryError, InvalidModelError
from api.security.sanitization import sanitize_query_string, validate_model_name


class WebSearchRequest(BaseModel):
    """Request body for web search."""

    model_config = {"protected_namespaces": ()}

    question: str
    max_results: int = 3
    model_name: str | None = None
    temperature: float = 0.7

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate and sanitize question."""
        v = sanitize_query_string(v)
        if not v:
            raise EmptyQueryError()
        return v

    @field_validator("model_name")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        """Validate model name if provided."""
        if v is not None and not validate_model_name(v):
            raise InvalidModelError(v)
        return v
