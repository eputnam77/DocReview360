# 0010 - Documentation Strategy

## Status
Accepted

## Context
DocReview360 contains a growing amount of end-user and developer documentation. Early ADRs mention placing docs in `docs/` but do not describe how user guides relate to the development records under `.dev/`. A clear policy helps new contributors find the right references and ensures the MkDocs site only contains user-facing material.

## Decision

* Keep **user-facing** documentation under `docs/` and build it with **MkDocs Material**.
* Store **development** records such as ADRs, templates and planning files under `.dev/`.
* Copy or summarise relevant ADRs into `docs/adr/` so the public site references important architectural choices without exposing internal discussions.
* The CI workflow builds the docs during the release gate to ensure the site remains valid.

## Consequences

* Contributors know where to place new guides and how to update the docs site.
* Internal planning files stay out of distribution packages.
* The public site can link directly to concise ADR summaries while detailed history lives in `.dev/ADRs`.
