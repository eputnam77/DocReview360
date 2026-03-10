# SPDX-License-Identifier: MIT
"""PostgreSQL row-level security (RLS) policy management.

When enabled, every row in content tables is gated by the ``org_id`` column
matching the session-local ``app.current_org_id`` setting.  This provides a
defence-in-depth layer complementary to the application-level org enforcement
in ``api/__init__.py``.

Usage::

    from docreview360.db_rls import install_rls_policies, set_rls_org_context

    # Once after creating the engine (PostgreSQL only):
    with engine.begin() as conn:
        install_rls_policies(conn)

    # Per request, before executing queries:
    with engine.begin() as conn:
        set_rls_org_context(conn, org_id=42)
        # ... queries here are restricted to org 42 ...
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# Tables that carry an org_id column and should be protected by RLS.
_RLS_TABLES: tuple[str, ...] = (
    "projects",
    "documents",
    "workflows",
    "approvals",
    "approval_records",
    "workflow_instance_records",
)


def is_postgresql(engine_or_conn: Any) -> bool:
    """Return True when the connected backend is PostgreSQL."""
    try:
        dialect = getattr(engine_or_conn, "dialect", None) or getattr(
            getattr(engine_or_conn, "engine", None), "dialect", None
        )
        return dialect is not None and dialect.name == "postgresql"
    except Exception:
        return False


def install_rls_policies(conn: Any) -> None:
    """Create RLS policies on content tables (PostgreSQL only).

    Safe to call multiple times — existing policies are dropped and recreated.
    This function is a no-op on non-PostgreSQL databases.
    """
    if not is_postgresql(conn):
        log.debug("db_rls: skipping RLS installation on non-PostgreSQL database")
        return

    from sqlalchemy import text

    for table in _RLS_TABLES:
        try:
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
            policy_name = f"rls_org_isolation_{table}"
            conn.execute(text(f"DROP POLICY IF EXISTS {policy_name} ON {table}"))
            conn.execute(
                text(
                    f"CREATE POLICY {policy_name} ON {table} "
                    "USING ("
                    "  org_id::text = current_setting('app.current_org_id', true)"
                    "  OR current_setting('app.current_org_id', true) IS NULL"
                    "  OR current_setting('app.current_org_id', true) = ''"
                    ")"
                )
            )
            log.debug("db_rls: installed RLS policy on %s", table)
        except Exception as exc:
            # Table may not have org_id column yet — log and continue gracefully.
            log.warning("db_rls: could not install RLS on %s: %s", table, exc)


def set_rls_org_context(conn: Any, org_id: int | str | None) -> None:
    """Set the ``app.current_org_id`` session variable for the connection.

    Call this once per request/transaction before executing queries so that
    RLS policies restrict results to the given organisation.  Pass ``None``
    to clear the restriction (superuser queries, background jobs, etc.).
    """
    from sqlalchemy import text

    value = str(org_id) if org_id is not None else ""
    conn.execute(text("SELECT set_config('app.current_org_id', :v, true)"), {"v": value})


def verify_rls_active(conn: Any) -> dict[str, bool]:
    """Return a mapping of table → RLS-enabled for all content tables.

    Useful in health checks and integration tests to assert RLS is installed.
    Always returns all-False on non-PostgreSQL backends.
    """
    if not is_postgresql(conn):
        return {t: False for t in _RLS_TABLES}

    from sqlalchemy import text

    result: dict[str, bool] = {}
    for table in _RLS_TABLES:
        try:
            row = conn.execute(
                text("SELECT relrowsecurity FROM pg_class WHERE relname = :t"),
                {"t": table},
            ).fetchone()
            result[table] = bool(row and row[0])
        except Exception:
            result[table] = False
    return result
