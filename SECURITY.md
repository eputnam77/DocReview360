# Security Policy

We take the security of DocReview360 seriously. Please report suspected
vulnerabilities so we can fix them quickly.

## Supported Versions

Only the latest release receives security patches. Please upgrade when new versions become available.

## Reporting a Vulnerability

Send an email to [security@example.com](mailto:security@example.com) with a clear
description of the issue or open a private GitHub issue if possible. We aim to
respond within **three business days**.

For details on how we triage and patch dependencies see the
[patch and upgrade guide](docs/security/patch-flow.md).

## Security Scans

Our CI pipeline runs **Bandit** and **pip-audit** on every commit to detect
common issues. Containers are also scanned with Trivy and Grype as described in
the patch guide.
