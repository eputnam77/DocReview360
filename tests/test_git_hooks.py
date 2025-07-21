from pathlib import Path

from docreview360 import git_hooks


def test_validate_patch_clean() -> None:
    patch = "diff --git a/file.txt b/file.txt\n@@\n+hello world\n"
    assert git_hooks.validate_patch(patch)


def test_validate_patch_detects_issues(tmp_path: Path) -> None:
    path = tmp_path / "p.patch"
    path.write_text("hello \tworld  \nveryveryverylongwordover20chars\n")
    patch = path.read_text()
    assert not git_hooks.validate_patch(patch)
