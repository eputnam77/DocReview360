from docreview360.monitoring import open_dashboard


def test_open_dashboard_returns_url() -> None:
    url = open_dashboard()
    assert url.startswith("http://")
