# SPDX-License-Identifier: MIT
"""Auth data models — User, Token, UserRecord, PasswordPolicy, PasswordPolicyError."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

CHARACTER_CLASS_LABELS = {
    "uppercase": "uppercase letters",
    "lowercase": "lowercase letters",
    "digits": "numbers",
    "symbols": "symbols",
}


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


class PasswordPolicyError(ValueError):
    """Raised when a password fails to meet the configured policy."""


class Token(BaseModel):
    """Response model for access tokens."""

    access_token: str
    token_type: str
    expires_in: int = 0
    refresh_token: str | None = None


class User(BaseModel):
    """Simple user model."""

    username: str
    active: bool = True


@dataclass(slots=True)
class UserRecord:
    """Persistent representation of an authenticated user."""

    username: str
    password_hash: str
    otp_secret: str | None
    active: bool
    failed_attempts: int
    locked_until: datetime | None
    token_generation: int = 0


_PBKDF2_ITERATIONS = 120_000


def _hash_password_fallback(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password_fallback(password: str, password_hash: str) -> bool:
    if not password_hash.startswith("pbkdf2$"):
        return False
    parts = password_hash.split("$")
    if len(parts) != 4:
        return False
    _, iterations_text, salt_hex, digest_hex = parts
    try:
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return secrets.compare_digest(digest.hex(), digest_hex)


@dataclass(frozen=True)
class PasswordPolicy:
    """Configurable password policy loaded from settings."""

    min_length: int
    character_classes: tuple[str, ...]
    min_character_classes: int
    disallow_reuse: bool
    symbol_characters: str
    history_count: int = 5       # number of previous passwords to check (0 = disabled)
    max_age_days: int = 0         # 0 = never expire

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
            "history_count": 5,
            "max_age_days": 0,
        }

        try:
            from ..settings_manager import load_settings
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

            symbol_characters = policy_settings.get("symbol_characters")
            if isinstance(symbol_characters, str) and symbol_characters.strip():
                config["symbol_characters"] = symbol_characters.strip()

            history_count = policy_settings.get("history_count")
            if isinstance(history_count, int) and history_count >= 0:
                config["history_count"] = history_count

            max_age_days = policy_settings.get("max_age_days")
            if isinstance(max_age_days, int) and max_age_days >= 0:
                config["max_age_days"] = max_age_days

        return cls(**config)

    def validate(
        self,
        password: str,
        *,
        existing_hash: str | None = None,
        password_history: list[str] | None = None,
    ) -> None:
        """Raise :class:`PasswordPolicyError` when ``password`` violates the policy."""
        # Import lazily to avoid circular import with UserRepository
        from ._repository import UserRepository

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

        if self.history_count > 0 and password_history:
            for hist_hash in password_history[: self.history_count]:
                try:
                    if UserRepository.verify_password(password, hist_hash):
                        n = min(self.history_count, len(password_history))
                        errors.append(
                            f"Password must differ from your last {n} password(s)."
                        )
                        break
                except Exception:
                    pass

        if errors:
            raise PasswordPolicyError(" ".join(errors))
