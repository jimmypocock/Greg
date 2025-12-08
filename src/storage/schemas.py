"""
Pydantic schemas for storage endpoints.

Defines response schemas for vector store statistics.
"""

from pydantic import BaseModel


# Schemas


class StorageStatsResponse(BaseModel):
    """Vector store statistics response."""

    chunks_by_provider: dict[str, int]
    storage_type: str
    total_chunks: int
    total_documents: int
