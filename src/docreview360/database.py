"""Lightweight database abstraction layer using SQLAlchemy."""

from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import StaticPool

from .models import Base


def default_url(database: str) -> str:
    """Return a default SQLAlchemy URL for the given backend.

    The ``database`` argument is treated case-insensitively and accepts common
    synonyms (e.g. ``"postgresql"``).
    """

    db = database.lower()
    if db in {"sqlite", "sqlite3"}:
        return "sqlite:///docreview360.db"
    if db in {"postgres", "postgresql"}:
        return "postgresql+psycopg://docreview360:docreview360@localhost:5432/docreview360"
    if db in {"mysql"}:
        return "mysql+pymysql://docreview360:docreview360@localhost:3306/docreview360"
    raise ValueError(f"Unsupported database '{database}'")


def _parse_sql_statements(file: Path) -> list[str]:
    """Return individual SQL statements from ``file``.

    The parser is aware of ``CREATE TRIGGER`` blocks whose terminating
    ``END;`` may appear on a separate line. To keep the implementation
    lightweight we normalise ``END`` blocks followed by optional
    whitespace and a semicolon into a single ``END;`` token using a
    regular expression before processing line-by-line.
    """

    content = re.sub(r"END\s*;", "END;", file.read_text(), flags=re.IGNORECASE)
    lines = content.splitlines()
    statements: list[str] = []
    buffer: list[str] = []
    in_trigger = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        code = stripped.split("--", 1)[0].strip()
        if not code:
            continue
        buffer.append(code)
        upper = code.upper()
        if upper.startswith("CREATE TRIGGER"):
            in_trigger = True
        if upper.startswith("END;") and in_trigger:
            statements.append("\n".join(buffer).rstrip(";"))
            buffer = []
            in_trigger = False
            continue
        if not in_trigger and code.endswith(";"):
            statements.append("\n".join(buffer).rstrip(";"))
            buffer = []
    if buffer:
        statements.append("\n".join(buffer).rstrip(";"))
    return statements


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
            if url == "sqlite:///:memory:":
                # ``StaticPool`` keeps the in-memory database alive for the
                # lifetime of this engine while ensuring each ``Database``
                # instance gets its own isolated database.
                url = "sqlite+pysqlite:///:memory:"
                connect_args = {"check_same_thread": False}
            else:
                connect_args = {"check_same_thread": False}
            self._engine = create_engine(url, connect_args=connect_args, poolclass=StaticPool)
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
        """Apply model and SQL migrations."""
        from .models import Base

        # ``Base.metadata.create_all`` may implicitly commit transactions which
        # interferes with any outer transactional context.  However using two
        # separate ``begin`` blocks for model creation and SQL migrations causes
        # new in-memory SQLite databases to be created when the connection is
        # closed after the first block.  When running the full test suite this
        # resulted in migrations being applied to a fresh database and all
        # previously created tables being lost, yielding an empty schema.
        #
        # Executing both operations within a single transactional ``begin``
        # block ensures that the same connection (and therefore the same
        # in-memory database) is used throughout and that all statements are
        # committed together.
        with self._engine.begin() as conn:
            Base.metadata.create_all(conn)
            self._apply_sql_migrations(migrations_path, conn)

    def _apply_sql_migrations(self, path: str | Path | None, conn: Any | None = None) -> None:
        """Execute raw SQL migrations if available."""
        if path is None:
            path = Path(__file__).resolve().parents[2] / "migrations"
        path = Path(path)
        if not path.exists():
            return

        if conn is None:
            with self._engine.begin() as conn:
                self._apply_sql_migrations(path, conn)
            return

        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_versions (filename TEXT PRIMARY KEY)"))
        applied = {row[0] for row in conn.execute(text("SELECT filename FROM schema_versions"))}
        for file in sorted(path.glob("*.sql")):
            name = file.name
            if name in applied:
                continue
            statements = _parse_sql_statements(file)
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                except OperationalError as exc:
                    msg = str(exc).lower()
                    if "duplicate column name" in msg or "already exists" in msg:
                        continue
                    raise
            conn.execute(
                text("INSERT INTO schema_versions (filename) VALUES (:name)"),
                {"name": name},
            )
        # When a connection is provided by the caller we rely on its enclosing
        # transaction to commit.  ``migrate`` now invokes this function within a
        # dedicated ``begin`` block ensuring all executed statements are
        # committed together.  Explicit commits here previously interacted poorly
        # with context-managed transactions leading to ``InvalidRequestError``
        # during migrations.

    def drop_all(self) -> None:
        """Drop all database tables. Useful for tests."""
        Base.metadata.drop_all(self._engine)
        with self._engine.begin() as conn:
            inspector = inspect(conn)
            for table in inspector.get_table_names():
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
