from pathlib import Path

from docreview360.github_sync import pull_document, push_document


def test_push_and_pull_document(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    doc = tmp_path / "a.txt"
    doc.write_text("hi")
    commit = push_document(doc, repo)
    assert len(commit) == 40
    data = pull_document(doc.name, repo)
    assert data == b"hi"
