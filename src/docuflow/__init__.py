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
    "tiptap",
    "fts",
    "vector_search",
    "rbac",
    "security_utils",
    "celery_app",
    "ai_utils",
    "monitoring",
]

from . import (
    ai_utils,
    api,
    approvals,
    archive,
    auth,
    celery_app,
    cli,
    comments,
    config,
    doc_types,
    documents,
    exporter,
    fts,
    logs,
    models,
    monitoring,
    plugins,
    rbac,
    reporting,
    search,
    security_utils,
    tiptap,
    vector_search,
    workflows,
)


def placeholder() -> int:
    """Return a constant used in placeholder tests."""
    return 42
