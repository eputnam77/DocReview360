import importlib
import sys


def test_workflows_skip_bootstrap_by_default(monkeypatch):
    """Importing workflows should not create sample data unless enabled."""
    monkeypatch.delenv("DOCREVIEW360_ENABLE_SAMPLE_BOOTSTRAP", raising=False)

    # Ensure a fresh import — also clear the package-level store so a
    # previous test's workflows don't persist across the reload.
    wf_pkg = sys.modules.get("docreview360.workflows")
    if wf_pkg is not None and hasattr(wf_pkg, "_workflows_store"):
        delattr(wf_pkg, "_workflows_store")
    for mod_name in [k for k in sys.modules if k.startswith("docreview360.workflows")]:
        del sys.modules[mod_name]

    wf = importlib.import_module("docreview360.workflows")
    assert wf.workflows == {}
