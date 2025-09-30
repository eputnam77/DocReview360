# New tests for uncovered modules and bug fixes
import json
import hashlib
from types import SimpleNamespace
from pathlib import Path

import pytest

from docreview360 import backup_utils, email_templates, provider_store, object_storage, audit, doc_types, chat_bot
from docreview360.documents import DocumentModel, documents
from docreview360.logs import logs


def test_provider_store_invalid_yaml(tmp_path):
    cfg = tmp_path / "providers.yaml"
    cfg.write_text("- not a mapping")
    with pytest.raises(ValueError):
        provider_store.load_providers(cfg)


def test_provider_store_roundtrip_and_health(tmp_path):
    cfg = tmp_path / "providers.yaml"
    # Loading when file missing returns copy of defaults
    data = provider_store.load_providers(cfg)
    data["documenso"]["api_key"] = "x"
    provider_store.save_providers(data, cfg)
    # Health update persists
    provider_store.set_provider_health("documenso", False, cfg)
    loaded = provider_store.load_providers(cfg)
    assert loaded["documenso"]["healthy"] is False


def test_object_storage_validation(tmp_path):
    with pytest.raises(ValueError):
        object_storage.upload_file(tmp_path, "file.txt", b"data", retention_days=-1)
    path = object_storage.upload_file(tmp_path, "file.txt", b"data")
    with pytest.raises(FileExistsError):
        object_storage.upload_file(tmp_path, "file.txt", b"x", append_only=True)
    assert path.read_bytes() == b"data"


def test_backup_restore_invalid_base64(tmp_path):
    documents.clear(); logs.clear()
    doc = DocumentModel(id="1", content="text")
    documents[doc.id] = doc
    path = backup_utils.create_backup(tmp_path / "bkp.gz")
    import gzip
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    data["documents"][0]["yjs_updates"] = ["!"]  # invalid base64
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)
    with pytest.raises(ValueError):
        backup_utils.restore_backup(path)
    assert "1" in documents  # state preserved


def test_email_template_update_clear():
    email_templates.TEMPLATES.clear()
    email_templates.create_template("demo", "sub", "body", task="x")
    tmpl = email_templates.update_template("demo", task=None)
    assert tmpl.task is None
    with pytest.raises(ValueError):
        email_templates.create_template("demo", "s", "b")
    with pytest.raises(KeyError):
        email_templates.delete_template("missing")


def test_audit_log_and_hashing(tmp_path, monkeypatch):
    audit._AUDIT_LOG_PATH = tmp_path / "audit.log"
    audit._AUDIT_ANCHOR_PATH = tmp_path / "audit.anchor"
    audit.clear_audit_log()
    e1 = audit.log_audit_event("doc", "created", actor="a")
    e2 = audit.log_audit_event("doc", "updated", actor="b")
    entries = audit.get_audit_log("doc")
    assert [e.id for e in entries] == [e1.id, e2.id]
    single = audit.get_audit_entry(e1.id)
    assert single and single.event == "created"
    removed = audit.purge_audit_logs(retention_days=1)
    assert removed >= 0
    # Hashing uploads segments
    uploads = []
    monkeypatch.setattr(audit, "upload_file", lambda *a, **k: uploads.append(a))
    audit.hash_new_log_segments(bucket=tmp_path, prefix="anchor", segment_size=1, retention_days=1)
    assert uploads, "hash anchors not uploaded"
    with pytest.raises(ValueError):
        audit.hash_new_log_segments(segment_size=0)
    with pytest.raises(ValueError):
        audit.hash_new_log_segments(retention_days=-1)


def test_doc_type_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(doc_types, "DATA_FILE", tmp_path / "types.json")
    doc_types.document_types.clear()
    doc_types.save_state()
    # invalid rename to existing
    a = doc_types.DocumentTypeModel(name="A", template="t", workflow=["Phase"])
    b = doc_types.DocumentTypeModel(name="B", template="t", workflow=["Phase"])
    doc_types.add_document_type(a)
    doc_types.add_document_type(b)
    with pytest.raises(ValueError):
        doc_types.update_document_type(
            "A",
            doc_types.DocumentTypeModel(name="B", template="t", workflow=["Phase"]),
        )
    # export to directory
    with pytest.raises(ValueError):
        doc_types.export_document_types(tmp_path)
    # invalid JSON import
    with pytest.raises(ValueError):
        doc_types.import_document_types_json("{}")


def test_chat_bot_helpers(monkeypatch):
    cb = chat_bot
    cb.projects.clear()
    cb.workflows.clear()
    cb.document_types.clear()
    monkeypatch.setattr(cb, "overdue_high_priority", lambda: [])
    proj = SimpleNamespace(temp_user=None, user="alice", status="Draft", workflow=None)
    cb.projects["p1"] = proj
    assert cb._assignment_question("who is assigned to project p1") == "alice is assigned to p1."
    assert cb._status_question("status of project p1") == "p1 is currently in the draft phase."
    assert cb._workload_question("what is workload for alice") == "alice has 1 project assigned."
    assert cb._overdue_question("any overdue high priority projects?") == "There are no overdue high priority projects."
    assert cb._template_list_question("list templates")
    assert "No document types" in cb._document_type_question("document types available")
    assert "general document template" in cb._template_question("which template to use for unknown")


def test_certs_fetch_certificate(tmp_path):
    from docreview360 import certs
    certs.clear_cache()
    cert_path = tmp_path / "cert.pem"
    cert_path.write_bytes(b"data")
    host = "example.com"
    fp = hashlib.sha256(b"data").hexdigest()
    certs.register_pinned_chain(host, fp)
    url = f"https://{host}/cert.pem"
    def fetcher(u):
        assert u == url
        return b"data"
    first = certs.fetch_certificate(url, fetcher=fetcher)
    second = certs.fetch_certificate(url, fetcher=fetcher)
    assert first == second == b"data"
    with pytest.raises(ValueError):
        certs.fetch_certificate("http://insecure/cert.pem", fetcher=fetcher)
    with pytest.raises(ValueError):
        certs.fetch_certificate(f"https://{host}/other.pem", fetcher=lambda u: b"x")
