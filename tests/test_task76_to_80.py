from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest
import yaml

iac = SourceFileLoader(
    "docuflow.iac_templates", "src/docuflow/iac_templates/__init__.py"
).load_module()
get_template = iac.get_template


def test_get_template_valid() -> None:
    content = get_template("eks")
    assert "aws_eks_cluster" in content


def test_get_template_invalid() -> None:
    with pytest.raises(ValueError):
        get_template("unknown")


def test_trivy_step_present() -> None:
    ci = Path(".github/workflows/ci.yml").read_text()
    assert "aquasecurity/trivy-action" in ci


def test_langgraph_manifest() -> None:
    data = yaml.safe_load(Path("services/langgraph-studio/deployment.yaml").read_text())
    assert data["metadata"]["name"] == "langgraph-studio"


def test_loki_alert_rule() -> None:
    alerts = Path("monitoring/loki-alerts.yaml").read_text()
    assert "HighErrorRate" in alerts


def test_fedramp_doc_exists() -> None:
    assert Path("docs/compliance/fedramp_controls.md").exists()
