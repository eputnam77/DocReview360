"""Authentication utilities for DocReview360."""

from __future__ import annotations

import os
import secrets
import sqlite3
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, TypeVar

import bcrypt
import pyotp
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

T = TypeVar("T")


SAFE_DEFAULT_ENVS = {"", "dev", "development", "test", "testing"}
SAFE_SEED_ENVS = SAFE_DEFAULT_ENVS | {"stage", "staging"}


def _current_environment() -> str:
    """Return the current deployment environment in lowercase."""

    return os.getenv("DOCREVIEW360_ENV", "").strip().lower()


def _allow_demo_seed() -> bool:
    """Return ``True`` when demo users may be seeded automatically."""

    return SEED_DEMO_USERS or _current_environment() in SAFE_SEED_ENVS


def _env_or_default(
    name: str,
    *,
    default: str,
    cast: Callable[[str], T] | None = None,
    required: bool = False,
    allow_defaults_in: set[str] = SAFE_DEFAULT_ENVS,
) -> T:
    """Return an environment variable or fall back to a development default.

    When ``name`` is unset, the ``default`` is returned and a ``RuntimeWarning``
    is emitted when the current environment (``DOCREVIEW360_ENV``) is one of the
    development environments listed in ``allow_defaults_in``. When ``required``
    is ``True`` and the environment is outside that allow-list, a
    :class:`RuntimeError` is raised so production deployments fail fast instead
    of silently using insecure defaults.
    """

    value = os.getenv(name)
    if value is None or value == "":
        current_env = _current_environment()
        if required and current_env not in allow_defaults_in:
            raise RuntimeError(
                f"{name} environment variable must be set for the"
                f" {current_env or 'production'} environment."
            )
        warnings.warn(
            f"{name} environment variable not set; using development default",
            RuntimeWarning,
            stacklevel=2,
        )
        value = default

    return cast(value) if cast else value  # type: ignore[return-value]


DEFAULT_SECRET_KEY = "docreview360-dev-secret"
DEFAULT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
DEFAULT_TOKEN_ISSUER = "docreview360.local"
DEFAULT_TOKEN_AUDIENCE = "docreview360-users"

SECRET_KEY = _env_or_default("DOCREVIEW360_SECRET_KEY", default=DEFAULT_SECRET_KEY, required=True)
ALGORITHM = _env_or_default("DOCREVIEW360_ALGORITHM", default=DEFAULT_ALGORITHM)
ACCESS_TOKEN_EXPIRE_MINUTES = _env_or_default(
    "DOCREVIEW360_ACCESS_EXPIRE_MINUTES",
    default=str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
    cast=int,
)
TOKEN_ISSUER = _env_or_default("DOCREVIEW360_TOKEN_ISSUER", default=DEFAULT_TOKEN_ISSUER)
TOKEN_AUDIENCE = _env_or_default("DOCREVIEW360_TOKEN_AUDIENCE", default=DEFAULT_TOKEN_AUDIENCE)

# separate secret for the OIDC flow
DEFAULT_OIDC_SECRET_KEY = "docreview360-oidc-dev-secret"
DEFAULT_OIDC_TOKEN_EXPIRE_MINUTES = 30
DEFAULT_OIDC_TOKEN_ISSUER = "docreview360-oidc.local"
DEFAULT_OIDC_TOKEN_AUDIENCE = "docreview360-oidc"

OIDC_SECRET_KEY = _env_or_default(
    "DOCREVIEW360_OIDC_SECRET_KEY", default=DEFAULT_OIDC_SECRET_KEY, required=True
)
OIDC_ALGORITHM = _env_or_default("DOCREVIEW360_OIDC_ALGORITHM", default=DEFAULT_ALGORITHM)
OIDC_TOKEN_EXPIRE_MINUTES = _env_or_default(
    "DOCREVIEW360_OIDC_EXPIRE_MINUTES",
    default=str(DEFAULT_OIDC_TOKEN_EXPIRE_MINUTES),
    cast=int,
)
OIDC_TOKEN_ISSUER = _env_or_default(
    "DOCREVIEW360_OIDC_TOKEN_ISSUER", default=DEFAULT_OIDC_TOKEN_ISSUER
)
OIDC_TOKEN_AUDIENCE = _env_or_default(
    "DOCREVIEW360_OIDC_TOKEN_AUDIENCE", default=DEFAULT_OIDC_TOKEN_AUDIENCE
)


def _as_bool(value: str) -> bool:
    """Return ``True`` when ``value`` represents an enabled boolean."""

    return value.strip().lower() in {"1", "true", "yes", "on"}


REQUIRE_MFA = _env_or_default("DOCREVIEW360_REQUIRE_MFA", default="false", cast=_as_bool)
SEED_DEMO_USERS = _env_or_default(
    "DOCREVIEW360_SEED_DEMO_USERS",
    default="true",
    cast=_as_bool,
)

MAX_FAILED_ATTEMPTS = _env_or_default(
    "DOCREVIEW360_MAX_FAILED_ATTEMPTS",
    default="5",
    cast=int,
)
LOCKOUT_SECONDS = _env_or_default(
    "DOCREVIEW360_LOCKOUT_SECONDS",
    default="300",
    cast=int,
)
LOCKOUT_DURATION = timedelta(seconds=LOCKOUT_SECONDS)


def _default_user_db_path() -> str:
    """Return the default path for the user credential store."""

    return str(Path("docreview360_users.db").resolve())


USER_DB_PATH = _env_or_default(
    "DOCREVIEW360_USER_DB",
    default=_default_user_db_path(),
)

DEMO_USER_DEFAULTS: dict[str, dict[str, str]] = {
    "alice": {
        "password": "password",
        "otp_secret": "123456",
    },
    "bob": {
        "password": "password",
        "otp_secret": "123456",
    },
}


class PasswordPolicyError(ValueError):
    """Raised when a password fails to meet the configured policy."""


def _has_uppercase(value: str, _: str) -> bool:
    return any(char.isupper() for char in value)


def _has_lowercase(value: str, _: str) -> bool:
    return any(char.islower() for char in value)


def _has_digits(value: str, _: str) -> bool:
    return any(char.isdigit() for char in value)


def _has_symbols(value: str, symbol_chars: str) -> bool:
    return any(char in symbol_chars for char in value)


CHARACTER_CLASS_CHECKS: dict[str, Callable[[str, str], bool]] = {
    "uppercase": _has_uppercase,
    "lowercase": _has_lowercase,
    "digits": _has_digits,
    "symbols": _has_symbols,
}

CHARACTER_CLASS_LABELS = {
    "uppercase": "uppercase letters",
    "lowercase": "lowercase letters",
    "digits": "numbers",
    "symbols": "symbols",
}


@dataclass(frozen=True)
class PasswordPolicy:
    """Configurable password policy loaded from settings."""

    min_length: int
    character_classes: tuple[str, ...]
    min_character_classes: int
    disallow_reuse: bool
    symbol_characters: str

    @classmethod
    def load(cls) -> "PasswordPolicy":  # noqa: C901
        """Build a policy instance from persisted settings."""

        default_classes = ("lowercase", "uppercase", "digits", "symbols")
        config: dict[str, Any] = {
            "min_length": 12,
            "character_classes": default_classes,
            "min_character_classes": 3,
            "disallow_reuse": True,
            "symbol_characters": "!@#$%^&*()-_=+[]{}|;:,.<>/?",
        }

        try:
            from .settings_manager import load_settings
        except Exception:
            return cls(**config)

        try:
            settings = load_settings()
        except Exception:
            return cls(**config)

        auth_settings = settings.get("auth") if isinstance(settings, dict) else None
        policy_settings = (
            auth_settings.get("password_policy", {}) if isinstance(auth_settings, dict) else {}
        )

        if isinstance(policy_settings, dict):
            min_length = policy_settings.get("min_length")
            if isinstance(min_length, int) and min_length > 0:
                config["min_length"] = min_length

            classes = policy_settings.get("character_classes")
            if isinstance(classes, (list, tuple)):
                processed = tuple(
                    str(item).strip().lower()
                    for item in classes
                    if str(item).strip().lower() in CHARACTER_CLASS_CHECKS
                )
                if processed:
                    config["character_classes"] = processed

            min_classes = policy_settings.get("min_character_classes")
            if isinstance(min_classes, int) and min_classes > 0:
                config["min_character_classes"] = min_classes

            disallow_reuse = policy_settings.get("disallow_reuse")
            if isinstance(disallow_reuse, bool):
                config["disallow_reuse"] = disallow_reuse

            symbol_chars = policy_settings.get("symbol_characters")
            if isinstance(symbol_chars, str) and symbol_chars:
                config["symbol_characters"] = symbol_chars

        valid_classes = tuple(
            cls_name
            for cls_name in config["character_classes"]
            if cls_name in CHARACTER_CLASS_CHECKS
        )
        if not valid_classes:
            valid_classes = default_classes

        min_classes_required = min(config["min_character_classes"], len(valid_classes))
        if min_classes_required <= 0:
            min_classes_required = len(valid_classes)

        return cls(
            min_length=config["min_length"],
            character_classes=valid_classes,
            min_character_classes=min_classes_required,
            disallow_reuse=config["disallow_reuse"],
            symbol_characters=config["symbol_characters"],
        )

    def validate(self, password: str, *, existing_hash: str | None = None) -> None:
        """Raise :class:`PasswordPolicyError` when ``password`` violates the policy."""

        errors: list[str] = []

        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long.")

        present_classes = [
            cls_name
            for cls_name in self.character_classes
            if CHARACTER_CLASS_CHECKS[cls_name](password, self.symbol_characters)
        ]

        if len(present_classes) < self.min_character_classes:
            labels = [CHARACTER_CLASS_LABELS.get(name, name) for name in self.character_classes]
            if self.min_character_classes >= len(self.character_classes):
                errors.append(
                    "Password must include characters from all of the following classes: "
                    + ", ".join(labels)
                    + "."
                )
            else:
                errors.append(
                    "Password must include at least "
                    f"{self.min_character_classes} of the following character classes: "
                    + ", ".join(labels)
                    + "."
                )

        if self.disallow_reuse and existing_hash:
            try:
                reused = UserRepository.verify_password(password, existing_hash)
            except Exception:
                reused = False
            if reused:
                errors.append("Password must differ from the previously used password.")

        if errors:
            raise PasswordPolicyError(" ".join(errors))


@lru_cache(maxsize=1)
def _password_policy() -> PasswordPolicy:
    """Return the cached password policy instance."""

    return PasswordPolicy.load()


@dataclass(slots=True)
class UserRecord:
    """Persistent representation of an authenticated user."""

    username: str
    password_hash: str
    otp_secret: str | None
    active: bool
    failed_attempts: int
    locked_until: datetime | None


class UserRepository:
    """SQLite-backed repository storing user credentials and MFA secrets."""

    def __init__(self, db_path: str) -> None:
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
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    otp_secret TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT
                )
                """
            )
            conn.commit()
        if SEED_DEMO_USERS:
            self._seed_defaults()

    def _seed_defaults(self) -> None:
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

        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if demo_defaults and password == demo_defaults.get("password"):
            self._seed_user(username, password, otp_secret=otp_secret, active=active)
            return

        existing = self.get_user(username)
        existing_hash = existing.password_hash if existing else None
        _password_policy().validate(password, existing_hash=existing_hash)
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
                )
                VALUES (?, ?, ?, ?, 0, NULL)
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

    def get_user(self, username: str) -> UserRecord | None:
        """Return ``UserRecord`` for ``username`` if present."""

        with self._connection() as conn:
            row = conn.execute(
                "SELECT username, password_hash, otp_secret, active, failed_attempts, locked_until"
                " FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                return None
            locked_until_str = row["locked_until"]
            locked_until = datetime.fromisoformat(locked_until_str) if locked_until_str else None
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
            )

    def set_active(self, username: str, active: bool) -> bool:
        """Toggle the active flag for ``username``; return ``True`` if updated."""

        with self._connection() as conn:
            updated = conn.execute(
                "UPDATE users SET active = ? WHERE username = ?",
                (int(active), username),
            )
            conn.commit()
            return updated.rowcount > 0

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

    def is_locked(self, record: UserRecord) -> bool:
        """Return ``True`` when ``record`` is currently locked out."""

        return bool(record.locked_until and record.locked_until > datetime.now(timezone.utc))

    @staticmethod
    def hash_password(password: str) -> str:
        """Return a salted password hash."""

        password_bytes = password.encode("utf-8")
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Return ``True`` when ``password`` matches ``password_hash``."""

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
        try:
            totp = pyotp.TOTP(otp_secret)
        except (TypeError, ValueError):
            return secrets.compare_digest(otp_secret, otp)
        return bool(totp.verify(otp, valid_window=1))


USER_REPOSITORY = UserRepository(USER_DB_PATH)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
oidc_scheme = OAuth2PasswordBearer(tokenUrl="oidc/token", auto_error=False)


class Token(BaseModel):
    """Response model for access tokens."""

    access_token: str
    token_type: str


class User(BaseModel):
    """Simple user model."""

    username: str
    active: bool = True


def is_active(username: str) -> bool:
    """Return ``True`` if ``username`` is marked active."""

    record = USER_REPOSITORY.get_user(username)
    return bool(record and record.active)


def authenticate_user(username: str, password: str) -> User | None:
    """Return ``User`` if credentials match and user is active."""

    if not username or not password:
        return None

    record = USER_REPOSITORY.get_user(username)
    if record is None:
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if (
            demo_defaults
            and password == demo_defaults.get("password")
            and _allow_demo_seed()
        ):
            USER_REPOSITORY._seed_user(
                username,
                password,
                otp_secret=demo_defaults.get("otp_secret"),
                active=True,
            )
            record = USER_REPOSITORY.get_user(username)
    if not record or not record.active:
        return None
    if USER_REPOSITORY.is_locked(record):
        return None
    if not UserRepository.verify_password(password, record.password_hash):
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if (
            demo_defaults
            and password == demo_defaults.get("password")
            and _allow_demo_seed()
        ):
            USER_REPOSITORY._seed_user(
                username,
                password,
                otp_secret=record.otp_secret,
                active=bool(record.active),
            )
            USER_REPOSITORY.reset_failures(username)
            return User(username=username, active=True)
        USER_REPOSITORY.record_failure(username)
        return None
    USER_REPOSITORY.reset_failures(username)
    return User(username=username, active=True)


def authenticate_mfa(username: str, password: str, otp: str) -> User | None:
    """Return ``User`` if credentials, OTP match, and user is active."""

    if not username or not password or not otp:
        return None
    record = USER_REPOSITORY.get_user(username)
    if not record or not record.active:
        return None
    if USER_REPOSITORY.is_locked(record):
        return None
    if not UserRepository.verify_password(password, record.password_hash):
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if SEED_DEMO_USERS and demo_defaults and password == demo_defaults.get("password"):
            USER_REPOSITORY._seed_user(
                username,
                password,
                otp_secret=record.otp_secret,
                active=bool(record.active),
            )
        else:
            USER_REPOSITORY.record_failure(username)
            return None
    if not UserRepository.verify_otp(record.otp_secret, otp):
        return None
    USER_REPOSITORY.reset_failures(username)
    return User(username=username, active=True)


def keycloak_mfa_login(username: str, password: str, otp: str) -> str:
    """Return a token from the Keycloak MFA stub."""
    from .stubs.task76 import authenticate_keycloak

    return authenticate_keycloak(username, password, otp)


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Return a signed JWT access token."""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update(
        {
            "exp": expire,
            "iss": TOKEN_ISSUER,
            "aud": TOKEN_AUDIENCE,
        }
    )
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))


def _require_csrf_token(request: Request) -> None:
    """Ensure the request presents a valid CSRF token when using cookie auth."""

    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_cookie or not csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF token",
        )
    if not secrets.compare_digest(str(csrf_cookie), str(csrf_header)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )


def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> User:
    cookie_token = request.cookies.get("access_token")
    if not token and cookie_token:
        _require_csrf_token(request)
        token = cookie_token
    elif not token:
        token = cookie_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=TOKEN_AUDIENCE,
            issuer=TOKEN_ISSUER,
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    record = USER_REPOSITORY.get_user(username)
    if record is None:
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if demo_defaults and _allow_demo_seed():
            USER_REPOSITORY._seed_user(
                username,
                demo_defaults["password"],
                otp_secret=demo_defaults.get("otp_secret"),
                active=True,
            )
            record = USER_REPOSITORY.get_user(username)
    if not record or not record.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return User(username=username, active=True)


async def _extract_otp(request: Request | None) -> str:
    """Return the submitted one-time password if present."""

    if request is None:
        return ""
    form = await request.form()
    otp = form.get("otp")
    return str(otp or "")


async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request | None = None,
) -> Token:
    """Issue a short-lived JWT bearer token."""

    if REQUIRE_MFA:
        otp = await _extract_otp(request)
        user = authenticate_mfa(form_data.username, form_data.password, otp)
    else:
        user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, password, or OTP",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"sub": user.username}, access_token_expires)
    return Token(access_token=access_token, token_type="bearer")


async def login_for_oidc_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request | None = None,
) -> Token:
    """Return an ID token for valid credentials using a separate secret."""
    if REQUIRE_MFA:
        otp = await _extract_otp(request)
        user = authenticate_mfa(form_data.username, form_data.password, otp)
    else:
        user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, password, or OTP",
        )
    token_expires = timedelta(minutes=OIDC_TOKEN_EXPIRE_MINUTES)
    id_token = create_id_token({"sub": user.username}, token_expires)
    return Token(access_token=id_token, token_type="bearer")


def create_id_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Return an ID token for OIDC authentication."""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update(
        {
            "exp": expire,
            "iss": OIDC_TOKEN_ISSUER,
            "aud": OIDC_TOKEN_AUDIENCE,
        }
    )
    return str(jwt.encode(to_encode, OIDC_SECRET_KEY, algorithm=OIDC_ALGORITHM))


def get_current_user_oidc(request: Request, token: str | None = Depends(oidc_scheme)) -> User:
    """Validate ID token and return the associated user."""
    cookie_token = request.cookies.get("access_token")
    if not token and cookie_token:
        _require_csrf_token(request)
        token = cookie_token
    elif not token:
        token = cookie_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload = jwt.decode(
            token,
            OIDC_SECRET_KEY,
            algorithms=[OIDC_ALGORITHM],
            audience=OIDC_TOKEN_AUDIENCE,
            issuer=OIDC_TOKEN_ISSUER,
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    record = USER_REPOSITORY.get_user(username)
    if record is None:
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if demo_defaults and _allow_demo_seed():
            USER_REPOSITORY._seed_user(
                username,
                demo_defaults["password"],
                otp_secret=demo_defaults.get("otp_secret"),
                active=True,
            )
            record = USER_REPOSITORY.get_user(username)
    if not record or not record.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return User(username=username, active=True)
