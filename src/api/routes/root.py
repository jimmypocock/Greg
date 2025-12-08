"""
Root route.

Provides API information and service discovery.

Endpoints:
    GET / - API info and service discovery
"""

from fastapi import APIRouter

from src.root import LinksResponse, RootResponse

router = APIRouter(tags=["Root"])


# Public functions


@router.get("/", response_model=RootResponse)
async def root():
    """API information and service discovery links."""
    return RootResponse(
        links=LinksResponse(
            docs="/docs",
            health="/health",
            openapi="/openapi.json",
            self="/",
        ),
        name="Greg API",
        version="2.0.0",
    )
