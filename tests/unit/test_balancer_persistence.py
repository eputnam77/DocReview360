from pathlib import Path

import pytest
from docreview360 import ai_balancer


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    """Worker registry should persist to disk and restore correctly."""
    ai_balancer.reset()
    ai_balancer.register_worker("alice")
    ai_balancer.register_worker("bob")
    # Simulate some load
    ai_balancer._workers["alice"] = 2  # type: ignore[attr-defined]
    ai_balancer._workers["bob"] = 1  # type: ignore[attr-defined]

    state = tmp_path / "state.json"
    ai_balancer.save_state(state)

    # Reset and ensure state is gone
    ai_balancer.reset()
    with pytest.raises(RuntimeError):
        ai_balancer.assign_job()

    ai_balancer.load_state(state)
    assert ai_balancer.current_load("alice") == 2
    assert ai_balancer.current_load("bob") == 1


def test_load_state_missing_file_clears_registry(tmp_path: Path) -> None:
    """Loading from a non-existent path should clear existing workers."""
    ai_balancer.reset()
    ai_balancer.register_worker("alice")
    missing = tmp_path / "missing.json"
    ai_balancer.load_state(missing)
    with pytest.raises(KeyError):
        ai_balancer.current_load("alice")


def test_assign_job_and_error_paths() -> None:
    """Exercise additional balancer branches for full coverage."""
    ai_balancer.reset()
    ai_balancer.register_worker("a")
    ai_balancer.register_worker("b")
    ai_balancer._workers["a"] = 1  # type: ignore[attr-defined]
    # ``b`` has lower load and should be chosen
    assert ai_balancer.assign_job() == "b"
    assert ai_balancer.current_load("b") == 1

    # Error conditions
    with pytest.raises(ValueError):
        ai_balancer.register_worker("")
    with pytest.raises(KeyError):
        ai_balancer.complete_job("ghost")
    with pytest.raises(KeyError):
        ai_balancer.deregister_worker("ghost")
