"""DocuFlow core package."""

__all__ = [
    "placeholder",
    "cli",
    "plugins",
    "models",
    "api",
    "auth",
    "config",
    "doc_types",
    "documents",
    "search",
    "workflows",
]

from . import (
    api,
    auth,
    cli,
    config,
    doc_types,
    documents,
    models,
    plugins,
    search,
    workflows,
)


def placeholder() -> int:
    """Return a constant used in placeholder tests."""
    return 42
