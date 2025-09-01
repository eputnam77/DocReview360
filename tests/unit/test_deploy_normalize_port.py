from docreview360.deploy import normalize_port


def test_normalize_port_non_integer_float_returns_zero():
    assert normalize_port(123.456) == 0
    assert normalize_port("123.456") == 0
