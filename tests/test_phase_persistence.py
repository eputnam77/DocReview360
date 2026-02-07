from __future__ import annotations

import importlib
from pathlib import Path

import docreview360.phases as phases


def test_phase_persistence_round_trip(tmp_path: Path, monkeypatch) -> None:
    phases_file = tmp_path / "phases.json"
    monkeypatch.setenv("DOCREVIEW360_PHASES_FILE", str(phases_file))
    monkeypatch.setenv("DOCREVIEW360_ENABLE_PHASE_PERSISTENCE", "true")

    phases_module = importlib.reload(phases)
    phases_module.reset_phases()
    phases_module.add_phase("Persisted Phase")

    assert phases_file.exists()

    phases_module = importlib.reload(phases)
    assert "Persisted Phase" in phases_module.list_phases()

    monkeypatch.delenv("DOCREVIEW360_PHASES_FILE", raising=False)
    monkeypatch.delenv("DOCREVIEW360_ENABLE_PHASE_PERSISTENCE", raising=False)
    phases_module = importlib.reload(phases)
    phases_module.reset_phases()
