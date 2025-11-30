import tempfile

import pytest

from docreview360.records_keeper import create_archival_folder


def test_create_archival_folder_rejects_whitespace_id():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError):
            create_archival_folder(tmp, "   ")


def test_create_archival_folder_rejects_path_traversal():
    """Project identifiers must not escape the base directory."""
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError):
            create_archival_folder(tmp, "../secret")
        with pytest.raises(ValueError):
            create_archival_folder(tmp, "a/b")


def test_create_archival_folder_success(tmp_path):
    folder = create_archival_folder(tmp_path, "project")
    assert folder.is_dir()
    # Folder should be nested under base/project/date
    assert folder.parent.parent == tmp_path


def test_create_archival_folder_strips_whitespace(tmp_path):
    """Leading/trailing whitespace in project ids should be ignored."""
    folder = create_archival_folder(tmp_path, "  spaced  ")
    assert folder.parent.parent == tmp_path
    assert folder.parent.name == "spaced"
