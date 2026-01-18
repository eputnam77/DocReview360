import importlib

import pytest


def test_add_phase_rejects_empty() -> None:
    phases = importlib.import_module("docreview360.phases")
    original = phases._phases.copy()
    try:
        with pytest.raises(ValueError):
            phases.add_phase(" ")
    finally:
        phases._phases = original


def test_rename_phase_rejects_empty_new() -> None:
    phases = importlib.import_module("docreview360.phases")
    original = phases._phases.copy()
    phases._phases = ["Alpha"]
    try:
        with pytest.raises(ValueError):
            phases.rename_phase("Alpha", "")
    finally:
        phases._phases = original
