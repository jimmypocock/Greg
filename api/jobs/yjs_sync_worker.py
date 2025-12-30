"""
Background worker for syncing Yjs documents to SQL.

Periodically syncs active Yjs documents back to SQL tables
for AI context, REST API reads, and data persistence.
"""

import asyncio
import logging
from typing import Optional

from api.database import get_session
from api.services.yjs_provider import yjs_provider
from api.services.yjs_sync import YjsSyncService

logger = logging.getLogger(__name__)


class YjsSyncWorker:
    """
    Background worker that periodically syncs Yjs documents to SQL.

    This ensures SQL tables stay up-to-date for:
    - AI context (needs latest song content)
    - REST API reads (non-websocket clients)
    - Data integrity (backup persistence)
    """

    DEFAULT_INTERVAL_SECONDS = 5.0

    def __init__(self, interval_seconds: float = DEFAULT_INTERVAL_SECONDS):
        self._interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the background sync worker."""
        if self._running:
            logger.warning("YjsSyncWorker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"YjsSyncWorker started (interval={self._interval}s)")

    async def stop(self) -> None:
        """Stop the background sync worker."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("YjsSyncWorker stopped")

    async def _run_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                await self._sync_all_active_documents()
            except Exception as e:
                logger.error(f"YjsSyncWorker error: {e}")

            await asyncio.sleep(self._interval)

    async def _sync_all_active_documents(self) -> None:
        """Sync all active Yjs documents to SQL."""
        active_songs = yjs_provider.get_active_song_ids()

        if not active_songs:
            return

        logger.debug(f"Syncing {len(active_songs)} active Yjs documents to SQL")

        async with get_session() as session:
            sync_service = YjsSyncService(session)

            for song_id in active_songs:
                try:
                    await sync_service.sync_yjs_to_sql(song_id)
                except Exception as e:
                    logger.error(f"Failed to sync song {song_id}: {e}")

    async def sync_single(self, song_id) -> None:
        """
        Manually trigger sync for a single song.

        Useful for immediate sync after important operations.
        """
        async with get_session() as session:
            sync_service = YjsSyncService(session)
            await sync_service.sync_yjs_to_sql(song_id)
            logger.debug(f"Manual sync completed for song {song_id}")


# Global worker instance
yjs_sync_worker = YjsSyncWorker()
