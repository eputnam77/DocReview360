# Developer Guide

This short guide explains how to run the project in a local environment.

## Installation

```bash
pip install -e .[dev]
pre-commit install
```

## Running Tests

Run all linters and the test suite with coverage using:

```bash
pre-commit run --all-files
pytest --cov=src
```

## Database Migrations

The :class:`docuflow.database.Database` class supports raw SQL migrations. Place
``.sql`` files in ``src/docuflow/migrations`` or provide a custom path to
:py:meth:`Database.migrate`. Each file is executed once and recorded in the
``schema_versions`` table.
