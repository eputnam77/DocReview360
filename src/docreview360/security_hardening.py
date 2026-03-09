"""Keycloak SSO hardening utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, cast

from cryptography.fernet import Fernet
from celery.schedules import crontab

from .auth import keycloak_mfa_login
from .backup_utils import create_backup
from .celery_app import app


def encrypt_backup(path: str | Path, data: str = "", key: bytes | None = None) -> bytes:
    """Write ``data`` encrypted to ``path`` and return the key used."""
    dest = Path(path)
    if not dest.parent.exists():
        raise FileNotFoundError(dest.parent)
    enc_key = key or Fernet.generate_key()
    cipher = Fernet(enc_key)
    token = cipher.encrypt(data.encode())
    dest.write_bytes(token)
    return enc_key


def import_realm_file(path: str) -> Dict[str, Any]:
    """Load a Keycloak realm JSON export from ``path``."""
    target = Path(path)
    data = json.loads(target.read_text())
    if "realm" not in data:
        raise ValueError("invalid realm export")
    return cast(Dict[str, Any], data)


def enforce_mfa_login(username: str, password: str, otp: str) -> str:
    """Authenticate using the Keycloak MFA stub."""
    return keycloak_mfa_login(username, password, otp)


def secure_backup(path: str) -> str:
    """Create and encrypt a daily backup."""
    backup = create_backup(Path(path))
    import gzip

    with gzip.open(backup, "rt", encoding="utf-8") as fh:
        data = fh.read()
    encrypt_backup(backup, data)
    return str(backup)


app.task(name="docreview360.secure_backup")(secure_backup)


def enable_fedramp_backup(path: str) -> None:
    """Schedule encrypted daily backups required by FedRAMP."""
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["fedramp_backup"] = {
        "task": "docreview360.secure_backup",
        "schedule": crontab(hour=1, minute=0),
        "args": (path,),
    }
