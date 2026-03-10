# Disaster Recovery Runbook

This runbook validates that backup and restore workflows recover critical state before release.

## Scope

The simulation validates recovery of:
- project-linked documents
- document version history
- audit log entries required for traceability

## RTO and RPO targets

| Tier | Scenario | RTO | RPO |
|------|----------|-----|-----|
| Critical | Database corruption / host loss | 4 hours | 1 hour |
| High | Redis / queue failure | 15 minutes | 0 (stateless queue) |
| Medium | Single container crash | 2 minutes (auto-restart) | 0 |
| Low | Scheduled maintenance | Planned window | 0 |

RPO of 1 hour requires: daily encrypted backup (`scripts/db_backup.sh`) **plus** PostgreSQL WAL archiving (or equivalent). SQLite-only deployments have a RPO equal to backup frequency.

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

## Recovery Procedures

### Database Restore from Encrypted Backup

```bash
# 1. Stop writes
docker compose -f docker-compose.prod.yml stop web worker beat

# 2. Decrypt and restore (SQLite)
BACKUP_PASSPHRASE="$(cat /run/secrets/backup_passphrase)" \
  openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE \
  -in /backups/docreview360_<timestamp>.sql.gz.enc \
  | gunzip | sqlite3 docreview360_restored.db

# 3. (PostgreSQL) Restore from dump
BACKUP_PASSPHRASE="..." \
  openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE \
  -in /backups/docreview360_<timestamp>.sql.gz.enc \
  | gunzip | psql "$DOCREVIEW360_DATABASE_URL"

# 4. Verify audit log chain integrity
python -c "from docreview360.logs import verify_audit_log_chain; \
           ok, broken = verify_audit_log_chain(); \
           print('CHAIN OK' if ok else f'BROKEN: {broken}')"

# 5. Restart and verify
docker compose -f docker-compose.prod.yml start web worker beat
curl -sf https://docreview360.example.gov/health/ready && echo "READY"
```

### Redis Failure

```bash
docker compose -f docker-compose.prod.yml restart redis
# If data volume corrupt:
docker compose -f docker-compose.prod.yml stop worker beat redis
docker volume rm docreview360_redis_data
docker compose -f docker-compose.prod.yml up -d redis worker beat
```

The rate limiter automatically falls back to in-memory mode during Redis outages.

### Communication Timeline

| Time | Action |
|------|--------|
| T+0 | Detect; open incident ticket |
| T+15m | Notify affected users |
| T+1h | Status update |
| T+4h | RTO deadline or escalate |
| T+24h | Post-incident review |

## Release evidence checklist

- simulation command and timestamp
- backup artifact path used during simulation
- successful restore summary output
- audit log chain verification output
- reviewer sign-off
