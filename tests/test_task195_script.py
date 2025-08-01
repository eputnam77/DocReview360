from pathlib import Path

# Use path relative to project root
project_root = Path(__file__).parent.parent
SCRIPT = project_root / "scripts" / "sendemail-validate.sample"


def test_sendemail_hook_contains_commands() -> None:
    text = SCRIPT.read_text()
    assert "codespell" in text
    assert "gitlint --msg-filename" in text
    assert "gitlint --staged" in text
    assert "docreview360.git_hooks" in text
