import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_contains_project_metadata() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert data["project"]["name"] == "docuflow"
    dev_deps = data["project"]["optional-dependencies"]["dev"]
    assert any(dep.startswith("pytest") for dep in dev_deps)


def test_ci_workflow_runs_tests() -> None:
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text())
    step_text = str(ci)
    assert "pytest" in step_text
