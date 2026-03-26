from datetime import date
from pathlib import Path

import pytest
from docreview360.release_notes import generate_release_notes, read_project_version


def test_read_project_version_returns_unknown_when_missing(tmp_path: Path) -> None:
    assert read_project_version(tmp_path / "missing.toml") == "unknown"


def test_generate_release_notes_includes_container_digests(tmp_path: Path) -> None:
    output = tmp_path / "release" / "RELEASE_NOTES.md"
    generated = generate_release_notes(
        output,
        version="0.1.2",
        container_digests=[
            "ghcr.io/acme/docreview360@sha256:0123456789abcdef",
            "docker.io/acme/docreview360@sha256:abcdef0123456789",
        ],
        release_date=date(2026, 3, 1),
    )

    text = generated.read_text(encoding="utf-8")
    assert "# DocReview360 v0.1.2 Release Notes" in text
    assert "Release date: 2026-03-01" in text
    assert "ghcr.io/acme/docreview360@sha256:0123456789abcdef" in text
    assert "docker.io/acme/docreview360@sha256:abcdef0123456789" in text


def test_generate_release_notes_rejects_invalid_digest(tmp_path: Path) -> None:
    output = tmp_path / "RELEASE_NOTES.md"
    with pytest.raises(ValueError):
        generate_release_notes(output, version="0.1.2", container_digests=["invalid-digest"])
