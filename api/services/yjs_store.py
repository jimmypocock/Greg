"""Store for managing Yjs document state persistence."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models import YjsDocument

logger = logging.getLogger(__name__)


class YjsDocumentStore:
    """Store for Yjs document state persistence."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, document_id: UUID) -> Optional[YjsDocument]:
        """Get a Yjs document by ID."""
        result = await self.session.execute(
            select(YjsDocument).where(YjsDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_song(
        self, song_id: UUID, document_name: str = "main"
    ) -> Optional[YjsDocument]:
        """Get a Yjs document for a song."""
        result = await self.session.execute(
            select(YjsDocument)
            .where(YjsDocument.song_id == song_id)
            .where(YjsDocument.document_name == document_name)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self, song_id: UUID, document_name: str = "main"
    ) -> YjsDocument:
        """Get or create a Yjs document for a song."""
        doc = await self.get_by_song(song_id, document_name)
        if doc is None:
            doc = YjsDocument(
                song_id=song_id,
                document_name=document_name,
            )
            self.session.add(doc)
            await self.session.commit()
            await self.session.refresh(doc)
            logger.info(f"Created Yjs document for song {song_id}: {document_name}")
        return doc

    async def save_state(
        self,
        song_id: UUID,
        state_vector: bytes,
        document_state: bytes,
        user_id: Optional[UUID] = None,
        document_name: str = "main",
    ) -> YjsDocument:
        """Save Yjs document state."""
        doc = await self.get_or_create(song_id, document_name)

        doc.state_vector = state_vector
        doc.document_state = document_state
        doc.last_updated_by = user_id

        await self.session.commit()
        await self.session.refresh(doc)

        logger.debug(
            f"Saved Yjs state for song {song_id}: "
            f"{len(document_state)} bytes"
        )
        return doc

    async def get_state(
        self, song_id: UUID, document_name: str = "main"
    ) -> tuple[Optional[bytes], Optional[bytes]]:
        """Get Yjs document state.

        Returns:
            Tuple of (state_vector, document_state) or (None, None) if not found.
        """
        doc = await self.get_by_song(song_id, document_name)
        if doc is None:
            return None, None
        return doc.state_vector, doc.document_state

    async def delete(self, song_id: UUID, document_name: str = "main") -> bool:
        """Delete a Yjs document."""
        doc = await self.get_by_song(song_id, document_name)
        if doc is None:
            return False

        await self.session.delete(doc)
        await self.session.commit()
        logger.info(f"Deleted Yjs document for song {song_id}: {document_name}")
        return True
