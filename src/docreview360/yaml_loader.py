# SPDX-License-Identifier: MIT
"""Shared YAML I/O helpers for DocReview360 configuration modules.

All YAML-backed config modules in this package delegate their file I/O to
:func:`load_yaml_file` and :func:`save_yaml_file` (or the :class:`YamlConfigLoader`
base class) so that safe-load error handling and atomic-write behaviour live in
one place.
"""

from __future__ import annotations

import os
import tempfile
from abc import ABC
from pathlib import Path
from typing import Any

import yaml


def load_yaml_file(path: Path, *, default: Any = None) -> Any:
    """Safe-load a YAML file and return its contents.

    Parameters
    ----------
    path:
        Location of the YAML file to read.
    default:
        Value returned when *path* does not exist.  Defaults to ``None``.

    Returns
    -------
    Any
        Parsed YAML value, or *default* when the file is absent.

    Raises
    ------
    ValueError
        If the file exists but contains invalid YAML.
    """
    if not path.exists():
        return default
    try:
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}") from exc


def save_yaml_file(path: Path, data: Any) -> None:
    """Atomically write *data* as YAML to *path*.

    Parent directories are created if they do not already exist.  The write is
    performed via a sibling temporary file that is then renamed into place so
    that concurrent readers never see a partially-written file.

    Parameters
    ----------
    path:
        Destination file path.
    data:
        Python object to serialise with ``yaml.safe_dump``.

    Raises
    ------
    OSError
        Propagated from the underlying filesystem operations.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialised = yaml.safe_dump(data)
    # Write to a sibling temp file then rename for atomicity.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".yaml.tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(serialised)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


class YamlConfigLoader(ABC):
    """Base class for YAML-backed configuration modules.

    Subclasses declare two class attributes:

    ``file_path`` : :class:`~pathlib.Path`
        The YAML file to load/save.
    ``default_data`` : Any
        Value returned by :meth:`load` when *file_path* does not exist.

    All methods delegate to :func:`load_yaml_file` / :func:`save_yaml_file` so
    validation and persistence logic stays in one place.
    """

    file_path: Path
    default_data: Any = None

    def load(self) -> Any:
        """Load from :attr:`file_path`, returning :attr:`default_data` if absent."""
        result = load_yaml_file(self.file_path, default=self.default_data)
        return result if result is not None else self.default_data

    def save(self, data: Any) -> None:
        """Save *data* as YAML to :attr:`file_path`."""
        save_yaml_file(self.file_path, data)

    def reload(self) -> Any:
        """Force a fresh load from disk, bypassing any in-memory state.

        The base implementation simply delegates to :meth:`load`; subclasses
        that maintain a cache should override this method to invalidate it.
        """
        return self.load()
