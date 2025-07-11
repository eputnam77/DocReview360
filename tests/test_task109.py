from docreview360.wasm_plugin import lint_text


def test_lint_pass_fail() -> None:
    weights = [0.0, -0.1, 1.2, 0.0]
    assert lint_text("clear", weights)
    assert not lint_text("bad bad bad", weights)
