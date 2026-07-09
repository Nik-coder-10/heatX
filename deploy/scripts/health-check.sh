#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Comprehensive Health Check
# Usage: ./deploy/scripts/health-check.sh [--json] [--verbose]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_JSON=false
VERBOSE=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Results accumulator
results=()
passed=0
failed=0
warnings=0

check() {
    local name="$1"
    local command="$2"
    local severity="${3:-error}"

    if eval "$command" 2>/dev/null; then
        results+=("{\"name\":\"$name\",\"status\":\"passed\",\"severity\":\"$severity\"}")
        passed=$((passed + 1))
        if [ "$VERBOSE" = true ] || [ "$OUTPUT_JSON" = false ]; then
            echo -e "  ${GREEN}[PASS]${NC} $name"
        fi
    else
        if [ "$severity" = "warning" ]; then
            results+=("{\"name\":\"$name\",\"status\":\"warning\",\"severity\":\"$severity\"}")
            warnings=$((warnings + 1))
            if [ "$VERBOSE" = true ] || [ "$OUTPUT_JSON" = false ]; then
                echo -e "  ${YELLOW}[WARN]${NC} $name"
            fi
        else
            results+=("{\"name\":\"$name\",\"status\":\"failed\",\"severity\":\"$severity\"}")
            failed=$((failed + 1))
            if [ "$VERBOSE" = true ] || [ "$OUTPUT_JSON" = false ]; then
                echo -e "  ${RED}[FAIL]${NC} $name"
            fi
        fi
    fi
}

echo_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "$@"
    fi
}

echo ""
if [ "$OUTPUT_JSON" = false ]; then
    echo "=========================================="
    echo "  Urban Heat Platform - Health Check"
    echo "=========================================="
    echo ""
fi

# ===== Docker Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Docker ===${NC}"; fi
check "Docker daemon" "docker info &>/dev/null"
echo_verbose "  Docker: $(docker --version 2>/dev/null)"

# ===== Container Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Containers ===${NC}"; fi

CONTAINERS=("urbanheat-postgres" "urbanheat-redis" "urbanheat-minio" "urbanheat-backend" "urbanheat-frontend" "urbanheat-nginx")

for container in "${CONTAINERS[@]}"; do
    check "$container running" "docker ps --filter 'name=$container' --filter 'status=running' --format '{{.Names}}' | grep -q '$container'"
done

# Check healthy status for containers with healthcheck
for container in "${CONTAINERS[@]}"; do
    if docker inspect "$container" &>/dev/null; then
        health_status=$(docker inspect "$container" --format '{{.State.Health.Status}}' 2>/dev/null || echo "none")
        if [ "$health_status" != "none" ]; then
            check "$container health ($health_status)" "docker inspect '$container' --format '{{.State.Health.Status}}' | grep -q 'healthy'"
        fi
    fi
done

# ===== Database Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Database ===${NC}"; fi
check "PostgreSQL ping" "docker exec urbanheat-postgres pg_isready -U postgres &>/dev/null"
check "PostGIS extension" "docker exec urbanheat-postgres psql -U postgres -d urbanheat -c 'SELECT PostGIS_version();' &>/dev/null" "warning"
check "DB connection count" "docker exec urbanheat-postgres psql -U postgres -d urbanheat -c 'SELECT count(*) FROM pg_stat_activity;' &>/dev/null"

# ===== Redis Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Redis ===${NC}"; fi
check "Redis ping" "docker exec urbanheat-redis redis-cli ping | grep -q 'PONG'"
check "Redis memory" "docker exec urbanheat-redis redis-cli INFO memory | grep -q 'used_memory:'"

# ===== API Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== API ===${NC}"; fi
check "Backend API" "curl -sf http://localhost:8000/api/v1/health &>/dev/null || curl -sf http://localhost/api/v1/health &>/dev/null"
check "API docs" "curl -sf http://localhost:8000/api/v1/openapi.json &>/dev/null || curl -sf http://localhost/api/v1/openapi.json &>/dev/null" "warning"

# ===== Frontend Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Frontend ===${NC}"; fi
check "Frontend HTML" "curl -sf http://localhost/ | grep -q 'html' &>/dev/null || curl -sf http://localhost:5173/ | grep -q 'html' &>/dev/null"

# ===== MinIO Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Storage ===${NC}"; fi
check "MinIO health" "curl -sf http://localhost:9000/minio/health/live &>/dev/null"

# ===== Monitoring Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Monitoring ===${NC}"; fi
check "Prometheus" "curl -sf http://localhost:9090/-/ready &>/dev/null" "warning"
check "Grafana" "curl -sf http://localhost:3000/api/health &>/dev/null" "warning"
check "Loki" "curl -sf http://localhost:3100/ready &>/dev/null" "warning"

# ===== Network Health =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Network ===${NC}"; fi
check "Network connectivity" "docker network inspect urbanheat-network &>/dev/null" "warning"

# ===== System Resources =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== System Resources ===${NC}"; fi
check "Disk space > 20%" "df / | tail -1 | awk '{print \$5}' | sed 's/%//' | awk '{exit \$1 > 80}'"
check "Memory available" "free | grep Mem | awk '{print \$7/\$2 * 100}' | awk '{exit \$1 < 10}'" "warning"

# ===== Security =====
if [ "$OUTPUT_JSON" = false ]; then echo -e "\n${BLUE}=== Security ===${NC}"; fi
check "HTTPS configured" "curl -sfI https://localhost 2>/dev/null | grep -q 'HTTP/2 200\|HTTP/1.1 200'" "warning"
check "Security headers" "curl -sfI http://localhost 2>/dev/null | grep -qi 'X-Frame-Options\|Strict-Transport-Security'" "warning"

# ===== Results =====
total=$((passed + failed + warnings))
readiness_score=$(( (passed * 100) / (total > 0 ? total : 1) ))

if [ "$OUTPUT_JSON" = true ]; then
    echo "{"
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"passed\": $passed,"
    echo "  \"failed\": $failed,"
    echo "  \"warnings\": $warnings,"
    echo "  \"total\": $total,"
    echo "  \"readiness_score\": $readiness_score,"
    echo "  \"checks\": ["
    local first=true
    for result in "${results[@]}"; do
        if [ "$first" = true ]; then first=false; else echo ","; fi
        echo -n "    $result"
    done
    echo ""
    echo "  ]"
    echo "}"
else
    echo ""
    echo "=========================================="
    echo "  Health Check Summary"
    echo "=========================================="
    echo ""
    echo -e "  ${GREEN}Passed: $passed${NC}"
    echo -e "  ${RED}Failed: $failed${NC}"
    echo -e "  ${YELLOW}Warnings: $warnings${NC}"
    echo -e "  Total: $total"
    echo ""
    if [ "$readiness_score" -ge 90 ]; then
        echo -e "  Readiness Score: ${GREEN}$readiness_score/100${NC}"
    elif [ "$readiness_score" -ge 70 ]; then
        echo -e "  Readiness Score: ${YELLOW}$readiness_score/100${NC}"
    else
        echo -e "  Readiness Score: ${RED}$readiness_score/100${NC}"
    fi
    echo ""
    echo "=========================================="
    echo ""
fi

exit $((failed > 0 ? 1 : 0))
