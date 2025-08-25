"""DocReview360 core package."""

__all__ = [
    "placeholder",
    "cli",
    "plugins",
    "plugins_ui",
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
    "log_hash_chain",
    "exporter",
    "reporting",
    "archive",
    "deploy",
    "comments",
    "tiptap",
    "fts",
    "vector_search",
    "git_hooks",
    "rbac",
    "security_utils",
    "celery_app",
    "ai_utils",
    "ai_writer_assign",
    "monitoring",
    "hr_sync",
    "seeds",
    "watchlist",
    "contextual_help",
    "notifications",
    "plugins_ui",
    "project_init",
    "metabase",
    "alerts",
    "fed_numbering",
    "editor_loader",
    "onlyoffice_editor",
    "editor_switcher",
    "security_hardening",
    "fann_corpus",
    "fann_model",
    "wasm_plugin",
    "pyo3_builder",
    "workflow_components",
    "conversion",
    "nemo_guardrails",
    "GuardrailsMiddleware",
    "chat_bot",
    "migration",
    "login_gov",
    "piv_cac",
    "auth0_provider",
    "okta",
    "reviewer_model",
    "document_compare",
    "quality",
    "review_analytics",
    "integrity",
]


# Importing every submodule at package import time pulls in a large dependency
# tree.  Many of those dependencies (FastAPI, Celery, etc.) are optional and not
# required for the lightweight helper modules used in our tests.  Eagerly
# importing them causes ``ModuleNotFoundError`` during test collection.  To keep
# the public API intact while avoiding heavy imports, we expose submodules lazily
# via ``__getattr__``.  This mirrors the behaviour of packages like ``numpy`` or
# ``pandas`` where modules are loaded on first access.

import sys
from importlib import import_module
from typing import Any


def __getattr__(name: str) -> Any:
    """Dynamically import submodules on first access.

    This allows ``from docreview360 import chat_bot`` without importing the
    entire dependency graph when the package is initialised.
    """

    if name in __all__:
        module = import_module(f".{name}", __name__)
        setattr(sys.modules[__name__], name, module)
        return module
    raise AttributeError(f"module {__name__} has no attribute {name}")


def placeholder(multiplier: int = 1) -> int:
    """Return ``42`` multiplied by ``multiplier``."""

    if not isinstance(multiplier, int):
        raise TypeError("multiplier must be an integer")
    if multiplier < 0:
        raise ValueError("multiplier must be non-negative")

    return 42 * multiplier
