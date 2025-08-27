from docreview360.fed_numbering import apply_numbering


def test_apply_numbering() -> None:
    text = "# Intro\n\n# Methods"
    mapping = {"Intro": "1", "Methods": "2"}
    result = apply_numbering(text, mapping)
    assert result.splitlines()[0] == "# 1 Intro"
    assert result.splitlines()[2] == "# 2 Methods"


def test_apply_numbering_preserves_heading_levels() -> None:
    """Headings should retain their original depth after numbering."""
    text = "# Intro\n\n## Details"
    mapping = {"Intro": "1", "Details": "1.1"}
    result = apply_numbering(text, mapping).splitlines()
    assert result[0] == "# 1 Intro"
    assert result[2] == "## 1.1 Details"
