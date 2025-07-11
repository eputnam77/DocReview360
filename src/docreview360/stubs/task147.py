"""Implementation for task 147."""

from pathlib import Path

from ..environment import add_environment, switch_environment


def task147(path: Path | None = None) -> str:
    """Add an environment and switch to it."""

    add_environment("stage", "https://stage", "orange", path=path or Path("environments.yaml"))
    url = switch_environment("stage", path=path or Path("environments.yaml"))
    return url
