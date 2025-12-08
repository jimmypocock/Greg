"""
Pydantic schemas for root endpoint.

Defines response schemas for API info.
"""

from pydantic import BaseModel


# Schemas


class LinksResponse(BaseModel):
    """API discovery links."""

    docs: str
    health: str
    openapi: str
    self: str


class RootResponse(BaseModel):
    """Root API response."""

    links: LinksResponse
    name: str
    version: str
