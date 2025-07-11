# 0006 - Database and Migration Strategy

## Status
Accepted

## Context
DocReview360 stores structured data for documents, projects and workflow approvals. The existing code ships a small SQLAlchemy wrapper and a set of models but no explicit record of how migrations are handled. We need a lightweight approach that works for the prototype without adding heavy dependencies.

## Decision

* Use SQLAlchemy models defined in `src/docreview360/models.py` as the single source of truth for table schemas.
* Provide a minimal migration helper in `Database.migrate()` that executes `.sql` files located under `migrations/` and tracks them in a `schema_versions` table.
* Avoid external frameworks like Alembic for now; the custom function keeps dependencies small and fits the project's simple schema.
* Future contributors can replace this mechanism with Alembic or another tool if schema complexity grows.

## Consequences

* New SQL files dropped into `migrations/` run once when `Database.migrate()` is called.
* Tests can reset the database easily using `Database.drop_all()`.
* The approach is lightweight but leaves room for more advanced tooling later if required.
