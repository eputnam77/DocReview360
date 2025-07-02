"""DocuFlow core package."""

__all__ = ["placeholder", "cli", "plugins", "models", "api", "auth"]

from . import api, auth, cli, models, plugins


def placeholder() -> int:
    """Return a constant used in placeholder tests."""
    return 42
