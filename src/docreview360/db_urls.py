# SPDX-License-Identifier: MIT
"""Database URL helpers that do not import SQLAlchemy."""

from __future__ import annotations


def default_url(database: str) -> str:
    """Return the default SQLAlchemy URL for a supported database backend."""

    db = database.strip().lower()
    if db in {"sqlite", "sqlite3"}:
        return "sqlite:///docreview360.db"
    if db in {"postgres", "postgresql"}:
        return "postgresql+psycopg://docreview360:docreview360@localhost:5432/docreview360"
    if db in {"mysql"}:
        return "mysql+pymysql://docreview360:docreview360@localhost:3306/docreview360"
    if db in {"mssql", "sqlserver", "mssql+pyodbc"}:
        return (
            "mssql+pyodbc://docreview360:docreview360@localhost:1433/docreview360"
            "?driver=ODBC+Driver+17+for+SQL+Server"
        )
    if db in {"oracle", "oracledb"}:
        return "oracle+oracledb://docreview360:docreview360@localhost:1521/docreview360"
    raise ValueError(f"Unsupported database '{database}'")
