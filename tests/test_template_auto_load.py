"""Auto-load latest template when creating project."""

# mypy: ignore-errors

import importlib.util
import sys
import types
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "docreview360"
pkg = types.ModuleType("docreview360")
pkg.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("docreview360", pkg)


def _load(name: str, file: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, PACKAGE_DIR / file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


template_manager = _load("docreview360.template_manager", "template_manager.py")
doc_types = _load("docreview360.doc_types", "doc_types.py")
search = _load("docreview360.search", "search.py")
task214_mod = _load("docreview360.stubs.task214", "stubs/task214.py")
task215_mod = _load("docreview360.stubs.task215", "stubs/task215.py")

DocumentTypeModel = doc_types.DocumentTypeModel
ProjectModel = search.ProjectModel
task214 = task214_mod.task214
task215 = task215_mod.task215
upload_template = template_manager.upload_template


def test_project_creation_autoloads_latest_template() -> None:
    upload_template("ac", b"# AC v1", {"v": 1})
    upload_template("ac", b"# AC v2", {"v": 2})
    doc_type = DocumentTypeModel(name="AC", template="", default_template_id=None)
    task214(doc_type, "ac")
    project = ProjectModel(id="p1", name="Proj", user="alice")
    doc = task215(project, doc_type)
    assert doc.content == "# AC v2"
  
