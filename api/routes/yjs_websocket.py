"""WebSocket route for Yjs real-time collaboration.

Provides WebSocket endpoint for real-time collaborative editing
using Yjs CRDT synchronization.

Endpoint:
    WS /ws/songs/{song_id}/yjs - Connect to Yjs document for a song
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.permissions import SongPermissionService, Permission
from api.services.yjs_provider import yjs_provider
from api.services.yjs_store import YjsDocumentStore
from api.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Yjs WebSocket"])


async def get_yjs_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> YjsDocumentStore:
    """Get a Yjs document store instance."""
    return YjsDocumentStore(session)


async def get_permission_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongPermissionService:
    """Get a permission service instance."""
    return SongPermissionService(session)


@router.websocket("/ws/songs/{song_id}/yjs")
async def yjs_websocket(
    websocket: WebSocket,
    song_id: UUID,
    token: str = Query(..., description="JWT access token"),
):
    """WebSocket endpoint for Yjs real-time collaboration.

    Authentication is done via query parameter `token` containing
    a valid JWT access token.

    Protocol:
    - Messages use Yjs binary sync protocol
    - First byte indicates message type:
      - 0: Sync message (followed by sync subtype)
      - 1: Awareness message (cursor positions, etc.)

    To connect from JavaScript/TypeScript:
    ```javascript
    import * as Y from 'yjs'
    import { WebsocketProvider } from 'y-websocket'

    const doc = new Y.Doc()
    const wsProvider = new WebsocketProvider(
      'ws://localhost:8080/ws/songs/{song_id}/yjs',
      'song-{song_id}',
      doc,
      { params: { token: 'your-jwt-token' } }
    )
    ```
    """
    # Get database session for this connection
    # Note: We need to handle session lifecycle carefully in WebSockets
    from api.database import async_session_factory

    async with async_session_factory() as session:
        # Validate token and get user
        try:
            user = await _validate_token_and_get_user(token, session)
            if user is None:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Check permission
        permission_service = SongPermissionService(session)
        try:
            await permission_service.require_permission(
                song_id, user.id, Permission.READ
            )
        except Exception as e:
            logger.warning(f"WebSocket permission denied: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Check if user can write (for awareness info)
        can_write = await permission_service.can_write(song_id, user.id)

        # Connect to Yjs provider
        store = YjsDocumentStore(session)
        client = await yjs_provider.connect(websocket, song_id, user.id, store)

        try:
            # Send initial document state
            await yjs_provider.send_initial_state(client)

            # Handle messages
            while True:
                message = await websocket.receive_bytes()
                await yjs_provider.handle_message(client, message, store)

        except WebSocketDisconnect:
            logger.debug(f"WebSocket disconnected: song={song_id}, user={user.id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await yjs_provider.disconnect(client, store)


async def _validate_token_and_get_user(token: str, session):
    """Validate JWT token and return user.

    This uses FastAPI-Users token validation.
    """
    from api.auth.users import get_jwt_strategy, get_user_manager
    from api.database.models import User

    try:
        # Get the JWT strategy
        jwt_strategy = get_jwt_strategy()

        # Decode and validate token
        user_manager = get_user_manager(session)
        user = await jwt_strategy.read_token(token, user_manager)

        if user is None or not user.is_active:
            return None

        return user
    except Exception as e:
        logger.debug(f"Token validation failed: {e}")
        return None
