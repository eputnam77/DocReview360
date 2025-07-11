from docreview360.monitoring import start_observability_stack


def test_start_observability_stack() -> None:
    cfg = start_observability_stack(8001, 3001)
    assert cfg["prometheus"].endswith("8001/")
    assert cfg["grafana"].endswith("3001/")
