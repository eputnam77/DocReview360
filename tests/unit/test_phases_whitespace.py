import docreview360.phases as phases
import pytest


def test_delete_and_rename_trim_input(monkeypatch: pytest.MonkeyPatch) -> None:
    # Provide a clean phase list to avoid interference with global state.
    monkeypatch.setattr(phases, "_phases", ["Initial"], raising=False)

    # Adding a new phase with extra whitespace should be normalised
    phases.add_phase("  Temp  ")
    assert "Temp" in phases.list_phases()

    # Renaming and deleting should also handle surrounding whitespace
    phases.rename_phase("  Temp  ", "  Renamed  ")
    assert "Renamed" in phases.list_phases()

    phases.delete_phase("  Renamed  ")
    assert "Renamed" not in phases.list_phases()
