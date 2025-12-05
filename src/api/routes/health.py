"""
Health and system info routes.

Endpoints:
    GET /         - API info
    GET /health   - Health check
    GET /models   - List available models
"""

import logging
from fastapi import APIRouter, Depends

from src.api.schemas import ModelInfo
from src.api.dependencies import get_config
from src.config.settings import Config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def root():
    """Get API information and available endpoints."""
    return {
        "message": "Greg API - Your AI Playground",
        "version": "2.0.0",
        "status": "running",
        "supported_files": ["pdf", "txt", "csv", "md", "docx", "xlsx", "png", "jpg"],
        "endpoints": {
            # System
            "health": "GET /health - System health and memory stats",
            "models": "GET /models - List available LLM models",
            # Documents
            "upload": "POST /documents - Upload and process a document",
            "upload_url": "POST /documents/url - Process a URL as a document",
            "list": "GET /documents - List processed documents",
            "delete": "DELETE /documents/{id} - Delete a document",
            "clear": "DELETE /documents - Clear all documents",
            # Q&A
            "ask": "POST /ask - Ask a question about documents",
            "search": "POST /web-search - Search the web",
            # Storage
            "storage": "GET /storage - Vector store statistics",
            "cleanup": "POST /storage/cleanup - Trigger storage cleanup",
        },
        "docs": "/docs",
    }


@router.get("/health")
async def health_check(config: Config = Depends(get_config)):
    """Check system health and available memory."""
    try:
        import psutil

        memory = psutil.virtual_memory()

        return {
            "status": "healthy",
            "memory": {
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
                "total_gb": round(memory.total / (1024**3), 2),
            },
            "model": config.LOCAL_LLM_MODEL,
            "optimal_settings": config.get_optimal_settings(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("/models")
async def list_models(config: Config = Depends(get_config)):
    """
    List all available LLM models across providers.

    Returns models from:
    - Ollama (local models)
    - Future: OpenAI, Anthropic, Google (when configured)
    """
    models = []

    # Get Ollama models
    try:
        import ollama

        ollama_models = ollama.list()
        for model in ollama_models.get("models", []):
            # Format size nicely
            size_bytes = model.get("size", 0)
            if size_bytes > 1024**3:
                size_str = f"{size_bytes / (1024**3):.1f}GB"
            elif size_bytes > 1024**2:
                size_str = f"{size_bytes / (1024**2):.1f}MB"
            else:
                size_str = f"{size_bytes}B"

            models.append(
                ModelInfo(
                    name=model.get("name", "unknown"),
                    provider="ollama",
                    size=size_str,
                    modified=model.get("modified_at", None),
                    available=True,
                )
            )
    except Exception as e:
        logger.warning(f"Could not fetch Ollama models: {e}")

    # Future: Add OpenAI models when OPENAI_API_KEY is set
    # Future: Add Anthropic models when ANTHROPIC_API_KEY is set
    # Future: Add Google models when GOOGLE_API_KEY is set

    return {
        "models": [m.model_dump() for m in models],
        "default": config.LOCAL_LLM_MODEL,
        "providers": {
            "ollama": {"available": len([m for m in models if m.provider == "ollama"]) > 0},
            "openai": {"available": False, "reason": "Not configured"},
            "anthropic": {"available": False, "reason": "Not configured"},
            "google": {"available": False, "reason": "Not configured"},
        },
    }
