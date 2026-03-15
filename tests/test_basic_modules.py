from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from docreview360 import archive, config, documents, logs, workflows


def test_config_roundtrip(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("DOCREVIEW360_DATABASE_URL", raising=False)
    cfg = config.Config(database="sqlite", editor="tiptap", cms="md", auth="none")
    cfg.save(tmp_path / "cfg.yaml")
    loaded = config.Config.load(tmp_path / "cfg.yaml")
    assert loaded == cfg


def test_config_load_missing(tmp_path: Path) -> None:
    assert config.Config.load(tmp_path / "none.yaml") is None


def test_config_invalid(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("[1]")
    with pytest.raises(ValueError):
        config.Config.load(bad)


def test_log_event_listener() -> None:
    captured = []
    logs.register_listener(captured.append)
    event = logs.log_event("create", user_id="alice")
    logs.unregister_listener(captured.append)
    assert event in captured


def test_workflow_lifecycle(tmp_path: Path) -> None:
    wf = workflows.create_workflow("p1", ["draft", "review"])
    workflows.assign_reviewer(wf.id, "alice")
    wf = workflows.advance_workflow(wf.id)
    assert wf.phase == "review"
    workflows.start_workflow(wf.id, "doc.md", b"hello")
    assert workflows.get_workflow(wf.id) is not None


def test_archive_document(monkeypatch: MonkeyPatch) -> None:
    doc = documents.DocumentModel(id="d1", content="hi")
    monkeypatch.setattr(archive, "upload_file", lambda *a, **k: None)
    record = archive.archive_document(doc)
    assert record.document_id == "d1"
