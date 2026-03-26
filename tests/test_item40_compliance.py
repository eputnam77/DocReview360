# SPDX-License-Identifier: MIT
"""Tests for Item 40: compliance, records management, and accessibility."""
from __future__ import annotations

import json
import os
import tempfile

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


# ---------------------------------------------------------------------------
# NARA metadata tests
# ---------------------------------------------------------------------------


class TestNaraMetadata:
    def _setup_doc(self, db, suffix=""):
        from docreview360.doc_types import list_document_types
        from docreview360.models import Document, Project

        dt_id = list_document_types()[0].id
        proj = Project(name=f"NaraProject{suffix}", document_type_id=dt_id)
        db.add(proj)
        db.flush()
        doc_id = f"nara-doc-{suffix}"
        doc = Document(id=doc_id, project_id=proj.id, content="Test")
        db.add(doc)
        db.flush()
        return doc_id

    def test_set_and_get(self):
        from docreview360.db_store import get_db
        from docreview360.nara_metadata import get_nara_metadata, set_nara_metadata

        with get_db().orm_session() as db:
            doc_id = self._setup_doc(db, "001")
            meta = set_nara_metadata(
                db,
                doc_id,
                schedule_number="DAA-0049-2019-0001",
                retention_period="7 years",
                vital_record=True,
                record_status="active",
            )
            assert meta.schedule_number == "DAA-0049-2019-0001"
            assert meta.vital_record is True

            fetched = get_nara_metadata(db, doc_id)
            assert fetched is not None
            assert fetched.retention_period == "7 years"

    def test_upsert_updates_existing(self):
        from docreview360.db_store import get_db
        from docreview360.nara_metadata import set_nara_metadata

        with get_db().orm_session() as db:
            doc_id = self._setup_doc(db, "002")
            set_nara_metadata(db, doc_id, retention_period="3 years")
            updated = set_nara_metadata(db, doc_id, retention_period="10 years")
            assert updated.retention_period == "10 years"

    def test_delete_nara_metadata(self):
        from docreview360.db_store import get_db
        from docreview360.nara_metadata import (
            delete_nara_metadata,
            get_nara_metadata,
            set_nara_metadata,
        )

        with get_db().orm_session() as db:
            doc_id = self._setup_doc(db, "003")
            set_nara_metadata(db, doc_id, vital_record=False)
            deleted = delete_nara_metadata(db, doc_id)
            assert deleted is True
            assert get_nara_metadata(db, doc_id) is None

    def test_list_vital_records(self):
        from docreview360.db_store import get_db
        from docreview360.doc_types import list_document_types
        from docreview360.models import Document, Project
        from docreview360.nara_metadata import list_vital_records, set_nara_metadata

        with get_db().orm_session() as db:
            dt_id = list_document_types()[0].id
            proj = Project(name="NaraVitalProject", document_type_id=dt_id)
            db.add(proj)
            db.flush()
            for i in range(3):
                doc = Document(id=f"vital-doc-{i}", project_id=proj.id, content="Test")
                db.add(doc)
            db.flush()
            set_nara_metadata(db, "vital-doc-0", vital_record=True)
            set_nara_metadata(db, "vital-doc-1", vital_record=False)
            set_nara_metadata(db, "vital-doc-2", vital_record=True)

            vitals = list_vital_records(db)
            vital_ids = [v.document_id for v in vitals]
            assert "vital-doc-0" in vital_ids
            assert "vital-doc-2" in vital_ids
            assert "vital-doc-1" not in vital_ids


# ---------------------------------------------------------------------------
# Legal hold tests
# ---------------------------------------------------------------------------


class TestLegalHold:
    def _setup_doc(self, db, suffix=""):
        from docreview360.doc_types import list_document_types
        from docreview360.models import Document, Project

        dt_id = list_document_types()[0].id
        proj = Project(name=f"LegalProject{suffix}", document_type_id=dt_id)
        db.add(proj)
        db.flush()
        doc_id = f"legal-doc-{suffix}"
        doc = Document(id=doc_id, project_id=proj.id, content="Test")
        db.add(doc)
        db.flush()
        return doc_id

    def test_create_hold(self):
        from docreview360.db_store import get_db
        from docreview360.legal_hold import create_legal_hold, get_legal_hold

        with get_db().orm_session() as db:
            hold = create_legal_hold(db, "Test Hold", "Litigation", "alice")
            assert hold.hold_name == "Test Hold"
            assert hold.status == "active"
            fetched = get_legal_hold(db, hold.id)
            assert fetched is not None

    def test_add_remove_document(self):
        from docreview360.db_store import get_db
        from docreview360.legal_hold import (
            add_document_to_hold,
            create_legal_hold,
            is_document_on_hold,
            remove_document_from_hold,
        )

        with get_db().orm_session() as db:
            doc_id = self._setup_doc(db, "add-rem")
            hold = create_legal_hold(db, "Add/Remove Hold", None, "alice")
            add_document_to_hold(db, hold.id, doc_id, added_by="alice")
            assert is_document_on_hold(db, doc_id) is True

            removed = remove_document_from_hold(db, hold.id, doc_id)
            assert removed is True
            assert is_document_on_hold(db, doc_id) is False

    def test_release_hold(self):
        from docreview360.db_store import get_db
        from docreview360.legal_hold import create_legal_hold, release_hold

        with get_db().orm_session() as db:
            hold = create_legal_hold(db, "Release Hold", None, "alice")
            released = release_hold(db, hold.id, "alice")
            assert released.status == "released"
            assert released.released_by == "alice"

    def test_is_document_on_hold_false(self):
        from docreview360.db_store import get_db
        from docreview360.legal_hold import is_document_on_hold

        with get_db().orm_session() as db:
            assert is_document_on_hold(db, "nonexistent-doc") is False

    def test_list_legal_holds_filter(self):
        from docreview360.db_store import get_db
        from docreview360.legal_hold import create_legal_hold, list_legal_holds, release_hold

        with get_db().orm_session() as db:
            h1 = create_legal_hold(db, "Active Hold", None, "alice")
            h2 = create_legal_hold(db, "Released Hold", None, "alice")
            release_hold(db, h2.id, "alice")

            active = list_legal_holds(db, status="active")
            active_ids = [h.id for h in active]
            assert h1.id in active_ids
            assert h2.id not in active_ids


# ---------------------------------------------------------------------------
# eDiscovery export tests
# ---------------------------------------------------------------------------


class TestEDiscovery:
    def test_export_creates_zip(self):
        import zipfile

        from docreview360.db_store import get_db
        from docreview360.ediscovery import export_ediscovery

        with get_db().orm_session() as db:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp_path = tmp.name

            result = export_ediscovery(
                db,
                document_ids=["ediscovery-doc-001", "ediscovery-doc-002"],
                output_path=tmp_path,
                include_audit=True,
                exported_by="alice",
            )

        assert result["exported"] == 2
        assert result["file_path"] == tmp_path
        assert result["size_bytes"] > 0

        with zipfile.ZipFile(tmp_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert any("ediscovery-doc-001" in n for n in names)

        os.unlink(tmp_path)

    def test_export_manifest_content(self):
        import zipfile

        from docreview360.db_store import get_db
        from docreview360.ediscovery import export_ediscovery

        with get_db().orm_session() as db:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp_path = tmp.name

            export_ediscovery(
                db,
                document_ids=["manifest-doc-001"],
                output_path=tmp_path,
                exported_by="bob",
            )

        with zipfile.ZipFile(tmp_path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["exported_by"] == "bob"
            assert "manifest-doc-001" in manifest["documents"]

        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Accessibility scan tests
# ---------------------------------------------------------------------------


class TestAccessibilityScan:
    def test_scan_clean_html(self):
        from docreview360.accessibility import scan_document_accessibility

        html = '<html lang="en"><h1>Title</h1><img src="x.png" alt="logo"><p>Text</p></html>'
        result = scan_document_accessibility(html, "doc-001")
        assert result.score == 100
        assert len(result.violations) == 0

    def test_scan_missing_alt_text(self):
        from docreview360.accessibility import scan_document_accessibility

        html = '<html lang="en"><img src="photo.jpg"></html>'
        result = scan_document_accessibility(html, "doc-002")
        criteria = [v.criterion for v in result.violations]
        assert "WCAG 1.1.1" in criteria
        assert result.score < 100

    def test_scan_returns_score_and_dict(self):
        from docreview360.accessibility import scan_document_accessibility, scan_result_to_dict

        html = "<html><img src='a.png'><a href='#'></a></html>"
        result = scan_document_accessibility(html, "doc-003")
        d = scan_result_to_dict(result)
        assert "score" in d
        assert "violations" in d
        assert "passes" in d
        assert isinstance(d["violations"], list)

    def test_scan_empty_link(self):
        from docreview360.accessibility import scan_document_accessibility

        html = '<html lang="en"><a href="/about">   </a></html>'
        result = scan_document_accessibility(html, "doc-004")
        criteria = [v.criterion for v in result.violations]
        assert "WCAG 2.4.4" in criteria

    def test_scan_heading_skip(self):
        from docreview360.accessibility import scan_document_accessibility

        html = '<html lang="en"><h1>Main</h1><h3>Skipped</h3></html>'
        result = scan_document_accessibility(html, "doc-005")
        criteria = [v.criterion for v in result.violations]
        assert "WCAG 1.3.1" in criteria


# ---------------------------------------------------------------------------
# Admin audit completeness endpoint
# ---------------------------------------------------------------------------


class TestAuditCompletenessEndpoint:
    def test_audit_completeness_returns_ok(self, monkeypatch):
        import docreview360.logs as logs_mod
        from docreview360 import auth, rbac
        from docreview360.api import app
        from fastapi.testclient import TestClient

        monkeypatch.setattr(
            logs_mod,
            "verify_audit_log_chain",
            lambda: {"ok": True, "total_entries": 5, "message": "Chain intact"},
        )

        client = TestClient(app)
        # Use demo user "alice" (password="password", already seeded in dev mode)
        try:
            auth.create_user("alice", "password")
        except Exception:
            pass
        rbac.add_role("alice", "admin")
        token_resp = client.post(
            "/token", data={"username": "alice", "password": "password"}
        )
        assert token_resp.status_code == 200, token_resp.text
        token = token_resp.json()["access_token"]

        resp = client.get(
            "/admin/audit/completeness",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ok"] is True
