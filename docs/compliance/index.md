# Security Compliance Overview

This document outlines the basic data flow and encryption strategy for DocReview360.
All user content is stored in encrypted backups and retained according to the
project retention policy. The diagrams below show how information moves through
the system and when it is removed.

See [FedRAMP Controls Mapping](fedramp_controls.md) for a table of related compliance controls.
See [Standards Mapping](standards_mapping.md) for how verification features align with common standards.

## Retention Defaults

Operational logs, audit logs and archived document snapshots are automatically
purged after a configurable retention period. By default operational logs are
retained for 365 days and compliance audit logs for 2555 days (seven years).
Archives remain at 365 days. These values can be adjusted in ``settings.yaml``::

    logs:
      retention_days: 365
      purge_interval_minutes: 1440
    audit_log:
      retention_days: 2555
      purge_interval_minutes: 1440
    archive:
      retention_days: 365
      purge_interval_minutes: 1440

Reducing the retention period will cause a scheduled purge job to remove items
older than the configured number of days. Increasing the interval allows less
frequent purge runs if desired.

## Encryption at rest

DocReview360 encrypts archived artefacts, archive metadata, and backup files at
rest using AES-GCM envelope encryption. Each payload is wrapped with a versioned
header that includes magic bytes, a key identifier, and a nonce so operators can
rotate keys without re-encrypting existing data. Encrypted payloads are uploaded
to object storage; decryption happens on read paths such as backup restoration
using the key referenced in the header.

Key material is sourced from the vault or environment-backed secret flow, and
the active key identifier is configured in ``settings.yaml`` under
``security.encryption_at_rest``. Missing or invalid key material blocks restore
operations and surfaces a clear error so operators can correct vault
configuration quickly.

## Audit log integrity monitoring

DocReview360 continuously validates audit log append operations. If a malformed
entry or an HMAC verification failure is encountered the platform emits an
``audit_log_corruption_detected`` event, triggers an immediate audit log hash
refresh and re-runs the SharePoint integrity task. Operators can monitor the
event stream or alerting pipelines for this action to quickly investigate
tampering attempts.
