#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Database Backup Script
# Automated PostgreSQL backup with retention, compression, and optional S3 sync
# =============================================================================

set -euo pipefail

# ===== Configuration =====
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DB_HOST="${POSTGRES_SERVER:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-urbanheat}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
DATE_TAG=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE_TAG}.dump.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"
S3_PATH="s3://${S3_BUCKET}/database/"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

cleanup_old() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    find "$BACKUP_DIR" -name "${DB_NAME}_*.dump.gz" -type f -mtime "+${RETENTION_DAYS}" -delete
    log "Cleanup complete"
}

perform_backup() {
    log "Starting backup: ${DB_NAME} -> ${BACKUP_FILE}"

    mkdir -p "$BACKUP_DIR"

    # Perform compressed pg_dump
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --format=custom \
        --verbose \
        --no-owner \
        --no-acl \
        2>>"$LOG_FILE" \
    | gzip -9 > "$BACKUP_FILE"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        local size
        size=$(du -h "$BACKUP_FILE" | cut -f1)
        log "Backup completed successfully: ${size}"
    else
        log "ERROR: Backup failed with exit code $exit_code"
        rm -f "$BACKUP_FILE"
        return 1
    fi
}

sync_to_s3() {
    if [ -n "$S3_BUCKET" ]; then
        log "Syncing to S3: ${S3_PATH}"
        if aws s3 cp "$BACKUP_FILE" "$S3_PATH" --storage-class STANDARD_IA 2>>"$LOG_FILE"; then
            log "S3 sync complete"
        else
            log "WARNING: S3 sync failed"
        fi
    else
        log "S3 sync not configured (S3_BACKUP_BUCKET not set)"
    fi
}

verify_backup() {
    log "Verifying backup integrity..."
    if gzip -t "$BACKUP_FILE" 2>/dev/null; then
        log "Backup integrity check passed"
        return 0
    else
        log "ERROR: Backup integrity check failed"
        return 1
    fi
}

main() {
    log "=== Backup Run Started ==="

    if perform_backup && verify_backup; then
        cleanup_old
        sync_to_s3
        log "=== Backup Run Completed Successfully ==="
    else
        log "=== Backup Run FAILED ==="
        exit 1
    fi
}

main "$@"
