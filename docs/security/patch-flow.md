# Patch and Upgrade Process

This guide outlines the security patch flow used by the DocuFlow project.

## Overview

1. **Renovate Bot** automatically opens PRs for outdated dependencies.
2. **Trivy** and **Grype** run in CI to detect vulnerabilities.
3. Critical CVEs trigger the incident response workflow in Slack and the FedRAMP POA&M template.
4. Hot-fix releases are published following semantic versioning.

