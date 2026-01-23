import importlib
import io
from types import SimpleNamespace

import pytest

from docreview360.object_storage import _validate_key, download_file, upload_file


def test_bucket_rejects_traversal_segments(tmp_path) -> None:
    with pytest.raises(ValueError):
        upload_file("../evil", "safe.txt", b"data")
    with pytest.raises(ValueError):
        upload_file("..\\evil", "safe.txt", b"data")
    with pytest.raises(ValueError):
        download_file("../evil", "safe.txt")


def test_bucket_rejects_newlines_and_whitespace() -> None:
    with pytest.raises(ValueError):
        upload_file(" bucket", "safe.txt", b"data")
    with pytest.raises(ValueError):
        upload_file("bucket\n", "safe.txt", b"data")


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


def test_rejects_leading_trailing_whitespace(tmp_path) -> None:
    bucket = tmp_path / "bucket"
    bucket.mkdir()
    with pytest.raises(ValueError):
        upload_file(bucket, " file.txt", b"data")
    with pytest.raises(ValueError):
        upload_file(bucket, "file.txt ", b"data")
    with pytest.raises(ValueError):
        _validate_key(" file.txt")


def test_s3_upload_download(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class Client:
        def get_object(self, Bucket, Key):
            return {"Body": io.BytesIO(b"data")}

        def put_object(self, Bucket, Key, Body, **extra):
            calls.update(extra)

    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: SimpleNamespace(client=lambda _: Client()),
    )

    assert download_file("s3://bucket", "key") == b"data"
    uri = upload_file("s3://bucket", "key", b"x", append_only=True, retention_days=2)
    assert uri == "s3://bucket/key"
    assert "ObjectLockRetainUntilDate" in calls


def test_s3_bucket_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: SimpleNamespace(client=lambda _: object()),
    )
    with pytest.raises(ValueError):
        download_file("s3://", "key")
    with pytest.raises(ValueError):
        upload_file("s3://bucket/path", "key", b"x")


def test_upload_retention_and_append(tmp_path):
    with pytest.raises(ValueError):
        upload_file(tmp_path, "k", b"d", retention_days=-1)
    bucket = tmp_path / "b"
    bucket.mkdir()
    (bucket / "f").write_text("x")
    with pytest.raises(FileExistsError):
        upload_file(bucket, "f", b"y", append_only=True)


def test_rejects_backslash_edges(tmp_path) -> None:
    bucket = tmp_path / "b"
    bucket.mkdir()
    # Leading or trailing backslashes should be treated as invalid
    with pytest.raises(ValueError):
        upload_file(bucket, "\\evil.txt", b"x")
    with pytest.raises(ValueError):
        upload_file(bucket, "dir\\", b"x")
    with pytest.raises(ValueError):
        _validate_key("\\evil.txt")
    with pytest.raises(ValueError):
        _validate_key("dir\\")
