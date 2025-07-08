# 0007 - Infrastructure and Monitoring Layout

## Status
Accepted

## Context
The repository contains Terraform templates and Grafana alerts but previous ADRs
focus mainly on application code. We need a record that explains why these
folders live in the monorepo and how they relate to deployments.

## Decision
* Keep infrastructure definitions under `iac/` so contributors can deploy
  optional AWS services without leaving the repository.
* Store alert rules and dashboards under `monitoring/` to provide basic
  observability out of the box.
* Both folders are treated as reference implementations. They are not required
  for local development but help teams reuse tested configurations.

## Consequences
* CI does not automatically apply these templates; operators run them manually.
* Including the files in the monorepo simplifies documentation and keeps
  configuration close to the code it observes.
