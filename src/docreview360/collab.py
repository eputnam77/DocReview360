from __future__ import annotations

from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from y_py import YDoc, encode_state_as_update

from .documents import documents, update_document

router = APIRouter()

# Track connected clients per document
_clients: Dict[str, Set[WebSocket]] = {}


@router.websocket("/collab/{doc_id}")
async def collab_endpoint(websocket: WebSocket, doc_id: str) -> None:
    """Minimal Yjs-compatible websocket relay."""

    await websocket.accept()
    group = _clients.setdefault(doc_id, set())
    group.add(websocket)

    # Send initial empty state so clients can sync
    await websocket.send_bytes(encode_state_as_update(YDoc()))

    try:
        while True:
            update = await websocket.receive_bytes()
            # Broadcast to other connected clients
            for client in list(group):
                if client is not websocket:
                    await client.send_bytes(update)
            # Persist raw update for reconciliation
            update_document(doc_id, documents[doc_id].content, yjs_updates=[update])
    except WebSocketDisconnect:
        group.discard(websocket)
        if not group:
            _clients.pop(doc_id, None)
