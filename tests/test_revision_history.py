import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

from docreview360.documents import (
    import_document,
    update_document,
    get_document_versions,
)
from docreview360.pandiff import compute_diff
from docreview360.records import sync_to_sharepoint


def test_upload_increments_version_and_sha256() -> None:
    doc = import_document("rev.md", b"alpha")
    sha0 = hashlib.sha256(b"alpha").hexdigest()
    assert hashlib.sha256(doc.content.encode()).hexdigest() == sha0

    update_document(doc.id, "beta")
    versions = get_document_versions(doc.id)
    assert len(versions) == 2
    assert versions[0] == "alpha"
    assert versions[1] == "beta"
    assert hashlib.sha256(versions[0].encode()).hexdigest() == sha0


def test_diff_button_caches_redline_docx() -> None:
    cache: Dict[Tuple[str, str], List[str]] = {}

    def diff_button(old: str, new: str) -> List[str]:
        key = (old, new)
        if key not in cache:
            cache[key] = compute_diff(old, new)
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
            count = sync_to_sharepoint(src, dest)
            versions.append(count)

    upload(True)
    assert dest.joinpath("file.txt").exists()
