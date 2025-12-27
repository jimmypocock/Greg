"""
Pydantic schemas for document management.

Defines request/response schemas for document endpoints.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from api.database.models import Document


# Schemas


class DocumentDetailResponse(BaseModel):
    """Detailed document response."""

    id: str
    name: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int | None
    total_tokens: int | None
    error_message: str | None
    created_at: str | None
    updated_at: str | None
    extra_metadata: dict | None = None

    @classmethod
    def from_model(cls, doc: "Document") -> "DocumentDetailResponse":
        """Create response from Document model."""
        return cls(
            id=str(doc.id),
            name=doc.name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status.value,
            chunk_count=doc.chunk_count,
            total_tokens=doc.total_tokens,
            error_message=doc.error_message,
            created_at=doc.created_at.isoformat() if doc.created_at else None,
            updated_at=doc.updated_at.isoformat() if doc.updated_at else None,
            extra_metadata=doc.extra_metadata,
        )


class DocumentListResponse(BaseModel):
    """List of documents response."""

    documents: list["DocumentResponse"]


class DocumentResponse(BaseModel):
    """Document info response."""

    id: str
    name: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int | None
    error_message: str | None
    created_at: str | None
    extra_metadata: dict | None = None

    @classmethod
    def from_model(cls, doc: "Document") -> "DocumentResponse":
        """Create response from Document model."""
        return cls(
            id=str(doc.id),
            name=doc.name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status.value,
            chunk_count=doc.chunk_count,
            error_message=doc.error_message,
            created_at=doc.created_at.isoformat() if doc.created_at else None,
            extra_metadata=doc.extra_metadata,
        )


class JobCreatedResponse(BaseModel):
    """Response when a background job is created."""

    job_id: str
    message: str
    status: str = "pending"
    websocket_url: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class URLProcessRequest(BaseModel):
    """Request body for processing a URL."""

    model_config = {"protected_namespaces": ()}

    chunk_size: int = 800
    model: str = "mistral"
    temperature: float = 0.7
    url: str
