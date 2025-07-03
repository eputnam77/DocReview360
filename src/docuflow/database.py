"""Lightweight database abstraction layer using SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class Database:
    """Simple wrapper providing a consistent database interface."""

    def __init__(self, url: str) -> None:
        if not url:
            raise ValueError("Database URL must be provided")
        self.url = url
        self._engine: Engine = create_engine(url)

    def initialize(self) -> None:
        """Validate the connection by executing a lightweight query."""
        with self._engine.begin() as conn:
            conn.execute(text("SELECT 1"))

    @contextmanager
    def session(self):
        """Yield a connection context."""
        with self._engine.begin() as conn:
            yield conn
