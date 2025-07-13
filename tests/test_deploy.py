from docreview360.deploy import normalize_port


def test_normalize_port_valid() -> None:
    assert normalize_port("8000") == 8000


def test_normalize_port_negative() -> None:
    assert normalize_port(-1) == 0
