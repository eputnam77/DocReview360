# SPDX-License-Identifier: MIT
"""Apple Push Notification service (APNs) — token-based auth integration.

APNs token-based auth requires:
  - DOCREVIEW360_APNS_TEAM_ID     : 10-character Apple Team ID
  - DOCREVIEW360_APNS_KEY_ID      : 10-character APNs auth key ID (from Apple)
  - DOCREVIEW360_APNS_PRIVATE_KEY : PEM-encoded EC private key (.p8 contents)
  - DOCREVIEW360_APNS_BUNDLE_ID   : iOS app bundle ID (e.g. com.example.docreview360)
  - DOCREVIEW360_APNS_SANDBOX     : set to "true" for development sandbox (default false)

When these variables are not set, ``send_apns_notification`` is a no-op and
returns an error dict.  No exceptions are raised so callers are never blocked
by missing APNs config.

Reference: https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/establishing_a_token-based_connection_to_apns
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

_logger = logging.getLogger(__name__)

# APNs endpoints
_APNS_HOST_PROD = "api.push.apple.com"
_APNS_HOST_SANDBOX = "api.sandbox.push.apple.com"
_APNS_PORT = 443

# Token expiry: Apple requires tokens be regenerated within 1 hour.
_TOKEN_TTL_SECONDS = 3_000  # 50 minutes — refresh before the 60-min limit

_cached_token: dict[str, Any] = {}  # {"token": str, "generated_at": float}


def _get_apns_config() -> dict[str, str] | None:
    """Return APNs config from env vars, or None if incomplete."""
    team_id = os.getenv("DOCREVIEW360_APNS_TEAM_ID", "").strip()
    key_id = os.getenv("DOCREVIEW360_APNS_KEY_ID", "").strip()
    private_key = os.getenv("DOCREVIEW360_APNS_PRIVATE_KEY", "").strip()
    bundle_id = os.getenv("DOCREVIEW360_APNS_BUNDLE_ID", "").strip()
    if not (team_id and key_id and private_key and bundle_id):
        return None
    return {
        "team_id": team_id,
        "key_id": key_id,
        "private_key": private_key,
        "bundle_id": bundle_id,
        "sandbox": os.getenv("DOCREVIEW360_APNS_SANDBOX", "false").strip().lower() == "true",
    }


def _generate_jwt(team_id: str, key_id: str, private_key_pem: str) -> str:
    """Generate an APNs provider JWT using PyJWT or fallback to jose."""
    now = int(time.time())
    payload = {"iss": team_id, "iat": now}
    headers = {"alg": "ES256", "kid": key_id}
    try:
        import jwt as _jwt  # PyJWT

        return _jwt.encode(payload, private_key_pem, algorithm="ES256", headers=headers)
    except ImportError:
        pass
    try:
        from jose import jwt as _jose_jwt

        return _jose_jwt.encode(payload, private_key_pem, algorithm="ES256", headers=headers)
    except ImportError:
        pass
    raise RuntimeError(
        "APNs token signing requires PyJWT (pip install PyJWT[crypto]) "
        "or python-jose[cryptography]."
    )


def _get_bearer_token(cfg: dict[str, str]) -> str:
    """Return a cached or freshly generated APNs bearer token."""
    global _cached_token  # noqa: PLW0603
    now = time.monotonic()
    generated_at = _cached_token.get("generated_at", 0.0)
    if _cached_token.get("token") and now - generated_at < _TOKEN_TTL_SECONDS:
        return _cached_token["token"]  # type: ignore[return-value]
    token = _generate_jwt(cfg["team_id"], cfg["key_id"], cfg["private_key"])
    _cached_token = {"token": token, "generated_at": now}
    return token


def send_apns_notification(
    device_token: str,
    title: str,
    body: str,
    badge: int | None = None,
    sound: str = "default",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a push notification to *device_token* via APNs.

    Returns a result dict with keys ``success`` (bool), ``status`` (HTTP
    status code or 0), and ``error`` (str or None).  Never raises.
    """
    cfg = _get_apns_config()
    if cfg is None:
        _logger.debug("APNs not configured — skipping push notification to %s", device_token)
        return {"success": False, "status": 0, "error": "APNs not configured"}

    host = _APNS_HOST_SANDBOX if cfg["sandbox"] else _APNS_HOST_PROD
    url = f"https://{host}:{_APNS_PORT}/3/device/{device_token}"

    aps: dict[str, Any] = {
        "alert": {"title": title, "body": body},
        "sound": sound,
    }
    if badge is not None:
        aps["badge"] = badge

    payload: dict[str, Any] = {"aps": aps}
    if extra:
        payload.update(extra)

    try:
        bearer = _get_bearer_token(cfg)
    except Exception as exc:
        _logger.error("Failed to generate APNs token: %s", exc)
        return {"success": False, "status": 0, "error": f"Token error: {exc}"}

    headers = {
        "authorization": f"bearer {bearer}",
        "apns-topic": cfg["bundle_id"],
        "apns-push-type": "alert",
        "content-type": "application/json",
    }

    try:
        import httpx

        with httpx.Client(http2=True, timeout=10.0) as client:
            resp = client.post(url, content=json.dumps(payload).encode(), headers=headers)
        if resp.status_code == 200:
            return {"success": True, "status": 200, "error": None}
        try:
            detail = resp.json().get("reason", resp.text)
        except Exception:
            detail = resp.text
        _logger.warning("APNs rejected notification for %s: %s %s", device_token, resp.status_code, detail)
        return {"success": False, "status": resp.status_code, "error": detail}
    except Exception as exc:
        _logger.error("APNs HTTP error for %s: %s", device_token, exc)
        return {"success": False, "status": 0, "error": str(exc)}


def clear_token_cache() -> None:
    """Clear the cached APNs bearer token (for testing)."""
    global _cached_token  # noqa: PLW0603
    _cached_token = {}
