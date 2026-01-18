from docreview360.wasm_plugin import lint_text


def test_lint_pass_fail() -> None:
    assert lint_text("Routine memo with clear structure")
    assert not lint_text("URGENT bad bad memo")
