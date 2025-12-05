"""
Root route.

Endpoints:
    GET / - API info and service discovery
"""

from fastapi import APIRouter

router = APIRouter(tags=["Root"])


# Public functions

@router.get("/")
async def root():
    """API information and service discovery links."""
    return {
        "name": "Greg API",
        "version": "2.0.0",
        "links": {
            "self": "/",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json",
        },
    }
