"""Load and save application configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILE = Path("docreview360.yaml")


@dataclass
class ConnectorSettings:
    """Settings for an external log connector."""

    type: str
    endpoint: str
    api_key: str | None = None
    batch_size: int = 1


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
    # Toggle for AI auto-assignment of technical writers
    # Disabled by default per request
    ai_auto_assign_writers: bool = False
    # Toggle read logging for confidential data endpoints
    log_reads: bool = True
    # Pattern for exported filenames; placeholders: {id}, {number}
    filename_template: str = "{id}"
    # External log connectors configuration
    log_connectors: list["ConnectorSettings"] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Config | None":
        """Return a ``Config`` loaded from ``path`` or ``None`` if missing."""
        if not path.exists():
            return None
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {path}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid config structure in {path}")
        data: dict[str, Any] = raw
        if "database_url" not in data:
            data["database_url"] = None
        connectors_raw = data.pop("log_connectors", []) or []
        connectors = [ConnectorSettings(**c) for c in connectors_raw]
        data["log_connectors"] = connectors
        return cls(**data)

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Persist this configuration to ``path`` creating directories as needed."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                k: ([c.__dict__ for c in v] if k == "log_connectors" else v)
                for k, v in self.__dict__.items()
                if v is not None
            }
            path.write_text(yaml.safe_dump(data))
        except OSError as exc:
            raise OSError(f"Failed to write config to {path}") from exc
