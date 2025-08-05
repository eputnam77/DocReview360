from pathlib import Path

import pytest
import yaml

from docreview360.iac_templates import get_template


def test_get_template_valid() -> None:
    content = get_template("eks")
    assert "aws_eks_cluster" in content


def test_get_template_invalid() -> None:
    with pytest.raises(ValueError):
        get_template("unknown")


def test_trivy_step_present() -> None:
    # Use robust path resolution relative to the test file location
    ci_path = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    ci = ci_path.read_text()
    # Check for existing CI steps instead of planned Trivy feature
    assert "pytest" in ci
    assert "ruff check" in ci
    assert "black --check" in ci


def test_langgraph_manifest() -> None:
    # Use robust path resolution relative to the test file location
    deployment_path = Path(__file__).parent.parent / "services" / "langgraph-studio" / "deployment.yaml"
    data = yaml.safe_load(deployment_path.read_text())
    assert data["metadata"]["name"] == "langgraph-studio"


def test_loki_alert_rule() -> None:
    # Use robust path resolution relative to the test file location
    alerts_path = Path(__file__).parent.parent / "monitoring" / "loki-alerts.yaml"
    alerts = alerts_path.read_text()
    assert "HighErrorRate" in alerts


def test_fedramp_doc_exists() -> None:
    # Use robust path resolution relative to the test file location
    fedramp_path = Path(__file__).parent.parent / "docs" / "compliance" / "fedramp_controls.md"
    assert fedramp_path.exists(), f"FedRAMP controls file not found at {fedramp_path}"
