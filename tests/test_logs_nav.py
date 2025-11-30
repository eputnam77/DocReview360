from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_sidebar_has_no_logs_link() -> None:
    sidebar = (REPO_ROOT / "frontend/components/workflow/Sidebar.tsx").read_text()
    assert "/logs" not in sidebar


def test_configuration_has_audit_logs_link() -> None:
    config_index = (REPO_ROOT / "frontend/pages/configuration/index.tsx").read_text()
    assert "/configuration/audit-logs" in config_index
