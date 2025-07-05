from docuflow.fann_corpus import curate_corpus


def test_curate_corpus() -> None:
    clean, anomalies = curate_corpus(["normal text", "BAD BAD", "another"], 0.5)
    assert "normal text" in clean
    assert "BAD BAD" in anomalies
