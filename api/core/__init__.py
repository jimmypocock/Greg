"""
Core API module.

Provides the core FastAPI application factory that apps can extend.
"""

from api.core.app import create_core_app

__all__ = ["create_core_app"]
