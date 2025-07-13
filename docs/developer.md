# Developer Guide

This short guide explains how to run the project in a local environment.

## Installation

Create and activate a virtual environment, then install the development
dependencies listed in `pyproject.toml`:

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows use .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .[dev]
pre-commit install
```

The repository also provides ``requirements.txt`` and ``requirements-dev.txt``
files for use with ``pip``. They are generated from the ``pyproject`` but may
lag behind the lock file, so ``pip install -e .[dev]`` is the most reliable way
to pull in the current dependencies.

## Running Tests

Run all linters and the test suite with coverage using:

```bash
pre-commit run --all-files
pytest --cov=src
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
