"""DocuFlow core package."""

__all__ = [
    "placeholder",
    "cli",
    "plugins",
    "models",
    "api",
    "auth",
    "doc_types",
    "documents",
]

from . import api, auth, cli, doc_types, documents, models, plugins


def placeholder() -> int:
    """Return a constant used in placeholder tests."""
    return 42
