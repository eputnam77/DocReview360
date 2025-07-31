# Repository Layout

```
DocReview360/
├── src/                  # Python package `docreview360`
├── tests/                # Unit and integration tests
├── frontend/             # Next.js frontend application
├── services/             # Optional microservices
├── plugins/              # Third-party extensions
├── iac/                  # Infrastructure as Code modules
├── monitoring/           # Grafana and alert rules
├── docs/                 # MkDocs documentation
├── migrations/           # SQL migration scripts applied at startup
├── scripts/              # Developer tools and CI helpers
├── .github/              # GitHub workflow definitions
└── .dev/                 # ADRs, TASKS, templates and planning docs
```

`migrations/` lives at the repository root so the lightweight
`Database.migrate()` helper can run raw SQL files without packaging
them. Python dependencies are defined in `pyproject.toml` and locked by
`poetry.lock`. CI jobs cache the `.venv` directory using the lockfile
hash so repeated runs are fast and deterministic.
