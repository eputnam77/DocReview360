# 0009 - Quality Gates and Tooling Choices

## Status
Accepted

## Context
The multi‑agent workflow relies on automated checks to keep code quality high. While `agents.yml` triggers the next Codex agent, the exact lint, type and security checks were not formally documented yet. Capturing these gates ensures future contributors understand why CI fails and how to run the tools locally.

## Decision
* Adopt two quality gates:
  * **Dev Gate** runs on feature branches and requires 70 % unit test coverage.
  * **Release Gate** runs on `main` and raises the bar to 90 % coverage plus documentation build.
* Tools executed in both gates are `ruff`, `black`, `mypy --strict`, `bandit`, `pip-audit`, and `pytest` with coverage.
* GitHub Actions (`ci.yml`) enforces the dev gate on every push. Additional workflows call the Codex API based on labels for agent handoff.
* A `.pre-commit-config.yaml` file mirrors these checks so developers can lint and test before pushing.

## Consequences
* Merge requests failing the gate hand over control to the **fixer** agent.
* Contributors know which commands to run locally and can reproduce CI failures easily.
* The repository documents its quality policy, helping new maintainers adopt the same standards.
