from pathlib import Path

from docreview360.document_checker import _analyze_structure, run_checks


def test_structure_and_readability(tmp_path: Path) -> None:
    content = (
        """# Introduction
Short intro.

# Body
"""
        + "word " * 250
        + "\n\n# Conclusion\nDone."
    )
    f = tmp_path / "doc.md"
    f.write_text(content)
    result = run_checks(f)
    structure = result["structure"]
    assert "body" in structure["overlong_sections"]
    assert structure["missing_sections"] == []
    assert "flesch_reading_ease" in result["readability"]


def test_missing_section(tmp_path: Path) -> None:
    content = """# Introduction
Intro text.

# Conclusion
Wrap up.
"""
    f = tmp_path / "doc2.md"
    f.write_text(content)
    result = run_checks(f)
    structure = result["structure"]
    assert "body" in structure["missing_sections"]


def test_repeated_headings_accumulate_section_content() -> None:
    content = (
        "# Introduction\nIntro\n\n# Body\n"
        + "word " * 120
        + "\n# Body\n"
        + "word " * 120
        + "\n# Conclusion\nDone."
    )
    structure = _analyze_structure(content)
    assert "body" in structure["overlong_sections"]
