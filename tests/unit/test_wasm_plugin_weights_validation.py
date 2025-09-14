import pytest
from docreview360.wasm_plugin import lint_text


def test_lint_text_weight_length_mismatch():
    # _fann_features returns length >2; mismatch should raise ValueError
    with pytest.raises(ValueError):
        lint_text("hi", weights=[0.1])
