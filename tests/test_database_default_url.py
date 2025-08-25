from docreview360.database import default_url


def test_default_url_postgres() -> None:
    url = default_url("postgres")
    assert url.startswith("postgresql+psycopg://")


def test_default_url_mysql() -> None:
    url = default_url("mysql")
    assert url.startswith("mysql+pymysql://")


def test_default_url_case_insensitive() -> None:
    assert default_url("Postgres") == default_url("postgres")
    assert default_url("MYSQL").startswith("mysql+pymysql://")
    assert default_url("SQLITE").startswith("sqlite:///")
    assert default_url("postgresql").startswith("postgresql+psycopg://")
