import importlib
import sys


def test_workflows_skip_bootstrap_by_default(monkeypatch):
    """Importing workflows should not create sample data unless enabled."""
    monkeypatch.delenv("DOCREVIEW360_ENABLE_SAMPLE_BOOTSTRAP", raising=False)

    # Ensure a fresh import — also clear the package-level store so a
    # previous test's workflows don't persist across the reload.
    if "docreview360.workflows" in sys.modules:
        del sys.modules["docreview360.workflows"]
    pkg = sys.modules.get("docreview360")
    if pkg is not None and hasattr(pkg, "_workflows_store"):
        delattr(pkg, "_workflows_store")

    wf = importlib.import_module("docreview360.workflows")
    assert wf.workflows == {}
