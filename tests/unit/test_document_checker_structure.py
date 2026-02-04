from docreview360.document_checker import _analyze_structure


def test_analyze_structure_strips_trailing_hashes() -> None:
    text = "\n".join(
        [
            "## Introduction ##",
            "Intro text.",
            "## Body ##",
            "Body text.",
            "## Conclusion ##",
            "Done.",
        ]
    )

    result = _analyze_structure(text)

    assert result["missing_sections"] == []
