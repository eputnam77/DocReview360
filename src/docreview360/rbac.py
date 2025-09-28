"""Role-based access control helpers backed by a persistent store."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Callable, Iterable, Iterator, Mapping, Set

from fastapi import Depends, HTTPException, status

from . import auth


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
    return role.strip().lower()


def _default_role_store_path() -> str:
    return str(Path("docreview360_roles.db").resolve())


def _role_store_path_from_env() -> str:
    return os.getenv("DOCREVIEW360_RBAC_DB", _default_role_store_path())


ROLE_PERMISSIONS: dict[str, Set[str]] = {
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
    "user": {"read"},
    "auditor": {"view_audit_log"},
    "verifier": {"verification_override"},
}

_ROLE_CACHE = _RoleCache()
_ROLE_REPOSITORY = RoleRepository(_role_store_path_from_env())


def configure_role_repository(path: str | os.PathLike[str]) -> None:
    """Replace the active role repository with one backed by ``path``."""

    global _ROLE_REPOSITORY
    _ROLE_REPOSITORY = RoleRepository(path)
    _ROLE_CACHE.invalidate()


def _with_repository(
    operation: Callable[[RoleRepository], None],
    username: str | None = None,
) -> None:
    try:
        operation(_ROLE_REPOSITORY)
    except RoleRepositoryError as exc:  # pragma: no cover - defensive
        raise RoleBackendError("role store operation failed") from exc
    else:
        if username is None:
            _ROLE_CACHE.invalidate()
        else:
            _ROLE_CACHE.invalidate(username)


def set_user_roles(username: str, roles: Iterable[str]) -> None:
    """Assign ``roles`` to ``username`` replacing any existing mapping."""

    def _op(repo: RoleRepository) -> None:
        repo.set_roles(username, roles)

    _with_repository(_op, username=username)


def add_role(username: str, role: str) -> None:
    """Add a single ``role`` to ``username``."""

    def _op(repo: RoleRepository) -> None:
        repo.add_role(username, role)

    _with_repository(_op, username=username)


def remove_role(username: str, role: str) -> None:
    """Remove ``role`` from ``username``."""

    def _op(repo: RoleRepository) -> None:
        repo.remove_role(username, role)

    _with_repository(_op, username=username)


def get_roles(username: str) -> set[str]:
    """Return all roles assigned to ``username``."""

    try:
        return _ROLE_CACHE.get(username, lambda: _ROLE_REPOSITORY.get_roles(username))
    except RoleRepositoryError as exc:
        raise RoleBackendError("role store operation failed") from exc


def has_role(username: str, role: str) -> bool:
    """Return ``True`` if ``username`` is assigned ``role``."""

    return _normalize_role(role) in get_roles(username)


def has_permission(username: str, action: str) -> bool:
    """Return ``True`` if ``username`` may perform ``action`` based on roles."""

    roles = {r.lower() for r in get_roles(username)}
    act = action.lower()
    return any(act in ROLE_PERMISSIONS.get(r, set()) for r in roles)


def list_role_assignments() -> Mapping[str, Set[str]]:
    """Return a snapshot of all role assignments."""

    try:
        return _ROLE_REPOSITORY.list_assignments()
    except RoleRepositoryError as exc:  # pragma: no cover - defensive
        raise RoleBackendError("role store operation failed") from exc


def reset_role_assignments(include_defaults: bool = True) -> None:
    """Clear all assignments and optionally restore default roles."""

    def _op(repo: RoleRepository) -> None:
        repo.clear()
        if include_defaults:
            repo.seed_defaults()

    _with_repository(_op)


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
