# 0004 - Continuous Integration and Agent Workflow

## Status
Accepted

## Context
The project follows the Codex multi-agent development process. A basic CI setup
is required to trigger agents and enforce the dev gate for every push.

## Decision
* Add `.github/workflows/agents.yml` as the router workflow that calls the
  Codex API based on the `ready-for:` label found in the latest commit message.
* Provide a helper script `scripts/next-agent.sh` that sets the `NEXT_AGENT`
  environment variable for the workflow.
* Keep `.github/workflows/ci.yml` running the lint, type check, security scan,
  and test suite defined in the dev gate.
* Introduce `.pre-commit-config.yaml` so contributors run the same checks locally.

## Consequences
* Agent handoffs are automated through GitHub Actions.
* Contributors get immediate feedback via pre-commit and CI.
