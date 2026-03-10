# SPDX-License-Identifier: MIT
"""Alembic environment configuration for DocReview360.

The database URL is read (in priority order) from:
  1. ``DOCREVIEW360_DATABASE_URL`` environment variable
  2. ``sqlalchemy.url`` in ``alembic.ini``

The SQLAlchemy ``Base.metadata`` from ``docreview360.models`` is used for
``--autogenerate`` support so that ``alembic revision --autogenerate`` can
detect schema drift between the ORM models and the live database.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make the source package importable when running from the project root.
_src = Path(__file__).resolve().parents[2] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from docreview360.models import Base  # noqa: E402  (after sys.path tweak)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url() -> str:
    """Return the database URL, preferring the environment variable."""
    env_url = os.environ.get("DOCREVIEW360_DATABASE_URL", "")
    return env_url or config.get_main_option("sqlalchemy.url", "sqlite:///docreview360.db")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live database connection."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
