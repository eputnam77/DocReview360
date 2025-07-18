from docreview360.database import default_url


def test_default_url_postgres() -> None:
    url = default_url("postgres")
    assert url.startswith("postgresql+psycopg://")


def test_default_url_mysql() -> None:
    url = default_url("mysql")
    assert url.startswith("mysql+pymysql://")
