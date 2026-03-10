# SPDX-License-Identifier: MIT
"""Shared database accessor for core domain persistence.

All modules that need to persist state across server restarts should import
``get_db`` from this module so they reuse the same lazily-initialised
:class:`~docreview360.database.Database` instance.
"""

from __future__ import annotations

import os

from .database import Database, default_url

_db: Database | None = None


def get_db() -> Database:
    """Return the lazily-initialised application :class:`Database` instance.

    The database is migrated (tables created) on first access so callers do
    not need to call :meth:`Database.migrate` themselves.
    """

    global _db
    if _db is None:
        url = os.getenv("DOCREVIEW360_DATABASE_URL", default_url("sqlite"))
        _db = Database(url)
        _db.migrate()
    return _db


def reset_db(url: str | None = None) -> None:
    """Replace the shared DB instance (primarily for tests).

    Passing *url* creates a new instance at that URL.  Passing ``None``
    drops the current instance so the next call to :func:`get_db` will
    reinitialise from environment variables.
    """

    global _db
    if url is None:
        _db = None
    else:
        _db = Database(url)
        _db.migrate()
