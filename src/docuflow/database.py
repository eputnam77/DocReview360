"""Lightweight database abstraction layer using SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


class Database:
    """Simple wrapper providing a consistent database interface.

    The class wraps a SQLAlchemy engine and offers a lightweight migration
    system. SQLAlchemy models are created automatically. Additionally, raw SQL
    files placed in a ``migrations`` directory are executed once and tracked in
    the ``schema_versions`` table.
    """

    def __init__(self, url: str) -> None:
        if not url:
            raise ValueError("Database URL must be provided")
        self.url = url
        if url.startswith("sqlite"):
            self._engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self._engine = create_engine(url)

    def initialize(self) -> None:
        """Validate the connection by executing a lightweight query."""
        with self._engine.begin() as conn:
            conn.execute(text("SELECT 1"))

    @contextmanager
    def session(self) -> Iterator[Any]:
        """Yield a connection context."""
        with self._engine.begin() as conn:
            yield conn

    def migrate(self, migrations_path: str | Path | None = None) -> None:
        """Apply model and SQL migrations.

        Parameters
        ----------
        migrations_path:
            Optional path to a directory containing ``.sql`` migration files.
            Files are applied in alphabetical order and recorded in the
            ``schema_versions`` table to avoid reapplication.
        """
        from .models import Base

        Base.metadata.create_all(self._engine)

        self._apply_sql_migrations(migrations_path)

    def _apply_sql_migrations(self, path: str | Path | None) -> None:
        """Execute raw SQL migrations if available."""
        if path is None:
            path = Path(__file__).with_name("migrations")
        path = Path(path)
        if not path.exists():
            return

        with self._engine.begin() as conn:
            conn.execute(
                text("CREATE TABLE IF NOT EXISTS schema_versions (filename TEXT PRIMARY KEY)")
            )
            applied = {row[0] for row in conn.execute(text("SELECT filename FROM schema_versions"))}
            for file in sorted(path.glob("*.sql")):
                name = file.name
                if name in applied:
                    continue
                conn.execute(text(file.read_text()))
                conn.execute(
                    text("INSERT INTO schema_versions (filename) VALUES (:name)"),
                    {"name": name},
                )

    def drop_all(self) -> None:
        """Drop all database tables. Useful for tests."""
        from .models import Base

        Base.metadata.drop_all(self._engine)
        with self._engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS schema_versions"))
