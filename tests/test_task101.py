from docuflow.fed_numbering import apply_numbering


def test_apply_numbering() -> None:
    text = "# Intro\n\n# Methods"
    mapping = {"Intro": "1", "Methods": "2"}
    result = apply_numbering(text, mapping)
    assert result.splitlines()[0] == "# 1 Intro"
    assert result.splitlines()[2] == "# 2 Methods"
