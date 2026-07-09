#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Redis Health Check
# =============================================================================

set -euo pipefail

REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

check_redis() {
    local cmd
    if [ -n "$REDIS_PASSWORD" ]; then
        cmd="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a '$REDIS_PASSWORD' ping"
    else
        cmd="redis-cli -h $REDIS_HOST -p $REDIS_PORT ping"
    fi

    local result
    result=$(eval "$cmd" 2>/dev/null)

    if [ "$result" = "PONG" ]; then
        echo "Redis health check: OK"
        return 0
    else
        echo "Redis health check: FAILED (response: $result)"
        return 1
    fi
}

check_memory() {
    local cmd
    if [ -n "$REDIS_PASSWORD" ]; then
        cmd="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a '$REDIS_PASSWORD' INFO memory"
    else
        cmd="redis-cli -h $REDIS_HOST -p $REDIS_PORT INFO memory"
    fi

    local used_memory
    used_memory=$(eval "$cmd" 2>/dev/null | grep "used_memory_human:" | cut -d: -f2)
    local max_memory
    max_memory=$(eval "$cmd" 2>/dev/null | grep "maxmemory_human:" | cut -d: -f2)

    echo "Redis memory: used=${used_memory:-unknown}, max=${max_memory:-unknown}"
}

main() {
    if check_redis; then
        check_memory
        exit 0
    else
        exit 1
    fi
}

main "$@"
