from docuflow.contextual_help import get_help, register_help


def test_help_registry() -> None:
    register_help("editor", "Use the toolbar to format text")
    assert get_help("editor").startswith("Use")
    assert get_help("unknown") == "No help available"
