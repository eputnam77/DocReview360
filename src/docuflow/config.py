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
        if not path.exists():
            return None
        data = yaml.safe_load(path.read_text()) or {}
        return cls(**data)  # type: ignore[arg-type]

    def save(self, path: Path = CONFIG_FILE) -> None:
        path.write_text(yaml.safe_dump(self.__dict__))
