#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Database Migration Script
# Runs Alembic migrations with health checks and rollback on failure
# =============================================================================

set -euo pipefail

MIGRATE_LOG="/var/log/urbanheat/migrate.log"
ALEMBIC_CFG="/app/alembic.ini"
MAX_RETRIES=5
RETRY_DELAY=5

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$MIGRATE_LOG"
}

wait_for_db() {
    log "Waiting for database..."
    local retries=0
    until pg_isready -h "$POSTGRES_SERVER" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" 2>/dev/null; do
        retries=$((retries + 1))
        if [ "$retries" -ge "$MAX_RETRIES" ]; then
            log "ERROR: Database not reachable after $MAX_RETRIES attempts"
            exit 1
        fi
        log "Attempt $retries/$MAX_RETRIES - retrying in ${RETRY_DELAY}s..."
        sleep "$RETRY_DELAY"
    done
    log "Database is reachable"
}

run_migrations() {
    log "Running database migrations..."
    cd /app

    # Try to upgrade, capture exit code
    if alembic -c "$ALEMBIC_CFG" upgrade head 2>>"$MIGRATE_LOG"; then
        log "Migrations applied successfully"
        alembic -c "$ALEMBIC_CFG" current 2>&1 | tee -a "$MIGRATE_LOG"
        return 0
    else
        log "ERROR: Migration failed"
        log "Attempting rollback to last known good state..."
        alembic -c "$ALEMBIC_CFG" downgrade -1 2>>"$MIGRATE_LOG" || true
        return 1
    fi
}

check_pending() {
    log "Checking for pending migrations..."
    local pending
    pending=$(alembic -c "$ALEMBIC_CFG" check 2>&1 || true)
    if echo "$pending" | grep -q "No new revisions"; then
        log "No pending migrations"
        return 0
    else
        log "Pending migrations detected"
        return 1
    fi
}

main() {
    log "=== Migration Run Started ==="
    log "Environment: ${ENVIRONMENT:-unknown}"
    log "Database: $POSTGRES_SERVER:$POSTGRES_PORT/$POSTGRES_DB"

    wait_for_db

    if ! check_pending; then
        if run_migrations; then
            log "Migration completed successfully"
        else
            log "FATAL: Migration failed, exiting"
            exit 1
        fi
    else
        log "No migrations needed"
    fi

    log "=== Migration Run Completed ==="
}

main "$@"
