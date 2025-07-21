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

Our CI pipeline runs **Bandit**, **pip-audit**, and **npm audit**. Containers are scanned with Trivy and Grype when available.

## Patch Policy

If **pip-audit** or our nightly security workflow flags a high-severity vulnerability we issue a hotfix within **48 hours**. Medium issues are addressed in the next regular release.

## Disclosure Guidance

We encourage responsible disclosure. Please avoid posting public issues for new vulnerabilities until we have published a fix. Coordinate with us at [security@example.com](mailto:security@example.com).

Refer to [.dev/BANDIT.md](.dev/BANDIT.md) for the latest automated scan results.
Dependency-Check runs when the tool is available; network restrictions may skip this step.
