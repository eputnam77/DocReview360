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
    Windows host.  Normalising separators ensures traversal attempts are caught
    consistently across platforms.
    """

    if not key or key.startswith("/") or key.endswith("/"):
        raise ValueError("invalid key")
    # Leading or trailing spaces can produce confusing files that are hard to
    # reference later. Treat such keys as invalid early.
    if key != key.strip():
        raise ValueError("invalid key")

    normalized = key.replace("\\", "/")
    # Newline or null bytes in paths can lead to log injection or truncation
    # issues on some filesystems. Treat such keys as invalid early.
    if any(c in normalized for c in ("\n", "\r", "\x00")):
        raise ValueError("invalid key")
    # Reject empty path segments to prevent ambiguous or accidental absolute
    # paths.  ``PurePosixPath`` collapses consecutive separators so we detect
    # them before normalisation.
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
        obj = s3.get_object(Bucket=bucket_name, Key=key)
        return cast(bytes, obj["Body"].read())

    path = Path(bucket) / key
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
        extra: dict[str, object] = {}
        if append_only:
            retain_until = datetime.now(timezone.utc) + timedelta(days=retention_days)
            extra = {
                "ObjectLockMode": "COMPLIANCE",
                "ObjectLockRetainUntilDate": retain_until,
            }
        s3.put_object(Bucket=bucket_name, Key=key, Body=data, **extra)
        return f"s3://{bucket_name}/{key}"

    dest = Path(bucket) / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    if append_only and dest.exists():
        raise FileExistsError("object already exists")
    dest.write_bytes(data)
    return dest
