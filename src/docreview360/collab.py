from __future__ import annotations

from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:  # pragma: no cover - exercised indirectly in fallback test
    from y_py import YDoc, encode_state_as_update
except ImportError:  # pragma: no cover - behaviour validated via fallback test
    YDoc = None  # type: ignore[assignment]
    encode_state_as_update = None  # type: ignore[assignment]
    YPY_AVAILABLE = False
else:
    YPY_AVAILABLE = True

from .documents import documents, update_document

router = APIRouter()

# Track connected clients per document
_clients: Dict[str, Set[WebSocket]] = {}

MISSING_DEPENDENCY_MESSAGE = (
    "Collaborative editing requires the optional 'y_py' package on the server."
)


@router.websocket("/collab/{doc_id}")
async def collab_endpoint(websocket: WebSocket, doc_id: str) -> None:
    """Minimal Yjs-compatible websocket relay."""

    if not YPY_AVAILABLE:
        await websocket.close(code=1013, reason=MISSING_DEPENDENCY_MESSAGE)
        return

    await websocket.accept()
    group = _clients.setdefault(doc_id, set())
    group.add(websocket)

    # Send initial empty state so clients can sync
    assert encode_state_as_update is not None  # for type-checkers
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
