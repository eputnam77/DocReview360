from docreview360.database import default_url


def test_default_url_strips_whitespace():
    assert default_url(" Postgres ") == default_url("postgres")
