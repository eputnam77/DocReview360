from docuflow.stubs.task164 import analyze_performance


def test_task164_performance_analysis() -> None:
    summary = analyze_performance(5)
    assert summary.startswith("avg ") and "over 5 calls" in summary
