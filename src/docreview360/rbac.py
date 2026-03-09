"""Role-based access control helpers backed by a persistent store."""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Iterable, Iterator, Mapping, Set

from fastapi import Depends, HTTPException, status

from . import auth, settings_manager
from .audit import log_audit_event


class RoleRepositoryError(RuntimeError):
    """Raised when the role persistence layer encounters an error."""


class RoleRepository:
    """SQLite-backed repository storing role assignments."""

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._path = Path(db_path)
        if not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        try:
            yield conn
        except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive
            raise RoleRepositoryError("role store operation failed") from exc
        finally:
            conn.close()

    def _initialise(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_roles (
                    username TEXT NOT NULL,
                    role TEXT NOT NULL,
                    PRIMARY KEY (username, role)
                )
                """
            )
            conn.commit()
        with self._connection() as conn:
            existing = conn.execute("SELECT 1 FROM user_roles LIMIT 1").fetchone()
        if existing is None:
            self.seed_defaults()

    def seed_defaults(self) -> None:
        defaults = {
            "alice": {"user", "admin"},
            "bob": {"auditor"},
            "system": {"admin"},
        }
        with self._connection() as conn:
            for username, roles in defaults.items():
                for role in roles:
                    conn.execute(
                        "INSERT OR IGNORE INTO user_roles (username, role) VALUES (?, ?)",
                        (username, role),
                    )
            conn.commit()

    def clear(self) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM user_roles")
            conn.commit()

    def set_roles(self, username: str, roles: Iterable[str]) -> None:
        normalized = sorted({_normalize_role(role) for role in roles})
        with self._connection() as conn:
            conn.execute("DELETE FROM user_roles WHERE username = ?", (username,))
            if normalized:
                conn.executemany(
                    "INSERT INTO user_roles (username, role) VALUES (?, ?)",
                    [(username, role) for role in normalized],
                )
            conn.commit()

    def add_role(self, username: str, role: str) -> None:
        normalized = _normalize_role(role)
        with self._connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO user_roles (username, role) VALUES (?, ?)",
                (username, normalized),
            )
            conn.commit()

    def remove_role(self, username: str, role: str) -> None:
        normalized = _normalize_role(role)
        with self._connection() as conn:
            conn.execute(
                "DELETE FROM user_roles WHERE username = ? AND role = ?",
                (username, normalized),
            )
            conn.commit()

    def get_roles(self, username: str) -> set[str]:
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT role FROM user_roles WHERE username = ?",
                (username,),
            )
            rows = cursor.fetchall()
        return {row[0] for row in rows}

    def list_assignments(self) -> dict[str, set[str]]:
        mapping: dict[str, set[str]] = {}
        with self._connection() as conn:
            cursor = conn.execute("SELECT username, role FROM user_roles")
            for username, role in cursor.fetchall():
                mapping.setdefault(username, set()).add(role)
        return mapping


class _RoleCache:
    """In-memory cache of user role lookups."""

    def __init__(self) -> None:
        self._data: dict[str, frozenset[str]] = {}
        self._lock = RLock()

    def get(self, username: str, loader: Callable[[], set[str]]) -> set[str]:
        with self._lock:
            cached = self._data.get(username)
        if cached is not None:
            return set(cached)
        roles = loader()
        frozen = frozenset(roles)
        with self._lock:
            self._data[username] = frozen
        return set(frozen)

    def invalidate(self, username: str | None = None) -> None:
        with self._lock:
            if username is None:
                self._data.clear()
            else:
                self._data.pop(username, None)


class RoleBackendError(RuntimeError):
    """Raised when the role store cannot be queried."""


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    if not normalized:
        raise ValueError("role must be non-empty")
    return normalized


def _default_role_store_path() -> str:
    return str(Path("docreview360_roles.db").resolve())


def _role_store_path_from_env() -> str:
    return os.getenv("DOCREVIEW360_RBAC_DB", _default_role_store_path())


_DEFAULT_ROLE_PERMISSIONS: Mapping[str, Set[str]] = {
    "admin": {
        "create",
        "read",
        "update",
        "delete",
        "edit_field_x",
        "view_audit_log",
        "verification_override",
    },
    "manager": {"create", "read", "update"},
    "sme": {"read", "edit_field_x"},
    "reviewer": {"read"},
    "editor": {"read", "update"},
    "observer": {"read"},
    "viewer": {"read"},
    "user": {"read"},
    "auditor": {"view_audit_log"},
    "verifier": {"verification_override"},
}

ROLE_PERMISSIONS: dict[str, Set[str]] = {
    role: set(perms) for role, perms in _DEFAULT_ROLE_PERMISSIONS.items()
}

_ROLE_PERMISSIONS_MTIME: float | None = None
_ROLE_PERMISSIONS_LAST_CHECK: float = 0.0
_ROLE_PERMISSIONS_CHECK_INTERVAL: float = 5.0  # seconds between stat calls
_ROLE_PERMISSIONS_LOCK = RLock()

_ROLE_CACHE = _RoleCache()
_ROLE_REPOSITORY = RoleRepository(_role_store_path_from_env())
_ROLE_CACHE_MTIME: float | None = None


def _get_role_repository() -> RoleRepository:
    """Return the active role repository, reloading if the DB path changed."""

    global _ROLE_REPOSITORY
    current_path = Path(_role_store_path_from_env()).resolve()
    if _ROLE_REPOSITORY._path.resolve() != current_path or not current_path.exists():
        _ROLE_REPOSITORY = RoleRepository(current_path)
        _ROLE_CACHE.invalidate()
    return _ROLE_REPOSITORY


def _refresh_cache_mtime(repo: RoleRepository) -> None:
    global _ROLE_CACHE_MTIME
    try:
        mtime = repo._path.stat().st_mtime
    except FileNotFoundError:
        mtime = None
    if _ROLE_CACHE_MTIME != mtime:
        _ROLE_CACHE.invalidate()
        _ROLE_CACHE_MTIME = mtime


def configure_role_repository(path: str | os.PathLike[str]) -> None:
    """Replace the active role repository with one backed by ``path``."""

    os.environ["DOCREVIEW360_RBAC_DB"] = str(path)
    _get_role_repository()
    _refresh_cache_mtime(_ROLE_REPOSITORY)


def _with_repository(  # noqa: C901
    operation: Callable[[RoleRepository], None],
    username: str | None = None,
    *,
    actor: str | None = None,
    context: Mapping[str, Any] | None = None,
    reset: bool = False,
    reset_include_defaults: bool | None = None,
) -> None:
    base_context = dict(context or {})
    repo = _get_role_repository()
    _refresh_cache_mtime(repo)
    try:
        before_roles = repo.get_roles(username) if username else set()
    except RoleRepositoryError as exc:  # pragma: no cover - defensive
        raise RoleBackendError("role store operation failed") from exc
    try:
        operation(repo)
    except RoleRepositoryError as exc:  # pragma: no cover - defensive
        raise RoleBackendError("role store operation failed") from exc
    else:
        if username is None:
            _ROLE_CACHE.invalidate()
        else:
            _ROLE_CACHE.invalidate(username)
        _refresh_cache_mtime(repo)
        audit_actor = actor or "system"
        if username is not None:
            try:
                after_roles = repo.get_roles(username)
            except RoleRepositoryError as exc:  # pragma: no cover - defensive
                raise RoleBackendError("role store operation failed") from exc
            added = sorted(after_roles - before_roles)
            removed = sorted(before_roles - after_roles)
            if added or removed:
                roles_before = sorted(before_roles)
                roles_after = sorted(after_roles)
                for role in added:
                    event_context = {
                        "target_user": username,
                        "role": role,
                        "roles_before": roles_before,
                        "roles_after": roles_after,
                        **base_context,
                    }
                    log_audit_event(
                        f"rbac::{username}",
                        "role_added",
                        actor=audit_actor,
                        **event_context,
                    )
                for role in removed:
                    event_context = {
                        "target_user": username,
                        "role": role,
                        "roles_before": roles_before,
                        "roles_after": roles_after,
                        **base_context,
                    }
                    log_audit_event(
                        f"rbac::{username}",
                        "role_removed",
                        actor=audit_actor,
                        **event_context,
                    )
        if reset:
            reset_context = {"include_defaults": reset_include_defaults, **base_context}
            log_audit_event(
                "rbac::global",
                "roles_reset",
                actor=audit_actor,
                **reset_context,
            )


def set_user_roles(
    username: str,
    roles: Iterable[str],
    *,
    actor: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Assign ``roles`` to ``username`` replacing any existing mapping."""

    def _op(repo: RoleRepository) -> None:
        repo.set_roles(username, roles)

    _with_repository(_op, username=username, actor=actor, context=context)


def add_role(
    username: str,
    role: str,
    *,
    actor: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Add a single ``role`` to ``username``."""

    def _op(repo: RoleRepository) -> None:
        repo.add_role(username, role)

    _with_repository(_op, username=username, actor=actor, context=context)


def remove_role(
    username: str,
    role: str,
    *,
    actor: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Remove ``role`` from ``username``."""

    def _op(repo: RoleRepository) -> None:
        repo.remove_role(username, role)

    _with_repository(_op, username=username, actor=actor, context=context)


def get_roles(username: str) -> set[str]:
    """Return all roles assigned to ``username``."""

    try:
        repo = _get_role_repository()
        _refresh_cache_mtime(repo)
        return _ROLE_CACHE.get(username, lambda: repo.get_roles(username))
    except RoleRepositoryError as exc:
        raise RoleBackendError("role store operation failed") from exc


def has_role(username: str, role: str) -> bool:
    """Return ``True`` if ``username`` is assigned ``role``."""

    try:
        normalized = _normalize_role(role)
    except ValueError:
        return False
    return normalized in get_roles(username)


def has_permission(username: str, action: str) -> bool:
    """Return ``True`` if ``username`` may perform ``action`` based on roles."""

    reload_role_permissions()
    roles = {r.lower() for r in get_roles(username)}
    act = action.lower()
    return any(act in ROLE_PERMISSIONS.get(r, set()) for r in roles)


def list_role_assignments() -> Mapping[str, Set[str]]:
    """Return a snapshot of all role assignments."""

    try:
        return _get_role_repository().list_assignments()
    except RoleRepositoryError as exc:  # pragma: no cover - defensive
        raise RoleBackendError("role store operation failed") from exc


def reset_role_assignments(
    include_defaults: bool = True,
    *,
    actor: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Clear all assignments and optionally restore default roles."""

    def _op(repo: RoleRepository) -> None:
        repo.clear()
        if include_defaults:
            repo.seed_defaults()

    _with_repository(
        _op,
        actor=actor,
        context=context,
        reset=True,
        reset_include_defaults=include_defaults,
    )


def _normalize_permission(action: str) -> str:
    return action.strip().lower()


def _coerce_permissions(raw: Mapping[str, Any]) -> dict[str, Set[str]]:  # noqa: C901
    mapping: dict[str, Set[str]] = {}
    for role, values in raw.items():
        try:
            normalized_role = _normalize_role(str(role))
        except ValueError:
            continue
        permissions: set[str] = set()
        candidate: Any
        if isinstance(values, Mapping):
            candidate = values.get("permissions", [])
        else:
            candidate = values
        if candidate is None:
            permissions = set()
        elif isinstance(candidate, str):
            permission = _normalize_permission(candidate)
            if permission:
                permissions.add(permission)
        elif isinstance(candidate, Iterable):
            for item in candidate:
                if isinstance(item, str):
                    permission = _normalize_permission(item)
                    if permission:
                        permissions.add(permission)
        else:
            continue
        mapping[normalized_role] = permissions
    return mapping


def _load_role_permissions_from_settings() -> dict[str, Set[str]]:
    settings = settings_manager.load_settings(settings_manager.SETTINGS_FILE)
    configured: Mapping[str, Any] | None = None
    rbac_cfg = settings.get("rbac")
    if isinstance(rbac_cfg, Mapping):
        candidate = rbac_cfg.get("roles") or rbac_cfg.get("role_permissions")
        if isinstance(candidate, Mapping):
            configured = candidate
    if configured is None:
        candidate = settings.get("role_permissions")
        if isinstance(candidate, Mapping):
            configured = candidate
    permissions = {role: set(perms) for role, perms in _DEFAULT_ROLE_PERMISSIONS.items()}
    if configured:
        overrides = _coerce_permissions(configured)
        for role, perms in overrides.items():
            permissions[role] = perms
    return permissions


def reload_role_permissions(force: bool = False) -> None:
    """Reload role permissions from settings when they change.

    Uses a time-based debounce to avoid a ``stat()`` syscall on every
    ``has_permission()`` call — the settings file is only re-checked at most
    once every ``_ROLE_PERMISSIONS_CHECK_INTERVAL`` seconds.
    """

    global _ROLE_PERMISSIONS_MTIME, _ROLE_PERMISSIONS_LAST_CHECK
    now = time.monotonic()
    if not force and ROLE_PERMISSIONS and (now - _ROLE_PERMISSIONS_LAST_CHECK) < _ROLE_PERMISSIONS_CHECK_INTERVAL:
        return
    path = settings_manager.SETTINGS_FILE
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:  # pragma: no cover - defensive
        mtime = None
    _ROLE_PERMISSIONS_LAST_CHECK = now
    with _ROLE_PERMISSIONS_LOCK:
        if not force and ROLE_PERMISSIONS and _ROLE_PERMISSIONS_MTIME == mtime:
            return
        permissions = _load_role_permissions_from_settings()
        ROLE_PERMISSIONS.clear()
        for role, perms in permissions.items():
            ROLE_PERMISSIONS[role] = set(perms)
        _ROLE_PERMISSIONS_MTIME = mtime


def get_role_permissions() -> Mapping[str, Set[str]]:
    """Return the current role-to-permission mapping."""

    reload_role_permissions()
    return ROLE_PERMISSIONS


reload_role_permissions(force=True)


def require_role(role: str) -> Callable[[auth.User], auth.User]:
    """Return a dependency ensuring the current user has ``role``."""

    def _dependency(user: auth.User = Depends(auth.get_current_user)) -> auth.User:
        try:
            if not has_role(user.username, role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden",
                )
        except RoleBackendError as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Role store unavailable",
            ) from exc
        return user

    return _dependency


def require_permission(action: str) -> Callable[[auth.User], auth.User]:
    """Return a dependency ensuring the user has permission ``action``."""

    def _dependency(user: auth.User = Depends(auth.get_current_user)) -> auth.User:
        try:
            if not has_permission(user.username, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden",
                )
        except RoleBackendError as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Role store unavailable",
            ) from exc
        return user

    return _dependency
