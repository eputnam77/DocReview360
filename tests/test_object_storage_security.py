import pytest

from docreview360.object_storage import download_file, upload_file


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

