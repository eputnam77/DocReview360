from __future__ import annotations

from datetime import datetime, timezone

from docreview360.archive import ArchiveRecord


def test_archive_record_metadata_isolation() -> None:
    """Each archived record should maintain independent metadata maps."""

    base_kwargs = dict(
        document_id="doc",
        markdown=b"md",
        html=b"html",
        docx=b"docx",
        pdf=b"pdf",
    )

    record1 = ArchiveRecord(id="one", timestamp=datetime.now(timezone.utc), **base_kwargs)
    record2 = ArchiveRecord(id="two", timestamp=datetime.now(timezone.utc), **base_kwargs)

    record1.metadata["flag"] = True

    assert "flag" not in record2.metadata
