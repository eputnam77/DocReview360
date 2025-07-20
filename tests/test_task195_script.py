from pathlib import Path

SCRIPT = Path(".git/hooks/sendemail-validate.sample")


def test_sendemail_hook_contains_commands() -> None:
    text = SCRIPT.read_text()
    assert "codespell" in text
    assert "gitlint --msg-filename" in text
    assert "gitlint --staged" in text
    assert "docreview360.git_hooks" in text
