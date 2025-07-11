# 0001 - Core Architecture

## Status
Accepted

## Context
DocReview360 integrates a Python FastAPI backend, a React/Next.js front end, and auxiliary
services for search, task queues and storage.  Early ADRs live under `.dev/ADRs/` but
this record summarises the agreed monorepo layout for end users.

## Decision
- Source code resides in `src/` with the `docuflow` package.
- Automated tests live in `tests/`.
- External services (future Rust or Go components) will live under `services/`.
- Development-only artifacts remain under `.dev/`.
- Continuous integration is defined in `.github/workflows/`.

The following C4 container diagram illustrates the high level design.

```mermaid
graph TD
    subgraph DocReview360
        A[React UI]\nNext.js
        B[API Server]\nFastAPI
        C[Database]\nPostgreSQL
        D[Task Queue]\nCelery/Redis
    end
    Admin((Admin)) --> A
    User((User)) --> A
    A --> B
    B --> C
    B --> D
```

## Consequences
This layout keeps runtime and developer assets separated and allows additional
microservices to be added under `services/` without disrupting the Python
package.  Documentation under `docs/` remains user-facing and can link to this
ADR for architecture overview.
