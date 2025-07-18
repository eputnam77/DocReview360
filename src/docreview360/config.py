from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILE = Path("docreview360.yaml")


@dataclass
class Config:
    """Configuration options for DocReview360."""

    database: str
    editor: str
    cms: str
    auth: str
    database_url: str | None = None
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Config | None":
        """Return a ``Config`` loaded from ``path`` or ``None`` if missing."""
        if not path.exists():
            return None
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - yaml error is rare
            raise ValueError(f"Invalid YAML in {path}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid config structure in {path}")
        data: dict[str, Any] = raw
        if "database_url" not in data:
            data["database_url"] = None
        return cls(**data)

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Persist this configuration to ``path`` creating directories as needed."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {k: v for k, v in self.__dict__.items() if v is not None}
            path.write_text(yaml.safe_dump(data))
        except OSError as exc:
            raise OSError(f"Failed to write config to {path}") from exc
