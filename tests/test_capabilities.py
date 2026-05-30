from click.testing import CliRunner

from docreview360.capabilities import capabilities_payload, list_capabilities
from docreview360.cli import cli


def test_core_capabilities_describe_lightweight_web_app() -> None:
    capabilities = {item.id: item for item in list_capabilities()}

    assert capabilities["core_review"].installed is True
    assert capabilities["sqlite"].installed is True
    assert capabilities["tiptap_editor"].installed is True
    assert capabilities["notifications"].installed is True
    assert capabilities["ml_runtime"].core is False
    assert capabilities["ml_runtime"].install_extra == "ml-cpu"
    assert capabilities["worker"].install_extra == "worker"


def test_capabilities_payload_is_json_ready() -> None:
    payload = capabilities_payload()

    assert isinstance(payload["capabilities"], list)
    assert payload["summary"]["total"] >= 1
    assert "core_ready" in payload["summary"]


def test_capabilities_cli_lists_core_and_optional_features() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["capabilities"])

    assert result.exit_code == 0
    assert "core_review:" in result.output
    assert "ml_runtime:" in result.output
