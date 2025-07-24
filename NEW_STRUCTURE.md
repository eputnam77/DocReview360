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

The `migrations/` directory is now at the repository root so that
`Database.migrate()` can pick up raw SQL files without packaging them.
Workflows rely on `pyproject.toml` and `poetry.lock` as the single
source of truth for Python dependencies.
