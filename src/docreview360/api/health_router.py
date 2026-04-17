# SPDX-License-Identifier: MIT
"""Health and readiness endpoints extracted from api.__init__."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Response
from sqlalchemy import text

from ..logs import _get_db
from .public_router import get_branding_config_status

_logger = logging.getLogger(__name__)

router = APIRouter()


def _db_health() -> tuple[str, int]:
    db_status = "ok"
    http_status = 200
    try:
        db = _get_db()
        with db.session() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        _logger.warning("Health check DB connectivity failed: %s", exc)
        db_status = "unavailable"
        http_status = 503
    return db_status, http_status


@router.get("/health")
async def health_check() -> Response:
    """Health check endpoint for monitoring."""

    db_status, http_status = _db_health()
    payload = json.dumps(
        {"status": "healthy" if http_status == 200 else "degraded", "db": db_status}
    )
    return Response(content=payload, status_code=http_status, media_type="application/json")


@router.get("/health/live")
async def health_live() -> Response:
    """Liveness probe -- returns 200 when the process is running."""

    return Response(
        content=json.dumps({"status": "live"}),
        status_code=200,
        media_type="application/json",
    )


@router.get("/health/ready")
async def health_ready() -> Response:
    """Readiness probe -- returns 200 only when the app can serve traffic."""

    db_status, http_status = _db_health()
    payload = json.dumps(
        {"status": "ready" if http_status == 200 else "not_ready", "db": db_status}
    )
    return Response(content=payload, status_code=http_status, media_type="application/json")


@router.get("/health/config")
async def health_config() -> Response:
    """Expose configuration health details that monitoring can alert on."""

    branding = get_branding_config_status()
    http_status = 200 if branding["loaded"] else 503
    payload = json.dumps(
        {
            "status": "healthy" if http_status == 200 else "degraded",
            "branding": branding,
        }
    )
    return Response(content=payload, status_code=http_status, media_type="application/json")
