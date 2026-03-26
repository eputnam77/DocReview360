import subprocess
from pathlib import Path

import pytest
from docreview360.release_signing import create_signed_git_tag, verify_git_tag_signature


def test_create_signed_git_tag_uses_default_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = args[0]
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(args[0], 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    output = create_signed_git_tag("v0.1.0", message="DocReview360 v0.1.0")

    assert output == "ok"
    assert captured["cmd"] == ["git", "tag", "-s", "v0.1.0", "-m", "DocReview360 v0.1.0"]


def test_create_signed_git_tag_uses_explicit_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = args[0]
        return subprocess.CompletedProcess(args[0], 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    create_signed_git_tag("v0.1.1", message="release", key_id="ABC123")

    assert captured["cmd"] == ["git", "tag", "-s", "-u", "ABC123", "v0.1.1", "-m", "release"]


def test_verify_git_tag_signature_uses_verify_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = args[0]
        return subprocess.CompletedProcess(args[0], 0, "", "Good signature")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    output = verify_git_tag_signature("v0.1.0", repo_root=Path("."))

    assert captured["cmd"] == ["git", "verify-tag", "v0.1.0"]
    assert output == "Good signature"
