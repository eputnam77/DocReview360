"""Tests for the document type persistence feature flag."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest

import docreview360.doc_types as doc_types_module


def _restore_module(original_cwd: Path, monkeypatch) -> None:
    """Reload the module with persistence enabled and original cwd."""

    os.chdir(original_cwd)
    monkeypatch.setenv("DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", "1")
    importlib.reload(doc_types_module)


def test_import_without_persistence_does_not_write(tmp_path, monkeypatch):
    """Importing with persistence disabled should not touch the JSON file."""

    original_cwd = Path.cwd()
    monkeypatch.setenv("DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", "0")
    monkeypatch.chdir(tmp_path)
    module = importlib.reload(doc_types_module)
    try:
        assert module.DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE is False
        assert module.list_document_types(), "Bootstrap should still populate defaults in memory"
        assert not (tmp_path / "document_types.json").exists()
    finally:
        _restore_module(original_cwd, monkeypatch)


def test_import_with_persistence_writes_file(tmp_path, monkeypatch):
    """Importing with persistence enabled should create the JSON file."""

    original_cwd = Path.cwd()
    monkeypatch.setenv("DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", "1")
    monkeypatch.chdir(tmp_path)
    module = importlib.reload(doc_types_module)
    try:
        data_file = tmp_path / "document_types.json"
        assert data_file.exists(), "Bootstrap should write defaults when persistence is enabled"
        payload = json.loads(data_file.read_text())
        entries = payload.get("document_types", payload) if isinstance(payload, dict) else payload
        assert isinstance(entries, list)
        assert entries, "Persisted payload should include default document types"
    finally:
        _restore_module(original_cwd, monkeypatch)


def test_persistence_disabled_emits_warning(tmp_path, monkeypatch):
    """Disabling persistence should raise a runtime warning on import."""

    original_cwd = Path.cwd()
    monkeypatch.setenv("DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", "0")
    monkeypatch.chdir(tmp_path)
    with pytest.warns(RuntimeWarning, match="will not be saved"):
        module = importlib.reload(doc_types_module)
    try:
        assert module.DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE is False
    finally:
        _restore_module(original_cwd, monkeypatch)
