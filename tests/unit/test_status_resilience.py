import docreview360.documents as docs
import docreview360.search as search
import docreview360.status as status
import docreview360.workflows as wf


def test_public_status_handles_missing(monkeypatch):
    monkeypatch.setattr(search, "projects", None)
    monkeypatch.setattr(docs, "documents", None)
    assert status.public_status() == {"projects": 0, "documents": 0}


def test_internal_status_handles_unsized(monkeypatch):
    monkeypatch.setattr(wf, "workflows", object())
    # ensure public counts unaffected by patch
    res = status.internal_status()
    assert res["workflows"] == 0
