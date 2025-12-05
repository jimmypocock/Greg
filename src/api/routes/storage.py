"""
Storage management routes.

Endpoints:
    GET  /storage          - Get vector store statistics
    POST /storage/cleanup  - Manually trigger cleanup (admin only)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends

from src.api.dependencies import get_config, get_vector_store_manager
from src.auth import CurrentUser, AdminUser
from src.config.settings import Config
from src.database import User
from src.vectorstore.manager import VectorStoreManager
from src.security.sanitization import sanitize_error_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/storage")
async def get_storage_stats(
    user: CurrentUser,
    config: Config = Depends(get_config),
    vector_store_manager: VectorStoreManager = Depends(get_vector_store_manager),
):
    """Get storage statistics for vector stores."""
    try:
        stats = vector_store_manager.get_storage_stats()

        # Add storage path
        stats["storage_path"] = str(config.VECTOR_STORE_DIR.absolute())

        return stats

    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/storage/cleanup")
async def cleanup_vector_stores(
    admin: AdminUser,
    vector_store_manager: VectorStoreManager = Depends(get_vector_store_manager),
):
    """Manually trigger vector store cleanup."""
    try:
        # Force cleanup
        cleanup_stats = vector_store_manager.cleanup_old_stores(force=True)

        # Clean orphaned upload files too
        orphaned_cleaned = vector_store_manager.cleanup_orphaned_files()
        cleanup_stats["orphaned_files_cleaned"] = orphaned_cleaned

        return cleanup_stats

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)
