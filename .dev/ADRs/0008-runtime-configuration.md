# 0008 - Runtime Configuration File

## Status
Accepted

## Context
Developers need a simple way to tweak authentication, database and service options when running DocReview360 locally or deploying in different environments. A small YAML file already lives at the repository root but its purpose is undocumented.

## Decision
* Use `docuflow.yaml` at the repository root as the default configuration file.
* Load this file on startup to configure the FastAPI server, database connection and optional integrations.
* Encourage contributors to copy it and override values rather than committing environment specific secrets.
* Provide `docker-compose.yml` for a local stack that reads the same configuration.

## Consequences
* New environments only need to supply a customised YAML file to adapt DocReview360.
* The configuration approach stays lightweight without introducing a complex settings library.
