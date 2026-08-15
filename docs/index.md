# DocReview360 — open-source document review and approval workflow software

DocReview360 is self-hosted document review software for technical and regulated documents. It routes documents through drafting, collaborative review, approval, and publication — with document version control, inline review comments, and a verifiable audit trail of every step.

```
Draft  →  Review  →  Resolve  →  Approve  →  Publish
```

This documentation is for administrators, deployers, and developers. If you review or author documents in the web app, open **Help & Support** in the sidebar instead.

## Get started

| I want to | Go to |
| --- | --- |
| Run DocReview360 on my machine | [Get started](getting_started.md) |
| Deploy to production | [Deployment](deployment.md) |
| Work through a realistic example | [Usage scenarios](scenarios.md) |
| Contribute code | [Developer guide](developer.md) |
| Decide if this is the right tool | [Comparison](comparison.md) |

## What DocReview360 does

Authors draft in a rich-text editor with autosave and revision history. Reviewers comment inline. Approvers sign off in the order the workflow defines. Every action lands in a hash-chained audit log.

![Project list showing documents, types, and review status](images/projects.png)

Core capabilities:

- **Projects and documents** — import DOCX, PDF, HTML, or Markdown; track revisions with SHA-256 hashes.
- **Workflows and approvals** — sequential or parallel phases, reminders, escalations, and digital signatures.
- **Roles and permissions** — role-based access control enforced on every endpoint.
- **Audit and compliance** — tamper-evident logs, retention policies, and export controls.
- **Document quality** — validate documents against federal writing standards.

## Configure

| Topic | Description |
| --- | --- |
| [Environment variables](environment_variables.md) | Secrets, database paths, and runtime flags. |
| [Settings reference](settings.md) | Everything in `settings.yaml`. |
| [RBAC configuration](rbac_configuration.md) | Roles, permissions, and assignment. |
| [Approval assignments](approval_assignments.md) | How approvers are chosen per phase. |

## Operate

| Topic | Description |
| --- | --- |
| [Observability](observability.md) | Metrics, logs, and monitoring. |
| [Disaster recovery](disaster_recovery.md) | Backup and restore runbook. |
| [Key rotation](security/key-rotation.md) | Rotate signing and encryption keys. |
| [Patch flow](security/patch-flow.md) | Triage and ship dependency fixes. |
| [Data retention and deletion](data_retention_and_deletion.md) | Retention windows and purge jobs. |
| [Migration policy](migration_policy.md) | Schema change rules. |
| [Air-gap deployment](air_gap_deployment.md) | Install without internet access. |
| [Blue-green deployment](blue_green_deployment.md) | Release without downtime. |

## Reference

| Topic | Description |
| --- | --- |
| [CLI reference](cli.md) | Every `docreview360` command. |
| [API overview](api_overview.md) | Authentication, endpoints, and versioning. |
| [Architecture decisions](adr/0001-core-architecture.md) | Why the system is built this way. |
| [Supported platforms](supported-platforms.md) | Tested operating systems and versions. |
| [Testing and quality](testing_and_quality.md) | Test suites, coverage gates, and scans. |
| [Changelog](changelog.md) | Shipped versions and release history. |

## Where content lives

Administrator and operator guidance belongs in `docs/`. End-user how-to content belongs in the in-app help page (`frontend/pages/help.tsx`) so it ships with the UI.

## License

DocReview360 is released under the MIT License. See [`LICENSE`](https://github.com/eputnam77/DocReview360/blob/main/LICENSE).
