#!/usr/bin/env bash
# Database backup script for PlexAddons PostgreSQL
# Usage: ./scripts/backup-db.sh [backup_dir]
#
# Environment variables:
#   DB_HOST       - PostgreSQL host (default: localhost)
#   DB_PORT       - PostgreSQL port (default: 5432)
#   DB_NAME       - Database name (default: plexaddons)
#   DB_USER       - Database user (default: plexaddons)
#   PGPASSWORD    - Database password (must be set)
#   BACKUP_DIR    - Backup directory (default: ./backups)
#   RETENTION_DAYS - Number of days to keep backups (default: 30)
#
# Can be run as a cron job:
#   0 3 * * * /path/to/scripts/backup-db.sh >> /var/log/plexaddons-backup.log 2>&1

set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-plexaddons}"
DB_USER="${DB_USER:-plexaddons}"
BACKUP_DIR="${1:-${BACKUP_DIR:-./backups}}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

if [ -z "${PGPASSWORD:-}" ]; then
    echo "ERROR: PGPASSWORD environment variable must be set"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Starting backup of ${DB_NAME}..."

# Dump and compress
pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_FILE"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date -Iseconds)] Backup complete: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Clean old backups
if [ "$RETENTION_DAYS" -gt 0 ]; then
    DELETED=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete -print | wc -l)
    if [ "$DELETED" -gt 0 ]; then
        echo "[$(date -Iseconds)] Cleaned ${DELETED} backup(s) older than ${RETENTION_DAYS} days"
    fi
fi

echo "[$(date -Iseconds)] Done."
