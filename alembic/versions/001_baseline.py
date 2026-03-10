# SPDX-License-Identifier: MIT
"""Baseline migration — represents the schema already created by the legacy migration system.

Revision ID: 001_baseline
Revises:
Create Date: 2026-03-10

This is a **no-op** migration that serves as the root anchor for the Alembic
revision chain.  The DocReview360 schema was originally managed by the custom
``Database.migrate()`` system (SQLAlchemy ``create_all`` + SQL files in
``migrations/``).  Existing deployments should run::

    alembic stamp 001_baseline

to record that the current schema is already at this baseline without
executing any DDL.  New deployments should run::

    alembic upgrade head

which will also be a no-op for this revision (schema is created by
``Database.migrate()`` on first startup) and will apply any subsequent
migrations on top.
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema is already managed by docreview360.database.Database.migrate().
    # This baseline is intentionally a no-op.
    pass


def downgrade() -> None:
    # Dropping the entire schema is a destructive, out-of-band operation.
    # Use `docreview360 migrate export backup.gz` before manual schema drops.
    pass
