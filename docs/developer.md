# Developer guide

Set up a development environment, then extend DocReview360 with migrations, plugins, and document types.

For first-run setup, see [Get started](getting_started.md). This page covers what you need to contribute code.

## Set up your environment

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev,test,security]"
pre-commit install
```

Python 3.11 and 3.12 are supported. 3.13 is not.

## Set authentication secrets

In development, DocReview360 falls back to safe defaults and logs a `RuntimeWarning` for each unset value. Set these to silence the warnings and to match production behavior:

```bash
export DOCREVIEW360_ENV=dev
export DOCREVIEW360_SECRET_KEY=your-secret
export DOCREVIEW360_ALGORITHM=HS256
export DOCREVIEW360_ACCESS_EXPIRE_MINUTES=30
export DOCREVIEW360_TOKEN_ISSUER=docreview360.local
export DOCREVIEW360_TOKEN_AUDIENCE=docreview360-users
export DOCREVIEW360_OIDC_SECRET_KEY=your-oidc-secret
export DOCREVIEW360_OIDC_ALGORITHM=HS256
export DOCREVIEW360_OIDC_EXPIRE_MINUTES=30
export DOCREVIEW360_OIDC_TOKEN_ISSUER=docreview360-oidc.local
export DOCREVIEW360_OIDC_TOKEN_AUDIENCE=docreview360-oidc
```

Set `DOCREVIEW360_ENV` to any value other than `dev` or `test` and missing secrets become a startup failure instead of a warning. Treat that as production.

Cookie-based auth requires an `X-CSRF-Token` header matching the `csrf_token` cookie.

See [Environment variables](environment_variables.md) for the complete list.

## Run the checks

```bash
pre-commit run --all-files
pytest --cov=src
```

The full command set is in [Testing and quality](testing_and_quality.md).

## Project layout

| Path | Contents |
| --- | --- |
| `src/docreview360/` | Backend and CLI: FastAPI, SQLAlchemy, Celery, ML |
| `src/docreview360/api/` | Route definitions |
| `frontend/` | Next.js app: `pages/`, `components/`, `extensions/` |
| `tests/` | pytest suite |
| `migrations/` | Raw SQL migrations |
| `scripts/` | Development and release tooling |

`src/docreview360/api/__init__.py` is very large. Search it rather than opening it whole.

## Database migrations

The `docreview360.database.Database` class applies raw SQL migrations. Put `.sql` files in the repository-level `migrations/` directory, or pass a custom path to `Database.migrate()`.

Each file runs once and is recorded in the `schema_versions` table. Migrations are forward-only.

```bash
docreview360 migrate                                  # apply packaged migrations
docreview360 migrate --migrations-path ./migrations   # apply your own
```

For the forward-only policy, rollback approach, supported engines, and SemVer rules for schema changes, see [Migration policy](migration_policy.md).

## Move data between instances

```bash
docreview360 migrate export backup.gz
docreview360 migrate import backup.gz
```

## Write a plugin

Register a plugin at runtime through the REST API. Send the module path and DocReview360 calls its `register` function with the global registry:

```bash
curl -X POST http://127.0.0.1:8000/plugins \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"module": "my_package.my_plugin"}'
```

Enable or disable a registered plugin:

```
PUT /plugins/{name}/enable
PUT /plugins/{name}/disable
```

Your module must expose a `register(registry)` function.

## Share document types

Administrators create document types through the API. To copy a configuration between instances, export it and re-import it:

- `docreview360.doc_types.export_document_types()`
- `docreview360.doc_types.import_document_types()`

## Related pages

- [Testing and quality](testing_and_quality.md)
- [API overview](api_overview.md)
- [CLI reference](cli.md)
- [Release packaging](release_packaging.md)
- [Architecture decisions](adr/0001-core-architecture.md)
