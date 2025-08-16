# Security Compliance Overview

This document outlines the basic data flow and encryption strategy for DocReview360.
All user content is stored in encrypted backups and retained according to the
project retention policy. The diagrams below show how information moves through
the system and when it is removed.

See [FedRAMP Controls Mapping](fedramp_controls.md) for a table of related compliance controls.

## Retention Defaults

Audit logs and archived document snapshots are automatically purged after a
configurable retention period. By default audit logs are retained for 90 days
and archives for 365 days. These values can be adjusted in ``settings.yaml``::

    audit_log:
      retention_days: 90
      purge_interval_minutes: 1440
    archive:
      retention_days: 365
      purge_interval_minutes: 1440

Reducing the retention period will cause a scheduled purge job to remove items
older than the configured number of days. Increasing the interval allows less
frequent purge runs if desired.
