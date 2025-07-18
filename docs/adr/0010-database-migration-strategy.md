# 0010 - Database Migration Strategy

## Status
Accepted

## Context
The project uses SQLAlchemy models but avoids heavy migration frameworks. A concise public record clarifies how schema updates are applied.

## Decision
- Treat the models in `src/docreview360/models.py` as the source of truth.
- `Database.migrate()` executes `.sql` files under `migrations/` and records versions in `schema_versions`.
- Future contributors may switch to Alembic if the schema grows, but the custom helper keeps dependencies light for now.

## Consequences
New SQL files run once when migrations are invoked. Tests can drop and recreate the database easily, while leaving room for more sophisticated tooling later.
