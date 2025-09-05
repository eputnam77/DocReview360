import docreview360.phases as phases
import pytest


def test_delete_phase_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phases, "_phases", ["Existing"], raising=False)
    with pytest.raises(KeyError):
        phases.delete_phase("Missing")


def test_rename_phase_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phases, "_phases", ["Existing"], raising=False)
    with pytest.raises(KeyError):
        phases.rename_phase("Missing", "Other")

