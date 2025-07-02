from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_architecture_files_exist() -> None:
    assert (ROOT / "src" / "docuflow").is_dir()
    assert (ROOT / "tests").is_dir()
    assert (ROOT / "docs").is_dir()
    assert (ROOT / ".dev" / "ADRs" / "0001-initial-architecture.md").exists()
    assert (ROOT / ".github" / "workflows" / "ci.yml").exists()
