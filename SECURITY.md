# Security policy

We take the security of DocReview360 seriously. Report suspected vulnerabilities so we can fix them quickly.

## Supported versions

Only the latest release receives security patches. Upgrade when a new version becomes available.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/eputnam77/DocReview360/security/advisories/new) to submit a clear description of the issue. We aim to respond within **three business days**.

Please do not open a public issue for an unfixed vulnerability. Coordinate with us privately until a fix is published.

## Patch policy

We triage reported and scanner-detected vulnerabilities on this schedule:

| Severity | Target |
| --- | --- |
| High or critical | Hotfix release within **48 hours** of triage |
| Medium | Next regular release |
| Low | Next regular release, or deferred with a note in the advisory |

Dependabot is enabled for Python, npm, Docker, and GitHub Actions, and opens pull requests for known-vulnerable dependencies.

For how we triage and land dependency upgrades, see the [patch and upgrade guide](docs/security/patch-flow.md).

## Security scanning

These checks run against the codebase before a release:

| Check | Command | Covers |
| --- | --- | --- |
| Bandit | `bandit -r src -lll --skip B101` | Python code security issues |
| pip-audit | `python scripts/run-pip-audit.py` | Python dependency advisories |
| npm audit | `npm audit` in `frontend/` | Frontend dependency advisories |
| Semgrep | `python scripts/run_semgrep.py` | Static analysis rules |

Bandit and Semgrep also run as pre-commit hooks. Container image scanning with Trivy is available as a local step (`trivy fs .`) but is not part of an automated gate.

Run the full set before opening a pull request. See [Testing and quality](docs/testing_and_quality.md).

## Dependency pinning

- Python runtime dependencies are pinned in `pyproject.toml` and mirrored in `requirements.txt` for scanning.
- Frontend dependencies are pinned in `frontend/package-lock.json`.
- High-severity findings are patched on the expedited path described above.
