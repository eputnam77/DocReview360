# Disaster Recovery Runbook

This runbook validates that backup and restore workflows recover critical state before release.

## Scope

The simulation validates recovery of:
- project-linked documents
- document version history
- audit log entries required for traceability

## RTO and RPO assumptions

- Target RTO: 60 minutes for a standard single-environment restore.
- Target RPO: 24 hours based on daily backup cadence.

Adjust these values to your operating requirements.

## Prerequisites

- Python environment with project dependencies installed.
- Write access to a temporary workspace path.

## Procedure

1. Run the simulation:

```bash
python scripts/simulate_disaster_recovery.py --backup-path .tmp/dr-simulation.json.gz
```

2. Confirm output reports successful restoration of project linkage, version count, and log entries.
3. Archive the command output in release evidence.

## Failure handling

If the simulation fails:
- block release
- inspect backup configuration and restore logs
- rerun after remediation

## Release evidence checklist

- simulation command and timestamp
- backup artifact path used during simulation
- successful restore summary output
- reviewer sign-off
