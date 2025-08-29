from __future__ import annotations

import json
from pathlib import Path

import pytest

from docreview360 import quality


def test_initialize_high_risk_terms_validates_shape(tmp_path: Path) -> None:
    path = tmp_path / "terms.json"
    path.write_text(json.dumps("not a list"))

    original = quality._HIGH_RISK_TERMS.copy()
    with pytest.raises(ValueError):
        quality.initialize_high_risk_terms(path)
    # state unchanged after failure
    assert quality._HIGH_RISK_TERMS == original

    # reset to ensure later tests operate with defaults
    quality.initialize_high_risk_terms()
