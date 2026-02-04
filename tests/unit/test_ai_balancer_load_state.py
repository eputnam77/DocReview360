import json
from pathlib import Path

import pytest

from docreview360 import ai_balancer


def test_load_state_invalid_format(tmp_path: Path) -> None:
    file = tmp_path / "state.json"
    file.write_text("[]")
    ai_balancer.reset()
    with pytest.raises(ValueError):
        ai_balancer.load_state(file)


def test_load_state_negative_values(tmp_path: Path) -> None:
    """Negative job counts should be rejected."""
    file = tmp_path / "state.json"
    file.write_text(json.dumps({"w1": -1}))
    ai_balancer.reset()
    with pytest.raises(ValueError):
        ai_balancer.load_state(file)


def test_load_state_non_integer_values(tmp_path: Path) -> None:
    """Non-integer job counts should raise ``ValueError``."""
    file = tmp_path / "state.json"
    file.write_text(json.dumps({"w1": "oops"}))
    ai_balancer.reset()
    with pytest.raises(ValueError):
        ai_balancer.load_state(file)


def test_load_state_float_values(tmp_path: Path) -> None:
    """Float job counts should be rejected to avoid truncation."""
    file = tmp_path / "state.json"
    file.write_text(json.dumps({"w1": 1.5}))
    ai_balancer.reset()
    with pytest.raises(ValueError):
        ai_balancer.load_state(file)


def test_load_state_invalid_json(tmp_path: Path) -> None:
    file = tmp_path / "state.json"
    file.write_text("{not-json")
    ai_balancer.reset()
    with pytest.raises(ValueError):
        ai_balancer.load_state(file)


def test_duplicate_registration_and_cleanup() -> None:
    ai_balancer.reset()
    ai_balancer.register_worker("w1")
    with pytest.raises(ValueError):
        ai_balancer.register_worker("w1")
    ai_balancer.assign_job()
    ai_balancer.complete_job("w1")
    assert ai_balancer.deregister_worker("w1") == 0
