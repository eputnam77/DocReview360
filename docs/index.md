# DocReview360 Documentation

This documentation set is primarily for **administrators, deployers, and developers** who run and maintain DocReview360.

If you are an end user (reviewer/author) using the web app, use the in-app help page at `/help` from the sidebar (**Help & Support**).

## Start here (admin/operator path)

1. [Getting Started](getting_started.md) — local setup and first run.
2. [Deployment](deployment.md) — production deployment options.
3. [Security key rotation](security/key-rotation.md) and [security patch flow](security/patch-flow.md).
4. [Disaster Recovery](disaster_recovery.md) — backup and restore runbook.
5. [RBAC Configuration](rbac_configuration.md) — role and permission controls.
6. [Observability](observability.md) — metrics, logging, and monitoring.

## Technical references

- [CLI Reference](cli.md)
- [API Overview](api_overview.md)
- [Developer Guide](developer.md)
- [Migration Policy](migration_policy.md)
- [Data Retention and Deletion](data_retention_and_deletion.md)
- [Supported Platforms](supported-platforms.md)
- [Architecture Decision Records](adr/0001-core-architecture.md)

## Product/release notes

- [CHANGELOG](../CHANGELOG.md) is the source of truth for shipped versions and release history.

## About documentation ownership

- `docs/` is focused on administrator and operational guidance.
- End-user how-to content should live in the frontend help experience (`frontend/pages/help.tsx`) so it ships with the product UI.

## License

This project is released under the MIT License. See `LICENSE` for details.
