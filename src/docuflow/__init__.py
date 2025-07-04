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
    "comments",
    "rbac",
    "security_utils",
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
    comments,
    config,
    doc_types,
    documents,
    exporter,
    logs,
    models,
    monitoring,
    plugins,
    rbac,
    reporting,
    search,
    security_utils,
    workflows,
)


def placeholder() -> int:
    """Return a constant used in placeholder tests."""
    return 42
