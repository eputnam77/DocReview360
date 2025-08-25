import importlib
import sys


def test_workflows_skip_bootstrap_by_default(monkeypatch):
    """Importing workflows should not create sample data unless enabled."""
    monkeypatch.delenv("DOCREVIEW360_ENABLE_SAMPLE_BOOTSTRAP", raising=False)

    # Ensure a fresh import
    if "docreview360.workflows" in sys.modules:
        del sys.modules["docreview360.workflows"]

    wf = importlib.import_module("docreview360.workflows")
    assert wf.workflows == {}
