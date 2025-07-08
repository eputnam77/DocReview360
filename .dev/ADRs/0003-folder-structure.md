# 0003 - Repository Structure and Templates

## Status
Accepted

## Context
The project currently lacks guidance on where to place documentation templates and additional tooling placeholders. The AGENTS playbook recommends storing development‑only files under `.dev/` and providing templates for documentation generation. These elements help future contributors maintain consistency and keep non‑distributed assets out of packages.

## Decision

* Create a `.dev/templates/` directory containing placeholder `README.md`, `API_DOCS.md`, and `CHANGELOG.md` files.
* Provide empty configuration files for TypeScript (`tsconfig.json`), Rust (`Cargo.toml`), and Go (`go.mod`) to prepare for multi‑language support.
* Ensure `pyproject.toml` excludes `.dev*` and test files from distribution and targets Python 3.12.
* Adopt a clear top‑level layout so contributors know where each language lives:

```text
DocuFlow/
├── src/            # Python package `docuflow`
├── tests/          # Python tests
├── frontend/       # Next.js application (TypeScript)
├── plugins/        # Language specific plugins
├── services/       # Optional microservices (Go/Rust)
├── iac/            # Terraform modules for infrastructure
├── monitoring/     # Grafana dashboards and alert rules
├── examples/       # Usage samples and demo data
├── docs/           # MkDocs documentation
├── scripts/        # Developer utilities
├── .github/        # GitHub workflows
└── .dev/           # ADRs, templates and planning docs
```

## Consequences

* Developers have a clear location for templates and cross‑language configuration.
* Packaging via `setuptools` will ignore development assets, keeping distributions clean.
* Future tooling can immediately build upon these placeholders without restructuring the repository.
