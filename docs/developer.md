# Developer Guide

This short guide explains how to run the project in a local environment.

## Prerequisites

Install [`uv`](https://github.com/astral-sh/uv) and [`Poetry`](https://python-poetry.org/) with `pip` or `pipx`:

```bash
pip install uv poetry
# or
pipx install uv poetry
```

1. **Create and activate a virtual environment**

   ```bash
   uv venv 3.12
   source 3.12/bin/activate
   ```

2. **Install development tools**

  ```bash
  poetry install --with dev
  poetry sync --with dev
  uv pip install -r pyproject.toml --extra dev
  pre-commit install
  ```

3. **Set authentication secrets**

   ```bash
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
   # Treat any non-dev/test value (for example "production") as production.
   # When set, missing secrets trigger a startup failure instead of a warning.
   export DOCREVIEW360_ENV=dev
   # Optional: DOCREVIEW360_SIGNATURE_SECRET for digital signatures
   # Cookie-based auth requires an X-CSRF-Token header that matches the csrf_token cookie.
   ```

4. **Testing**

  Run code checks and tests:

  ```bash
  pre-commit run --all-files
  pytest --cov=src
  ```

5. **End-to-end testing (with Playwright)**

  ```bash
  playwright install
  pytest -m e2e
  ```

## Database Migrations

The :class:`docreview360.database.Database` class supports raw SQL migrations. Place
``.sql`` files in ``src/docreview360/migrations`` or provide a custom path to
:py:meth:`Database.migrate`. Each file is executed once and recorded in the
``schema_versions`` table.

## Working with plugins

Plugins can be registered at runtime using the REST API.  Send a JSON body
containing ``{"module": "my_package.my_plugin"}`` to ``POST /plugins`` and the
module's ``register`` function will be invoked with the global registry.  Plugins
may also be enabled or disabled via ``PUT /plugins/{name}/enable`` or
``PUT /plugins/{name}/disable``.

## Document type management

Administrators can create document types through the API.  Export existing types
using :func:`docreview360.doc_types.export_document_types` and re-import them with
:func:`docreview360.doc_types.import_document_types` to share configurations between
instances.
