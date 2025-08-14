"""Revision history and SharePoint integration tests."""

import hashlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Dict, List, Tuple

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "docreview360"
pkg = types.ModuleType("docreview360")
pkg.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("docreview360", pkg)

# Load required modules explicitly to avoid executing package __init__

def _load(name: str, file: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, PACKAGE_DIR / file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


documents = _load("docreview360.documents", "documents.py")
pandiff = _load("docreview360.pandiff", "pandiff.py")
records = _load("docreview360.records", "records.py")

import_document = documents.import_document
update_document = documents.update_document
get_document_versions = documents.get_document_versions


def test_upload_increments_version_and_sha256() -> None:
    doc = import_document("rev.md", b"alpha")
    sha0 = hashlib.sha256(b"alpha").hexdigest()
    assert hashlib.sha256(doc.content.encode()).hexdigest() == sha0

    update_document(doc.id, "beta")
    versions = get_document_versions(doc.id)
    assert len(versions) == 1
    assert versions[0] == "alpha"
    assert hashlib.sha256(versions[0].encode()).hexdigest() == sha0

    update_document(doc.id, "gamma")
    versions = get_document_versions(doc.id)
    assert len(versions) == 2
    assert hashlib.sha256(versions[1].encode()).hexdigest() == hashlib.sha256(b"beta").hexdigest()


def test_diff_button_caches_redline_docx() -> None:
    cache: Dict[Tuple[str, str], List[str]] = {}

    def diff_button(old: str, new: str) -> List[str]:
        key = (old, new)
        if key not in cache:
            cache[key] = pandiff.compute_diff(old, new)
        return cache[key]

    first = diff_button("one", "two")
    second = diff_button("one", "two")
    assert first == second
    assert len(cache) == 1


def test_sharepoint_toggle_records_version(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("hello")
    dest = tmp_path / "sp"
    versions: List[int] = []

    def upload(toggle: bool) -> None:
        if toggle:
            count = records.sync_to_sharepoint(src, dest)
            versions.append(count)

    upload(True)
    assert dest.joinpath("file.txt").exists()
    assert versions == [1]


def test_restore_draft_replaces_document_and_logs_new_version() -> None:
    doc = import_document("restore.md", b"v0")
    update_document(doc.id, "v1")
    update_document(doc.id, "v2")
    versions = get_document_versions(doc.id)
    assert versions == ["v0", "v1"]

    doc = update_document(doc.id, versions[1])  # restore draft 2
    versions = get_document_versions(doc.id)
    assert doc.content == "v1"
    assert len(versions) == 3
    assert len(versions) + 1 == 4
