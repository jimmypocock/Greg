"""
Core API module.

Provides the core FastAPI application factory that apps can extend.
"""

from packages.core.api.app import create_core_app

__all__ = ["create_core_app"]
