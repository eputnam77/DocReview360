import subprocess
from pathlib import Path

from docreview360.github_sync import pull_document, push_document


def test_push_and_pull_document(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    remote = tmp_path / "remote.git"

    def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(cmd, cwd=cwd, check=True)

    _run(["git", "init", "--bare", remote.as_posix()])
    doc = tmp_path / "a.txt"
    doc.write_text("hi")
    commit = push_document(doc, repo, remote=remote)
    assert len(commit) == 40
    data = pull_document(doc.name, repo, remote=remote)
    assert data == b"hi"
