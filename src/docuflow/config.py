from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_FILE = Path("docuflow.yaml")


@dataclass
class Config:
    """Configuration options for DocuFlow."""

    database: str
    editor: str
    cms: str
    auth: str
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Config | None":
        """Return a ``Config`` loaded from ``path`` or ``None`` if missing."""
        if not path.exists():
            return None
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - yaml error is rare
            raise ValueError(f"Invalid YAML in {path}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Invalid config structure in {path}")
        return cls(**data)  # type: ignore[arg-type]

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Persist this configuration to ``path`` creating directories as needed."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(yaml.safe_dump(self.__dict__))
        except OSError as exc:
            raise OSError(f"Failed to write config to {path}") from exc
