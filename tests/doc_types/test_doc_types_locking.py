from __future__ import annotations

import importlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

import docreview360.doc_types as original_doc_types


@pytest.fixture
def doc_types(tmp_path, monkeypatch):
    """Provide an isolated doc_types module bound to a temporary persistence file."""

    monkeypatch.setenv("DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", "0")
    module = importlib.reload(original_doc_types)
    monkeypatch.setattr(module, "DATA_FILE", tmp_path / "document_types.json")
    monkeypatch.setattr(module, "DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE", True)
    module.document_types.clear()
    module._STATE_VERSION = 0
    module._STATE_UPDATED_AT = None
    yield module
    monkeypatch.undo()
    importlib.reload(module)


def test_concurrent_save_raises_stale_error(doc_types, monkeypatch):
    doc_a = doc_types.DocumentTypeModel(name="TypeA", template="", workflow=["Phase"])
    doc_b = doc_types.DocumentTypeModel(name="TypeB", template="", workflow=["Phase"])

    original_atomic = doc_types._atomic_write
    write_started = threading.Event()
    release_write = threading.Event()

    def delayed_atomic(path, data):
        if not write_started.is_set():
            write_started.set()
            assert release_write.wait(timeout=5), "Timed out waiting to release write lock"
        original_atomic(path, data)

    monkeypatch.setattr(doc_types, "_atomic_write", delayed_atomic)

    def worker(model):
        return doc_types.add_document_type(model)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_first = executor.submit(worker, doc_a)
        assert write_started.wait(timeout=5), "Writer did not start in time"
        future_second = executor.submit(worker, doc_b)
        release_write.set()
        added = future_first.result()
        with pytest.raises(doc_types.StaleStateError):
            future_second.result()

    assert doc_types.get_document_type(doc_a.name) is added
    assert doc_types.get_document_type(doc_b.name) is None
    assert doc_types._STATE_VERSION == 1

    payload = json.loads(doc_types.DATA_FILE.read_text())
    assert payload["version"] == 1
    names = {item["name"] for item in payload["document_types"]}
    assert names == {doc_a.name}


def test_stale_state_detection_on_external_change(doc_types):
    first = doc_types.DocumentTypeModel(name="Persisted", template="", workflow=["Phase"])
    doc_types.add_document_type(first)
    expected_version = doc_types._STATE_VERSION

    external_payload = {
        "version": expected_version + 1,
        "updated_at": "2024-01-01T00:00:00Z",
        "document_types": [
            {"name": "External", "template": "", "workflow": ["Phase"]},
        ],
    }
    doc_types._atomic_write(doc_types.DATA_FILE, json.dumps(external_payload, indent=2))

    stale = doc_types.DocumentTypeModel(name="Stale", template="", workflow=["Phase"])
    doc_types.document_types[stale.name] = stale

    with pytest.raises(doc_types.StaleStateError) as excinfo:
        doc_types.save_state(expected_version=expected_version)

    assert "Reload" in str(excinfo.value)
    assert doc_types._STATE_VERSION == expected_version

    payload = json.loads(doc_types.DATA_FILE.read_text())
    names = {item["name"] for item in payload["document_types"]}
    assert names == {"External"}
