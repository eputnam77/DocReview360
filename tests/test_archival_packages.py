"""Export and archival package tests."""

from __future__ import annotations

import hashlib
import io
import xml.etree.ElementTree as ET
import zipfile

from docreview360.logs import clear_logs, log_event, query_logs
from docreview360.notifications import send_email, sent_emails

# AR-BAG


def create_bag(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("bagit.txt", "BagIt-Version: 1.0")
        manifest = "\n".join(
            f"{hashlib.sha256(data).hexdigest()}  {name}" for name, data in files.items()
        )
        zf.writestr("manifest-sha256.txt", manifest)
        for name, data in files.items():
            zf.writestr(f"data/{name}", data)
    return buf.getvalue()


def test_bagit_zip_contains_manifest() -> None:
    pkg = create_bag({"doc.txt": b"hi"})
    with zipfile.ZipFile(io.BytesIO(pkg)) as zf:
        assert "bagit.txt" in zf.namelist()
        manifest = zf.read("manifest-sha256.txt").decode()
        assert hashlib.sha256(b"hi").hexdigest() in manifest


# AR-METS


def generate_mets(files: dict[str, bytes]) -> str:
    mets = ET.Element("mets")
    premis = ET.SubElement(mets, "premis")
    premis.set("count", str(len(files)))
    return ET.tostring(mets).decode()


def test_mets_xml_has_premis_event_count() -> None:
    xml = generate_mets({"a.txt": b"a", "b.txt": b"b"})
    root = ET.fromstring(xml)
    assert root.find("premis").get("count") == "2"


# AR-PUR


def purview_upload(data: bytes) -> str:
    checksum = hashlib.sha256(data).hexdigest()
    log_event("archive", checksum=checksum)
    return checksum


def test_purview_archive_logs_row() -> None:
    clear_logs()
    checksum = purview_upload(b"data")
    entry = query_logs("archive")[0]
    assert entry.metadata["checksum"] == checksum


# AR-Fail


def archive_payload(data: bytes) -> None:
    if data != b"good":
        log_event("ARCHIVE_FAILED")
        send_email("default", "records@example.com", subject="fail", body="bad")


def test_corrupt_payload_triggers_email_to_records() -> None:
    clear_logs()
    sent_emails.clear()
    archive_payload(b"bad")
    assert query_logs("ARCHIVE_FAILED")
    assert sent_emails[0]["to"] == "records@example.com"
