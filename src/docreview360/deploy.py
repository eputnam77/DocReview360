"""Deployment helpers for containerised environments."""

from __future__ import annotations


def normalize_port(port: int | str | float | None) -> int:
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
        # ``int`` will happily truncate floats (e.g. ``123.5`` -> ``123``) which
        # is rarely the desired behavior for port numbers. Treat non-integer
        # floats as invalid so callers don't accidentally bind to an unexpected
        # port when a decimal value is supplied.
        if isinstance(port, float) and not port.is_integer():
            return 0
        value = int(port) if port is not None else 0
    except (TypeError, ValueError):
        return 0
    if not 0 <= value <= 65535:
        return 0
    return value
