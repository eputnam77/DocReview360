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
    "approvals",
    "logs",
    "exporter",
    "reporting",
]

from . import (
    api,
    approvals,
    auth,
    cli,
    config,
    doc_types,
    documents,
    exporter,
    logs,
    models,
    plugins,
    reporting,
    search,
    workflows,
)


def placeholder() -> int:
    """Return a constant used in placeholder tests."""
    return 42
