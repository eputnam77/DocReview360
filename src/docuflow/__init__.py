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
    "archive",
    "ai_utils",
    "monitoring",
]

from . import (
    ai_utils,
    api,
    approvals,
    archive,
    auth,
    cli,
    config,
    doc_types,
    documents,
    exporter,
    logs,
    models,
    monitoring,
    plugins,
    reporting,
    search,
    workflows,
)


def placeholder() -> int:
    """Return a constant used in placeholder tests."""
    return 42
