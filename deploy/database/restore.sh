#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Database Restore Script
# Restore PostgreSQL database from compressed dump
# Usage: ./restore.sh <backup_file>
# =============================================================================

set -euo pipefail

RESTORE_LOG="/var/log/urbanheat/restore.log"
DB_HOST="${POSTGRES_SERVER:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-urbanheat}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$RESTORE_LOG"
}

usage() {
    echo "Usage: $0 <backup_file.dump.gz>"
    echo ""
    echo "Options:"
    echo "  --dry-run    Validate backup file without restoring"
    exit 1
}

validate_backup() {
    local file="$1"

    if [ ! -f "$file" ]; then
        log "ERROR: Backup file not found: $file"
        return 1
    fi

    # Check gzip integrity
    if ! gzip -t "$file" 2>/dev/null; then
        log "ERROR: Backup file is corrupted or not a valid gzip"
        return 1
    fi

    # Check pg_dump format
    if ! gzip -dc "$file" | head -c 100 | grep -q "PGDMP"; then
        log "ERROR: File is not a valid pg_dump archive"
        return 1
    fi

    log "Backup file validated: $file"
    return 0
}

perform_restore() {
    local file="$1"
    local dry_run="${2:-false}"

    log "WARNING: About to restore database '$DB_NAME' on $DB_HOST:$DB_PORT"
    log "This will DROP all existing data!"
    log ""
    log "Backup file: $file"
    log "Size: $(du -h "$file" | cut -f1)"
    log ""

    if [ "$dry_run" = "true" ]; then
        log "DRY RUN - Validation passed, no restore performed"
        return 0
    fi

    # Confirm
    echo -n "Are you sure you want to continue? [y/N]: "
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log "Restore cancelled by user"
        exit 0
    fi

    log "Starting restore..."

    # Terminate existing connections
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '$DB_NAME'
        AND pid <> pg_backend_pid();
    " 2>/dev/null || true

    # Drop and recreate database
    log "Dropping existing database..."
    PGPASSWORD="$DB_PASSWORD" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME"
    log "Creating fresh database..."
    PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

    # Restore
    log "Restoring data..."
    gzip -dc "$file" | PGPASSWORD="$DB_PASSWORD" pg_restore \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-owner \
        --no-acl \
        --exit-on-error \
        2>>"$RESTORE_LOG"

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        log "Restore completed successfully"
    else
        log "ERROR: Restore failed with exit code $exit_code"
        return 1
    fi
}

main() {
    local dry_run="false"

    if [ $# -lt 1 ]; then
        usage
    fi

    if [ "$1" = "--dry-run" ]; then
        dry_run="true"
        shift
    fi

    local backup_file="$1"

    log "=== Restore Run Started ==="
    log "Database: $DB_NAME on $DB_HOST:$DB_PORT"

    if validate_backup "$backup_file"; then
        if perform_restore "$backup_file" "$dry_run"; then
            log "=== Restore Run Completed Successfully ==="
        else
            log "=== Restore Run FAILED ==="
            exit 1
        fi
    else
        log "=== Restore Run FAILED - Invalid backup ==="
        exit 1
    fi
}

main "$@"
