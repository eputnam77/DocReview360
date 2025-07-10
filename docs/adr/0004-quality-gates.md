# 0004 - Quality Gates Overview

This ADR summarises the lint, type and security checks defined in `.dev/ADRs/0009-quality-gates.md`. The project enforces a **Dev Gate** with 70 % coverage on feature branches and a stricter **Release Gate** on `main`. Both gates run `ruff`, `black`, `mypy`, `bandit`, `pip-audit` and the test suite. GitHub Actions handles these steps automatically, while `.pre-commit-config.yaml` lets developers run them locally.
