# 0009 - Infrastructure and Monitoring

## Status
Accepted

## Context
Terraform modules and Grafana dashboards ship with the repository. These optional resources help teams deploy DocReview360 alongside observability tooling, but they are not required for local development.

## Decision
- Keep infrastructure code under `iac/` so operators can reuse tested Terraform modules.
- Store alert rules and dashboards under `monitoring/` as reference configurations.
- CI does not apply these templates automatically; deployment is a manual step.

## Consequences
Including infrastructure and monitoring assets in the monorepo keeps configuration close to the code it observes and simplifies documentation for ops teams.
