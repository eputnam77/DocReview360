# SPDX-License-Identifier: MIT
"""Auth repository — UserRepository SQLite-backed credential store."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

try:  # Optional dependencies for production-grade auth.
    import bcrypt
except ModuleNotFoundError:  # pragma: no cover - minimal dev installs
    bcrypt = None  # type: ignore[assignment]

try:
    import pyotp
except ModuleNotFoundError:  # pragma: no cover - minimal dev installs
    pyotp = None  # type: ignore[assignment]

import secrets

from ._models import UserRecord, _hash_password_fallback, _verify_password_fallback


class UserRepository:
    """SQLite-backed repository storing user credentials and MFA secrets."""

    def __init__(self, db_path: str) -> None:
        # Import here to avoid circular import at module level
        from . import MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION, DEMO_USER_DEFAULTS, _allow_demo_seed

        self._path = Path(db_path)
        if not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _initialise(self) -> None:
        from . import _allow_demo_seed

        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    otp_secret TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    token_generation INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            try:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN token_generation INTEGER NOT NULL DEFAULT 0"
                )
            except Exception:  # column already exists
                pass
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                    jti TEXT PRIMARY KEY,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS password_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    changed_at TEXT NOT NULL
                )
                """
            )
            try:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN password_changed_at TEXT"
                )
            except Exception:  # column already exists
                pass
            conn.commit()
        if _allow_demo_seed():
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        from . import DEMO_USER_DEFAULTS

        legacy_totp = {"JBSWY3DPEHPK3PXP", "JBSWY3DPEHPK3PXQ"}
        for username, data in DEMO_USER_DEFAULTS.items():
            existing = self.get_user(username)
            if existing:
                if not self.verify_password(data["password"], existing.password_hash):
                    self._seed_user(
                        username,
                        data["password"],
                        otp_secret=data.get("otp_secret"),
                        active=bool(existing.active),
                    )
                if existing.otp_secret in legacy_totp and data.get("otp_secret"):
                    self.update_otp_secret(username, data["otp_secret"])
                continue
            self._seed_user(
                username,
                data["password"],
                otp_secret=data.get("otp_secret"),
                active=True,
            )

    def _seed_user(
        self,
        username: str,
        password: str,
        *,
        otp_secret: str | None = None,
        active: bool = True,
    ) -> None:
        """Insert or replace a demo user without enforcing the password policy."""
        password_hash = self.hash_password(password)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    otp_secret,
                    active,
                    failed_attempts,
                    locked_until
                ) VALUES (?, ?, ?, ?, 0, NULL)
                ON CONFLICT(username) DO UPDATE SET
                    password_hash=excluded.password_hash,
                    otp_secret=excluded.otp_secret,
                    active=excluded.active,
                    failed_attempts=0,
                    locked_until=NULL
                """,
                (username, password_hash, otp_secret, int(active)),
            )
            conn.commit()

    def create_user(
        self,
        username: str,
        password: str,
        *,
        otp_secret: str | None = None,
        active: bool = True,
    ) -> None:
        """Create or replace a user with a hashed password."""
        from . import DEMO_USER_DEFAULTS, _allow_demo_seed, _password_policy

        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if demo_defaults and password == demo_defaults.get("password"):
            self._seed_user(username, password, otp_secret=otp_secret, active=active)
            return

        existing = self.get_user(username)
        existing_hash = existing.password_hash if existing else None
        history = self.get_password_history(username) if existing else []
        _password_policy().validate(password, existing_hash=existing_hash, password_history=history)
        password_hash = self.hash_password(password)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    otp_secret,
                    active,
                    failed_attempts,
                    locked_until,
                    token_generation
                )
                VALUES (?, ?, ?, ?, 0, NULL, 0)
                ON CONFLICT(username) DO UPDATE SET
                    password_hash=excluded.password_hash,
                    otp_secret=excluded.otp_secret,
                    active=excluded.active,
                    failed_attempts=0,
                    locked_until=NULL,
                    token_generation=token_generation + 1
                """,
                (username, password_hash, otp_secret, int(active)),
            )
            conn.commit()
        self.add_password_history(username, password_hash)

    def get_user(self, username: str) -> UserRecord | None:
        """Return ``UserRecord`` for ``username`` if present."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT username, password_hash, otp_secret, active, failed_attempts,"
                " locked_until, token_generation"
                " FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                return None
            locked_until_str = row["locked_until"]
            locked_until = (
                datetime.fromisoformat(locked_until_str) if locked_until_str else None
            )
            if locked_until and locked_until <= datetime.now(timezone.utc):
                conn.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?",
                    (username,),
                )
                conn.commit()
                locked_until = None
            return UserRecord(
                username=row["username"],
                password_hash=row["password_hash"],
                otp_secret=row["otp_secret"],
                active=bool(row["active"]),
                failed_attempts=int(row["failed_attempts"]),
                locked_until=locked_until,
                token_generation=int(row["token_generation"] or 0),
            )

    def list_users(self) -> list[UserRecord]:
        """Return all users stored in the repository."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT username, password_hash, otp_secret, active, failed_attempts,"
                " locked_until, token_generation"
                " FROM users ORDER BY username"
            ).fetchall()
        records: list[UserRecord] = []
        for row in rows:
            locked_until_str = row["locked_until"]
            locked_until = (
                datetime.fromisoformat(locked_until_str) if locked_until_str else None
            )
            records.append(
                UserRecord(
                    username=row["username"],
                    password_hash=row["password_hash"],
                    otp_secret=row["otp_secret"],
                    active=bool(row["active"]),
                    failed_attempts=int(row["failed_attempts"]),
                    locked_until=locked_until,
                    token_generation=int(row["token_generation"] or 0),
                )
            )
        return records

    def bump_token_generation(self, username: str) -> int:
        """Increment ``token_generation`` for ``username``, invalidating all existing tokens."""
        with self._connection() as conn:
            conn.execute(
                "UPDATE users SET token_generation = token_generation + 1 WHERE username = ?",
                (username,),
            )
            conn.commit()
            row = conn.execute(
                "SELECT token_generation FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return int(row["token_generation"]) if row else 0

    def get_token_generation(self, username: str) -> int:
        """Return the current ``token_generation`` for ``username``, or 0 if unknown."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT token_generation FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return int(row["token_generation"] or 0) if row else 0

    def delete_user(self, username: str) -> bool:
        """Delete ``username`` from the repository; return ``True`` if removed."""
        with self._connection() as conn:
            deleted = conn.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            return deleted.rowcount > 0

    def rename_user(self, username: str, new_username: str) -> bool:
        """Rename ``username`` to ``new_username``; return ``True`` if updated."""
        with self._connection() as conn:
            updated = conn.execute(
                "UPDATE users SET username = ? WHERE username = ?",
                (new_username, username),
            )
            conn.commit()
            return updated.rowcount > 0

    def set_active(self, username: str, active: bool) -> bool:
        """Toggle the active flag for ``username``; return ``True`` if updated."""
        from . import DEMO_USER_DEFAULTS, _allow_demo_seed

        with self._connection() as conn:
            if active:
                updated = conn.execute(
                    "UPDATE users SET active = ? WHERE username = ?",
                    (int(active), username),
                )
            else:
                updated = conn.execute(
                    "UPDATE users SET active = ?, token_generation = token_generation + 1"
                    " WHERE username = ?",
                    (int(active), username),
                )
            conn.commit()
            if updated.rowcount > 0:
                return True

        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if demo_defaults and _allow_demo_seed():
            self._seed_user(
                username,
                demo_defaults["password"],
                otp_secret=demo_defaults.get("otp_secret"),
                active=active,
            )
            return True
        return False

    def update_otp_secret(self, username: str, otp_secret: str) -> None:
        """Persist a new MFA secret for ``username``."""
        with self._connection() as conn:
            conn.execute(
                "UPDATE users SET otp_secret = ? WHERE username = ?",
                (otp_secret, username),
            )
            conn.commit()

    def record_failure(self, username: str) -> None:
        """Increment the failed login counter and lock if necessary."""
        from . import LOCKOUT_DURATION, MAX_FAILED_ATTEMPTS

        with self._connection() as conn:
            row = conn.execute(
                "SELECT failed_attempts FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                return
            attempts = int(row["failed_attempts"]) + 1
            locked_until: datetime | None = None
            if attempts >= MAX_FAILED_ATTEMPTS:
                locked_until = datetime.now(timezone.utc) + LOCKOUT_DURATION
                attempts = 0
            conn.execute(
                "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE username = ?",
                (attempts, locked_until.isoformat() if locked_until else None, username),
            )
            conn.commit()

    def reset_failures(self, username: str) -> None:
        """Clear failure counters for ``username``."""
        with self._connection() as conn:
            conn.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?",
                (username,),
            )
            conn.commit()

    def add_password_history(self, username: str, password_hash: str) -> None:
        """Record ``password_hash`` in the history table for ``username``."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO password_history (username, password_hash, changed_at)"
                " VALUES (?, ?, ?)",
                (username, password_hash, now),
            )
            conn.execute(
                """
                DELETE FROM password_history WHERE id IN (
                    SELECT id FROM password_history WHERE username = ?
                    ORDER BY id DESC LIMIT -1 OFFSET 20
                )
                """,
                (username,),
            )
            conn.execute(
                "UPDATE users SET password_changed_at = ? WHERE username = ?",
                (now, username),
            )
            conn.commit()

    def get_password_history(self, username: str, limit: int = 20) -> list[str]:
        """Return the last ``limit`` password hashes for ``username``."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT password_hash FROM password_history"
                " WHERE username = ? ORDER BY id DESC LIMIT ?",
                (username, limit),
            ).fetchall()
        return [row["password_hash"] for row in rows]

    def get_password_age_days(self, username: str) -> int | None:
        """Return the number of days since the last password change, or None if unknown."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT password_changed_at FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None or not row["password_changed_at"]:
            return None
        try:
            changed_at = datetime.fromisoformat(row["password_changed_at"])
            if changed_at.tzinfo is None:
                changed_at = changed_at.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - changed_at
            return max(0, delta.days)
        except Exception:
            return None

    def is_password_expired(self, username: str, max_age_days: int) -> bool:
        """Return True if the password is older than ``max_age_days``."""
        if max_age_days <= 0:
            return False
        age = self.get_password_age_days(username)
        if age is None:
            return False
        return age >= max_age_days

    def is_locked(self, record: UserRecord) -> bool:
        """Return ``True`` when ``record`` is currently locked out."""
        return bool(
            record.locked_until and record.locked_until > datetime.now(timezone.utc)
        )

    @staticmethod
    def hash_password(password: str) -> str:
        """Return a salted password hash."""
        if bcrypt is None:
            return _hash_password_fallback(password)
        password_bytes = password.encode("utf-8")
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Return ``True`` when ``password`` matches ``password_hash``."""
        if bcrypt is None:
            return _verify_password_fallback(password, password_hash)
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            return False

    @staticmethod
    def verify_otp(otp_secret: str | None, otp: str) -> bool:
        """Validate ``otp`` using ``otp_secret`` if available."""
        if not otp_secret:
            return False
        if otp_secret.isdigit() and len(otp_secret) == len(otp):
            return secrets.compare_digest(otp_secret, otp)
        if pyotp is None:
            return secrets.compare_digest(otp_secret, otp)
        try:
            totp = pyotp.TOTP(otp_secret)
        except (TypeError, ValueError):
            return secrets.compare_digest(otp_secret, otp)
        return bool(totp.verify(otp, valid_window=1))

    def revoke_token(self, jti: str, expires_at: datetime) -> None:
        """Persist ``jti`` to the DB revocation table until it expires."""
        expires_iso = expires_at.isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
                (jti, expires_iso),
            )
            conn.execute("DELETE FROM revoked_tokens WHERE expires_at <= ?", (now_iso,))
            conn.commit()

    def is_token_revoked(self, jti: str) -> bool:
        """Return ``True`` if ``jti`` is present in the DB revocation table and unexpired."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT expires_at FROM revoked_tokens WHERE jti = ?", (jti,)
            ).fetchone()
        if row is None:
            return False
        if row[0] <= now_iso:
            return False
        return True
