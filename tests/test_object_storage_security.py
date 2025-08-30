import pytest
from docreview360.object_storage import _validate_key, download_file, upload_file


def test_upload_rejects_path_traversal(tmp_path):
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    with pytest.raises(ValueError):
        upload_file(bucket, "../evil.txt", b"data")
    with pytest.raises(ValueError):
        upload_file(bucket, "sub/../evil.txt", b"data")


def test_download_rejects_path_traversal(tmp_path):
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(ValueError):
        download_file(bucket, "../secret.txt")


def test_validate_rejects_windows_style(tmp_path) -> None:
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    with pytest.raises(ValueError):
        upload_file(bucket, "..\\evil.txt", b"data")
    with pytest.raises(ValueError):
        _validate_key("..\\evil.txt")


def test_rejects_drive_specifier_anywhere(tmp_path) -> None:
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    # A colon in later path segments should be rejected to prevent Windows
    # drive specifiers sneaking into file names.
    with pytest.raises(ValueError):
        upload_file(bucket, "safe/C:evil.txt", b"data")


def test_rejects_empty_path_segment(tmp_path) -> None:
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    with pytest.raises(ValueError):
        upload_file(bucket, "a//b", b"data")
    with pytest.raises(ValueError):
        _validate_key("a//b")


def test_rejects_dot_segments(tmp_path) -> None:
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    with pytest.raises(ValueError):
        upload_file(bucket, "a/./b", b"data")
    with pytest.raises(ValueError):
        _validate_key("a/./b")


def test_rejects_newlines_and_null_bytes(tmp_path) -> None:
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    with pytest.raises(ValueError):
        upload_file(bucket, "evil\n.txt", b"data")
    with pytest.raises(ValueError):
        upload_file(bucket, "evil\r.txt", b"data")
    with pytest.raises(ValueError):
        _validate_key("evil\n.txt")
    with pytest.raises(ValueError):
        _validate_key("nul\x00.txt")

