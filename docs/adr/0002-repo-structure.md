# 0002 - Repository Layout Overview

## Status
Accepted

## Context
Several directories store optional infrastructure and monitoring assets. Users
of the open-source package might wonder why these exist alongside the Python
code and frontend.

## Decision
The repository keeps a single monorepo so contributors can access code, examples,
Terraform modules and dashboards in one place. The main folders are:

```text
src/         - Python package
frontend/    - Next.js application
services/    - Additional microservices
plugins/     - Editor and exporter extensions
iac/         - Terraform templates
monitoring/  - Grafana alerts and dashboards
examples/    - Example workflows and sample data
scripts/     - Helper utilities for CI and development
p/           - Semgrep rulesets for SAST
```

Development files under `.dev/` are excluded from packages, while CI workflows
reside in `.github/`. Documentation lives in `docs/` and is built with MkDocs.

## Consequences
This layout favors discoverability over a minimal distribution tarball.
Optional pieces can be ignored during installation but remain documented and
tested alongside the code.
