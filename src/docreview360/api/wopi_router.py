# SPDX-License-Identifier: MIT
"""WOPI host API endpoints for Microsoft 365 co-authoring (Item 41).

Protocol reference:
  https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/

WOPI uses a *query-parameter* access token rather than an ``Authorization``
header, so these endpoints validate ``access_token`` themselves and do NOT use
``Depends(auth.get_current_user)``.

Registered under the ``/wopi`` prefix in ``api/__init__.py``.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from jose import JWTError, jwt

from ..documents import get_document
from ..wopi import (
    WOPICheckFileInfo,
    get_wopi_file_info,
    get_wopi_lock,
    put_file_contents,
    refresh_wopi_lock,
    release_wopi_lock,
    set_wopi_lock,
)

_logger = logging.getLogger(__name__)
router = APIRouter(tags=["wopi"])

# ---------------------------------------------------------------------------
# WOPI override header constants
# ---------------------------------------------------------------------------

_OVERRIDE_LOCK = "LOCK"
_OVERRIDE_UNLOCK = "UNLOCK"
_OVERRIDE_REFRESH_LOCK = "REFRESH_LOCK"
_OVERRIDE_GET_LOCK = "GET_LOCK"

# ---------------------------------------------------------------------------
# Supported file types for WOPI discovery
# ---------------------------------------------------------------------------

_WOPI_OFFICE_EXTS = [
    {"ext": "docx", "actions": ["view", "edit", "editnew"]},
    {"ext": "xlsx", "actions": ["view", "edit", "editnew"]},
    {"ext": "pptx", "actions": ["view", "edit", "editnew"]},
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_access_token(access_token: str) -> str:
    """Validate a WOPI access token (JWT) and return the username.

    Raises ``HTTP 401`` on any validation failure.
    """
    from .. import auth as _auth_mod

    try:
        payload = jwt.decode(
            access_token,
            _auth_mod.SECRET_KEY,
            algorithms=[_auth_mod.ALGORITHM],
            audience=_auth_mod.TOKEN_AUDIENCE,
            issuer=_auth_mod.TOKEN_ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WOPI access token",
        ) from exc

    username: str | None = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid WOPI access token",
        )
    return username


# ---------------------------------------------------------------------------
# CheckFileInfo — GET /wopi/files/{file_id}
# ---------------------------------------------------------------------------


@router.get("/wopi/files/{file_id}", response_class=JSONResponse)
def wopi_check_file_info(
    file_id: str,
    access_token: str = Query(..., description="WOPI JWT access token"),
) -> dict:
    """Return WOPI CheckFileInfo metadata for the requested document."""
    user = _validate_access_token(access_token)
    info: WOPICheckFileInfo = get_wopi_file_info(file_id, user)
    return dataclasses.asdict(info)


# ---------------------------------------------------------------------------
# GetFile — GET /wopi/files/{file_id}/contents
# ---------------------------------------------------------------------------


@router.get("/wopi/files/{file_id}/contents")
def wopi_get_file(
    file_id: str,
    access_token: str = Query(..., description="WOPI JWT access token"),
) -> Response:
    """Return the raw bytes of the document content (WOPI GetFile)."""
    _validate_access_token(access_token)
    doc = get_document(file_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    content_bytes = doc.content.encode("utf-8")
    return Response(
        content=content_bytes,
        media_type="application/octet-stream",
        headers={
            "X-WOPI-ItemVersion": str(doc.version_number),
        },
    )


# ---------------------------------------------------------------------------
# PutFile — POST /wopi/files/{file_id}/contents
# ---------------------------------------------------------------------------


@router.post("/wopi/files/{file_id}/contents", status_code=200)
async def wopi_put_file(
    file_id: str,
    request: Request,
    access_token: str = Query(..., description="WOPI JWT access token"),
    x_wopi_lock: Optional[str] = Header(None, alias="X-WOPI-Lock"),
) -> dict:
    """Save new file content for the document (WOPI PutFile).

    The request body is the raw bytes of the new file version.  The caller
    must hold the current lock (``X-WOPI-Lock`` header) unless no lock exists
    (zero-length file case).
    """
    user = _validate_access_token(access_token)
    doc = get_document(file_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Enforce lock check when a lock exists
    existing_lock = get_wopi_lock(file_id)
    if existing_lock is not None:
        if x_wopi_lock is None or x_wopi_lock != existing_lock.lock_token:
            current_token = existing_lock.lock_token if existing_lock else ""
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=current_token,
                headers={"X-WOPI-Lock": current_token},
            )

    body = await request.body()
    put_file_contents(file_id, body, user)
    doc_after = get_document(file_id)
    version = str(doc_after.version_number) if doc_after else "1"
    return JSONResponse(
        content={},
        status_code=200,
        headers={"X-WOPI-ItemVersion": version},
    )


# ---------------------------------------------------------------------------
# Lock/Unlock/RefreshLock/GetLock — POST /wopi/files/{file_id}
# ---------------------------------------------------------------------------


@router.post("/wopi/files/{file_id}", status_code=200)
def wopi_file_operation(
    file_id: str,
    access_token: str = Query(..., description="WOPI JWT access token"),
    x_wopi_override: str = Header(..., alias="X-WOPI-Override"),
    x_wopi_lock: Optional[str] = Header(None, alias="X-WOPI-Lock"),
    x_wopi_old_lock: Optional[str] = Header(None, alias="X-WOPI-OldLock"),
) -> Response:
    """Dispatch WOPI Lock / Unlock / RefreshLock / GetLock operations.

    The ``X-WOPI-Override`` header selects the operation:

    * ``LOCK``         — acquire or refresh a lock
    * ``UNLOCK``       — release the lock
    * ``REFRESH_LOCK`` — extend an existing lock's TTL
    * ``GET_LOCK``     — return the current lock token (no-op otherwise)
    """
    user = _validate_access_token(access_token)
    override = x_wopi_override.upper().strip()

    if override == _OVERRIDE_GET_LOCK:
        lock = get_wopi_lock(file_id)
        token = lock.lock_token if lock else ""
        return Response(
            status_code=200,
            headers={"X-WOPI-Lock": token},
        )

    if override == _OVERRIDE_LOCK:
        if x_wopi_lock is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-WOPI-Lock header required for LOCK",
            )
        set_wopi_lock(file_id, x_wopi_lock, user)
        return Response(status_code=200, headers={"X-WOPI-Lock": x_wopi_lock})

    if override == _OVERRIDE_UNLOCK:
        if x_wopi_lock is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-WOPI-Lock header required for UNLOCK",
            )
        release_wopi_lock(file_id, x_wopi_lock)
        return Response(status_code=200)

    if override == _OVERRIDE_REFRESH_LOCK:
        if x_wopi_lock is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-WOPI-Lock header required for REFRESH_LOCK",
            )
        refresh_wopi_lock(file_id, x_wopi_lock)
        return Response(status_code=200, headers={"X-WOPI-Lock": x_wopi_lock})

    # Unknown override operation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Unknown X-WOPI-Override: {x_wopi_override}",
    )


# ---------------------------------------------------------------------------
# WOPI discovery — GET /wopi/discovery
# ---------------------------------------------------------------------------

_WOPI_DISCOVERY_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<wopi-discovery>
  <net-zone name="external-https">
{app_entries}
  </net-zone>
</wopi-discovery>
"""

_ACTION_TEMPLATE = (
    '      <action name="{action}" ext="{ext}"'
    ' urlsrc="{base_url}/wopi/files/&#x3C;id&#x3E;?access_token=&#x3C;token&#x3E;"/>'
)


@router.get("/wopi/discovery", response_class=PlainTextResponse)
def wopi_discovery(request: Request) -> PlainTextResponse:
    """Return WOPI discovery XML consumed by Office Online Server.

    Lists the supported file types (docx, xlsx, pptx) and the action URLs
    that Office Online should call for ``view``, ``edit``, and ``editnew``
    operations.
    """
    base_url = str(request.base_url).rstrip("/")
    action_lines: list[str] = []
    for entry in _WOPI_OFFICE_EXTS:
        ext: str = entry["ext"]  # type: ignore[assignment]
        for action in entry["actions"]:  # type: ignore[union-attr]
            action_lines.append(_ACTION_TEMPLATE.format(action=action, ext=ext, base_url=base_url))
    app_entries = "\n".join(action_lines)
    xml = _WOPI_DISCOVERY_TEMPLATE.format(app_entries=app_entries)
    return PlainTextResponse(content=xml, media_type="application/xml")
