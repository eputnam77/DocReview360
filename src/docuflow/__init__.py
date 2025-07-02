"""DocuFlow core package."""

__all__ = ["placeholder", "cli", "plugins", "models", "api"]

from . import api, cli, models, plugins


def placeholder() -> int:
    """Return a constant used in placeholder tests."""
    return 42
