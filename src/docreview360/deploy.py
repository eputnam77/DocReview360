"""Deployment helpers for containerised environments."""

from __future__ import annotations


def normalize_port(port: int | str | None) -> int:
    """Return a valid TCP port number.

    Parameters
    ----------
    port:
        The raw port value, typically from ``$PORT`` or a CLI argument.

    Returns
    -------
    int
        ``port`` converted to an integer if possible. Negative or
        invalid values yield ``0`` so the caller can decide on a default.
    """
    try:
        value = int(port) if port is not None else 0
    except (TypeError, ValueError):
        return 0
    return value if value >= 0 else 0
