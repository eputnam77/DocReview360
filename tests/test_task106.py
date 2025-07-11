from pathlib import Path

from docreview360.fann_corpus import curate_corpus, export_corpus


def test_curate_corpus() -> None:
    clean, anomalies = curate_corpus(["normal text", "BAD BAD", "another"], 0.5)
    assert "normal text" in clean
    assert "BAD BAD" in anomalies


def test_export_corpus(tmp_path: Path) -> None:
    clean = ["good"]
    anomalies = ["bad"]
    dest = export_corpus(clean, anomalies, tmp_path / "corpus.csv")
    assert dest.exists()
    lines = dest.read_text().splitlines()
    assert lines[0] == "text,label"
    assert "good,0" in lines
    assert "bad,1" in lines
