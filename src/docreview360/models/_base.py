# SPDX-License-Identifier: MIT
"""SQLAlchemy declarative base and Pydantic BaseModel shim."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import DeclarativeBase

try:  # pragma: no cover - pydantic optional
    from pydantic import BaseModel, Field  # noqa: F401
except Exception:  # pragma: no cover

    class BaseModel:  # type: ignore[no-redef]
        """Fallback stub when Pydantic is unavailable."""

        def __init__(self, **data: Any) -> None:  # pragma: no cover - simple shim
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:  # pragma: no cover
            return self.__dict__

        def model_validate(self, obj: Any) -> "BaseModel":  # pragma: no cover - convenience
            return obj

        @classmethod
        def model_validate_json(cls, json_data: str) -> "BaseModel":  # pragma: no cover
            import json

            return cls(**json.loads(json_data))

        @classmethod
        def model_json_schema(cls) -> dict[str, Any]:  # pragma: no cover
            return {}


class Base(DeclarativeBase):
    """Base class for all models."""
