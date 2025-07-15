# Dev Security Notes

This file documents our local scanning steps so developers can reproduce the CI checks.

1. **Static analysis**: run `bandit -r src -lll` and save the output to `.dev/BANDIT.md`.
2. **Dependency audit**: run `pip-audit -r requirements.txt` and append the results to `.dev/BANDIT.md`.
3. **Semgrep**: run `semgrep --config p/ci` when network access is available; results are also recorded in `.dev/BANDIT.md`.

These steps keep our security documentation up to date.
