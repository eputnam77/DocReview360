#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# db_backup.sh — Encrypted database backup for DocReview360.
#
# Usage:
#   BACKUP_PASSPHRASE=<secret> ./scripts/db_backup.sh [output_dir]
#
# The script auto-detects the database backend from DOCREVIEW360_DATABASE_URL
# and writes an AES-256-CBC encrypted, gzip-compressed dump to OUTPUT_DIR.
#
# To restore a SQLite backup:
#   openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE \
#     -in backup.sql.gz.enc | gunzip | sqlite3 restored.db
#
# To restore a PostgreSQL backup:
#   openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE \
#     -in backup.sql.gz.enc | gunzip | psql "$DOCREVIEW360_DATABASE_URL"

set -euo pipefail

DB_URL="${DOCREVIEW360_DATABASE_URL:-sqlite:///docreview360.db}"
OUTPUT_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)

if [[ -z "${BACKUP_PASSPHRASE:-}" ]]; then
  echo "[backup] ERROR: BACKUP_PASSPHRASE environment variable is required." >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

if [[ "${DB_URL}" == sqlite* ]]; then
  DB_PATH="${DB_URL#sqlite:///}"
  # Handle absolute paths (sqlite:////abs/path)
  if [[ "${DB_URL}" == sqlite:////* ]]; then
    DB_PATH="/${DB_URL#sqlite:////}"
  fi
  BACKUP_FILE="${OUTPUT_DIR}/docreview360_${TIMESTAMP}.sql.gz.enc"
  echo "[backup] SQLite: dumping ${DB_PATH} → ${BACKUP_FILE}"
  sqlite3 "${DB_PATH}" .dump \
    | gzip \
    | openssl enc -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE \
    > "${BACKUP_FILE}"

elif [[ "${DB_URL}" == postgresql* || "${DB_URL}" == postgres* ]]; then
  BACKUP_FILE="${OUTPUT_DIR}/docreview360_${TIMESTAMP}.sql.gz.enc"
  echo "[backup] PostgreSQL: pg_dump → ${BACKUP_FILE}"
  pg_dump "${DB_URL}" \
    | gzip \
    | openssl enc -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE \
    > "${BACKUP_FILE}"

elif [[ "${DB_URL}" == mysql* ]]; then
  echo "[backup] MySQL: use mysqldump directly with --single-transaction, then pipe through" >&2
  echo "         gzip | openssl enc -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE" >&2
  exit 1

elif [[ "${DB_URL}" == mssql* ]]; then
  echo "[backup] MSSQL: use SQL Server Agent or sqlcmd with vendor backup tools." >&2
  exit 1

elif [[ "${DB_URL}" == oracle* ]]; then
  echo "[backup] Oracle: use expdp (Data Pump) for production backups." >&2
  exit 1

else
  echo "[backup] ERROR: unrecognised database URL scheme in DOCREVIEW360_DATABASE_URL." >&2
  exit 1
fi

BACKUP_SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
echo "[backup] Done: ${BACKUP_FILE} (${BACKUP_SIZE})"
echo "[backup] Restore command:"
echo "  openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE \\"
echo "    -in ${BACKUP_FILE} | gunzip | sqlite3 restored.db"
