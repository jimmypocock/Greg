"""
Pydantic schemas for LLM endpoints.

Defines response schemas for models and provider information.
"""

from pydantic import BaseModel


# Schemas


class DefaultModelInfo(BaseModel):
    """Default model configuration."""

    model: str
    provider: str


class ModelInfo(BaseModel):
    """Model information."""

    name: str
    size: str | None = None


class ModelsListResponse(BaseModel):
    """Response for listing available models."""

    default: DefaultModelInfo
    providers: dict[str, "ProviderInfo"]


class ProviderInfo(BaseModel):
    """Provider availability and models."""

    available: bool
    models: list[ModelInfo] | None = None
    reason: str | None = None
    recommended: list["RecommendedModel"] | None = None


class RecommendedModel(BaseModel):
    """Recommended model info."""

    description: str
    name: str
