# SPDX-License-Identifier: MIT
"""Document versioning — history, restore, freeze/unfreeze, diff."""

from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from ..audit import log_audit_event
from ._models import FrozenDocumentError, documents
from ._store import update_document


def get_document_versions(doc_id: str) -> list[str]:
    """Return the list of all versions for ``doc_id``."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    return [rev.content for rev in document.history]


def get_document_version(doc_id: str, index: int) -> str:
    """Return a specific version for ``doc_id``."""
    versions = get_document_versions(doc_id)
    if index < 0 or index >= len(versions):
        raise IndexError("version index out of range")
    return versions[index]


def get_version_history(doc_id: str) -> list[dict[str, Any]]:
    """Return rich version history metadata for ``doc_id``."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    history: list[dict[str, Any]] = []
    base_version = document.version_number - len(document.history) + 1
    for i, rev in enumerate(document.history):
        history.append(
            {
                "revision_id": rev.id,
                "version_number": max(1, base_version + i),
                "timestamp": rev.timestamp.isoformat(),
                "author": rev.author,
                "content_length": len(rev.content),
            }
        )
    return history


def restore_document_version(
    doc_id: str, revision_id: str, author: str | None = None
) -> Any:
    """Restore ``doc_id`` content to the revision identified by ``revision_id``."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    if document.frozen:
        raise FrozenDocumentError(
            f"Document '{doc_id}' is frozen. Unfreeze it before restoring."
        )
    target = next((r for r in document.history if r.id == revision_id), None)
    if target is None:
        raise KeyError(f"Revision '{revision_id}' not found in document '{doc_id}'")
    doc, _ = update_document(doc_id, target.content, author=author)
    log_audit_event(doc_id, "version_restored", revision_id=revision_id, actor=author)
    return doc


def freeze_document(doc_id: str) -> Any:
    """Freeze ``doc_id`` so its content can no longer be changed."""
    from ._models import document_lock

    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    with document_lock:
        document.frozen = True
    log_audit_event(doc_id, "version_frozen")
    return document


def unfreeze_document(doc_id: str) -> Any:
    """Lift the freeze on ``doc_id``, allowing content changes again."""
    from ._models import document_lock

    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    with document_lock:
        document.frozen = False
    log_audit_event(doc_id, "version_unfrozen")
    return document


def diff_document_revisions(
    doc_id: str,
    revision_id_a: str,
    revision_id_b: str,
) -> dict[str, Any]:
    """Return a unified-diff and per-line change breakdown between two revisions."""
    import difflib as _difflib

    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")

    base_version = document.version_number - len(document.history) + 1

    def _find_revision(rev_id: str) -> tuple[str, dict[str, Any]]:
        if rev_id == "current":
            latest = document.history[-1] if document.history else None
            meta: dict[str, Any] = {
                "id": "current",
                "version_number": document.version_number,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "author": latest.author if latest else None,
            }
            return document.content, meta
        for i, rev in enumerate(document.history):
            if rev.id == rev_id:
                meta = {
                    "id": rev.id,
                    "version_number": max(1, base_version + i),
                    "timestamp": rev.timestamp.isoformat(),
                    "author": rev.author,
                }
                return rev.content, meta
        raise KeyError(f"Revision '{rev_id}' not found in document '{doc_id}'")

    content_a, meta_a = _find_revision(revision_id_a)
    content_b, meta_b = _find_revision(revision_id_b)

    lines_a = content_a.splitlines()
    lines_b = content_b.splitlines()

    unified = list(
        _difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=f"revision/{revision_id_a}",
            tofile=f"revision/{revision_id_b}",
            lineterm="",
        )
    )

    added = sum(1 for ln in unified if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in unified if ln.startswith("-") and not ln.startswith("---"))
    ratio = SequenceMatcher(None, content_a, content_b).ratio()

    return {
        "unified_diff": unified,
        "lines_added": added,
        "lines_removed": removed,
        "similarity_ratio": round(ratio, 4),
        "revision_a": meta_a,
        "revision_b": meta_b,
    }
