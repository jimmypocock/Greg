"""
Pydantic schemas for document Q&A.

Defines request/response schemas for ask endpoints.
"""

import uuid

from pydantic import BaseModel, field_validator

from src.ask.exceptions import EmptyQuestionError, InvalidDocumentIdError


class QuestionRequest(BaseModel):
    """Request body for asking questions."""

    model_config = {"protected_namespaces": ()}

    question: str
    document_id: str
    max_results: int = 5
    model_name: str | None = None
    stream: bool = False
    temperature: float = 0.7
    use_web_search: bool = False

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate question is not empty."""
        v = v.strip()
        if not v:
            raise EmptyQuestionError()
        return v

    def get_document_uuid(self) -> uuid.UUID | None:
        """Parse document_id to UUID, or None if 'all'/'unified'."""
        if self.document_id in ("all", "unified"):
            return None

        try:
            return uuid.UUID(self.document_id)
        except ValueError:
            raise InvalidDocumentIdError(self.document_id)
