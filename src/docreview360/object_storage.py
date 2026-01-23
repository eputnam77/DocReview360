"""Lightweight file-based object storage plug-in."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath


def _validate_key(key: str) -> None:
    """Raise :class:`ValueError` if ``key`` attempts path traversal.

    The original implementation only relied on :class:`pathlib.Path` to split the
    key which meant Windows-style separators (``"\\"``) were treated as normal
    characters on POSIX systems.  As a result a key like ``"..\\secret"`` would
    bypass the ``".."`` check and could be interpreted as a parent directory on a
    Windows host.  Normalizing separators ensures traversal attempts are caught
    consistently across platforms.
    """

    if not key or key.startswith("/") or key.endswith("/"):
        raise ValueError("invalid key")
    # Leading or trailing spaces can produce confusing files that are hard to
    # reference later. Treat such keys as invalid early.
    if key != key.strip():
        raise ValueError("invalid key")

    normalized = key.replace("\\", "/")
    # After normalizing Windows separators ensure the key still isn't absolute
    # or pointing to a directory via a trailing slash.
    if normalized.startswith("/") or normalized.endswith("/"):
        raise ValueError("invalid key")
    # Newline or null bytes in paths can lead to log injection or truncation
    # issues on some filesystems. Treat such keys as invalid early.
    if any(c in normalized for c in ("\n", "\r", "\x00")):
        raise ValueError("invalid key")
    # Reject empty path segments to prevent ambiguous or accidental absolute
    # paths.  ``PurePosixPath`` collapses consecutive separators so we detect
    # them before normalization.
    if "//" in normalized:
        raise ValueError("invalid key")
    if (
        normalized == "."
        or "/./" in normalized
        or normalized.startswith("./")
        or normalized.endswith("/.")
    ):
        raise ValueError("invalid key")
    parts = PurePosixPath(normalized).parts
    # ``PurePosixPath`` does not treat ``":"`` specially so a key like
    # ``"safe/C:secret"`` would previously pass validation even though it
    # contains a Windows drive specifier.  Reject keys containing a colon in
    # *any* segment to avoid platform specific path tricks.
    if ":" in normalized or ".." in parts or "." in parts:
        raise ValueError("invalid key")


def _sanitize_bucket(bucket: str | Path) -> Path:
    """Return a normalized, absolute path for ``bucket``.

    The storage helpers accept either :class:`str` or :class:`pathlib.Path`
    instances for the ``bucket`` parameter.  Historically we simply wrapped the
    value in :class:`Path` which meant inputs such as ``"../etc"`` or
    ``"..\\etc"`` would happily traverse outside the intended storage root.
    Normalising separators and rejecting ``".."`` segments prevents directory
    traversal via the ``bucket`` argument itself.  The resulting path is always
    absolute to avoid ambiguity about where files are written on disk.
    """

    bucket_text = str(bucket)
    if not bucket_text:
        raise ValueError("invalid bucket")
    if bucket_text != bucket_text.strip():
        raise ValueError("invalid bucket")
    if any(ch in bucket_text for ch in ("\n", "\r", "\x00")):
        raise ValueError("invalid bucket")

    normalized = bucket_text.replace("\\", "/")
    # ``PurePosixPath`` gives us a stable representation regardless of the host
    # OS so we can reliably detect traversal segments like ``..`` even on
    # Windows when users pass in backslash-separated paths.
    if any(part == ".." for part in PurePosixPath(normalized).parts):
        raise ValueError("invalid bucket")

    bucket_path = Path(bucket_text).expanduser()
    # ``Path.resolve`` with ``strict=False`` collapses ``.`` segments and
    # returns an absolute path without requiring the directory to exist yet.
    return bucket_path.resolve()


def download_file(bucket: str | Path, key: str) -> bytes:
    """Return the contents of ``bucket``/``key``.

    Parameters
    ----------
    bucket:
        Root directory used as the storage bucket.
    key:
        Relative file path under the bucket. Must not be absolute or empty.

    Returns
    -------
    bytes
        The file contents.
    """

    _validate_key(key)

    # Support reading from S3 when ``bucket`` is an ``s3://`` URL. The
    # dependency on :mod:`boto3` is optional so tests that only use the file
    # system do not require the package.
    if str(bucket).startswith("s3://"):
        from importlib import import_module
        from typing import Any, cast

        boto3 = cast(Any, import_module("boto3"))
        s3 = boto3.client("s3")
        bucket_name = str(bucket)[5:]
        if not bucket_name or "/" in bucket_name:
            raise ValueError("invalid s3 bucket")
        obj = s3.get_object(Bucket=bucket_name, Key=key)
        return cast(bytes, obj["Body"].read())

    bucket_path = _sanitize_bucket(bucket)
    path = bucket_path / key
    return path.read_bytes()


def upload_file(
    bucket: str | Path,
    key: str,
    data: bytes,
    *,
    append_only: bool = False,
    retention_days: int = 1,
) -> Path | str:
    """Save ``data`` to ``bucket``/``key`` and return the file path.

    Parameters
    ----------
    bucket:
        Root directory used as the storage bucket.
    key:
        Relative file path under the bucket. Must not be absolute or empty.
    data:
        File contents to write.
    append_only:
        When ``True`` existing objects will not be overwritten. For S3
        destinations an object lock in ``COMPLIANCE`` mode is applied so the
        object becomes append-only.
    retention_days:
        Optional retention period for S3 object lock.

    Returns
    -------
    Path | str
        Location of the written file or S3 URI.
    """

    _validate_key(key)
    if retention_days < 0:
        raise ValueError("retention_days must be non-negative")

    # Handle S3 buckets via ``boto3`` if the bucket name is an ``s3://`` URL.
    if str(bucket).startswith("s3://"):
        from importlib import import_module
        from typing import Any, cast

        boto3 = cast(Any, import_module("boto3"))
        s3 = boto3.client("s3")
        bucket_name = str(bucket)[5:]
        if not bucket_name or "/" in bucket_name:
            raise ValueError("invalid s3 bucket")
        extra: dict[str, object] = {}
        if append_only:
            retain_until = datetime.now(timezone.utc) + timedelta(days=retention_days)
            extra = {
                "ObjectLockMode": "COMPLIANCE",
                "ObjectLockRetainUntilDate": retain_until,
            }
        s3.put_object(Bucket=bucket_name, Key=key, Body=data, **extra)
        return f"s3://{bucket_name}/{key}"

    bucket_path = _sanitize_bucket(bucket)
    dest = bucket_path / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    if append_only and dest.exists():
        raise FileExistsError("object already exists")
    dest.write_bytes(data)
    return dest
