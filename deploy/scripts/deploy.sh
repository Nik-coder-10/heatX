#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Single-Command Deployment Script
# Usage: ./deploy/scripts/deploy.sh [environment] [options]
#   environment: dev | prod (default: dev)
#   Options:
#     --https         Enable HTTPS with Let's Encrypt
#     --no-cache      Build without Docker cache
#     --pull          Pull latest images
#     --monitoring    Include monitoring stack (prometheus, grafana, loki)
# =============================================================================

set -euo pipefail

# ===== Configuration =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_DIR="$PROJECT_ROOT/deploy"

ENV="${1:-dev}"
HTTPS=false
NO_CACHE=""
PULL=false
MONITORING=false
COMPOSE_FILES=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

usage() {
    cat <<EOF
Urban Heat Mitigation Platform - Deployment Script

Usage: $0 [environment] [options]

Environments:
  dev    Deploy development stack with hot-reload (default)
  prod   Deploy production stack with optimization

Options:
  --https         Enable HTTPS with Let's Encrypt (prod only)
  --no-cache      Build Docker images without cache
  --pull          Pull latest base images
  --monitoring    Deploy monitoring stack (Prometheus, Grafana, Loki)

Examples:
  $0 dev                                          # Dev deployment
  $0 prod                                         # Production deployment
  $0 prod --https --monitoring                    # Full production with HTTPS + monitoring
  $0 prod --no-cache --pull                       # Fresh production build
EOF
    exit 1
}

# ===== Parse Arguments =====
shift 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --https)      HTTPS=true ;;
        --no-cache)   NO_CACHE="--no-cache" ;;
        --pull)       PULL=true ;;
        --monitoring) MONITORING=true ;;
        -h|--help)    usage ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
    shift
done

# ===== Validation =====
if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    log_error "Invalid environment: $ENV. Use 'dev' or 'prod'."
    exit 1
fi

if [ "$HTTPS" = true ] && [ "$ENV" != "prod" ]; then
    log_error "HTTPS is only supported in production environment"
    exit 1
fi

# ===== Pre-deployment Checks =====
pre_checks() {
    log_info "Running pre-deployment checks..."

    # Check Docker
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_ok "Docker $(docker --version | cut -d' ' -f3 | tr -d ',')"

    # Check Docker Compose
    if ! docker compose version &>/dev/null; then
        log_error "Docker Compose is not available"
        exit 1
    fi
    log_ok "Docker Compose $(docker compose version --short 2>/dev/null || docker-compose --version 2>/dev/null | cut -d' ' -f4 | tr -d ',')"

    # Check .env file for production
    if [ "$ENV" = "prod" ] && [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error "Production deployment requires .env file"
        log_info "Create from template: cp .env.example .env && edit .env"
        exit 1
    fi

    # Check disk space
    local available
    available=$(df / | tail -1 | awk '{print $4}')
    if [ "$available" -lt 5242880 ]; then  # 5GB in KB
        log_warn "Low disk space: $(($available / 1024)) MB available"
    fi

    log_ok "Pre-deployment checks passed"
}

# ===== Setup =====
setup() {
    log_info "Setting up deployment environment..."

    # Create required directories
    mkdir -p "$PROJECT_ROOT/data/satellite"
    mkdir -p "$PROJECT_ROOT/data/uploads"
    mkdir -p "$PROJECT_ROOT/data/models"
    mkdir -p "$PROJECT_ROOT/data/backups"
    mkdir -p "$PROJECT_ROOT/logs"

    # Build compose command
    if [ "$ENV" = "dev" ]; then
        COMPOSE_FILES+=("-f" "$COMPOSE_DIR/docker-compose.dev.yml")
    else
        COMPOSE_FILES+=("-f" "$COMPOSE_DIR/docker-compose.prod.yml")
        if [ "$HTTPS" = true ]; then
            COMPOSE_FILES+=("-f" "$COMPOSE_DIR/docker-compose.https.yml")
        fi
    fi

    # Add monitoring profile
    if [ "$MONITORING" = true ]; then
        log_info "Monitoring stack enabled"
    fi

    # Pull images
    if [ "$PULL" = true ]; then
        log_info "Pulling latest base images..."
        docker compose "${COMPOSE_FILES[@]}" pull
    fi

    log_ok "Environment setup complete"
}

# ===== Database Migration =====
run_migrations() {
    log_info "Running database migrations..."

    if [ "$ENV" = "prod" ]; then
        docker compose "${COMPOSE_FILES[@]}" run --rm backend \
            alembic upgrade head 2>&1 || {
            log_error "Migration failed"
            exit 1
        }
    else
        log_info "Migrations will run on backend startup (dev mode)"
    fi

    log_ok "Migrations complete"
}

# ===== Deploy =====
deploy() {
    log_info "Building and starting services..."

    BUILD_CMD="docker compose ${COMPOSE_FILES[*]} up -d --build"
    if [ -n "$NO_CACHE" ]; then
        BUILD_CMD="$BUILD_CMD $NO_CACHE"
    fi

    log_info "Running: $BUILD_CMD"
    eval "$BUILD_CMD" || {
        log_error "Deployment failed"
        exit 1
    }

    log_ok "Services started"
}

# ===== Health Check =====
health_check() {
    log_info "Running health checks..."

    local services=("postgres" "redis" "minio" "backend" "frontend" "nginx")
    local max_retries=12
    local retry_delay=10

    for service in "${services[@]}"; do
        local retries=0
        local container="urbanheat-$service"

        while [ $retries -lt $max_retries ]; do
            if docker ps --filter "name=$container" --filter "status=running" --format "{{.Names}}" | grep -q "$container"; then
                # Check health status if available
                local health
                health=$(docker inspect "$container" --format '{{.State.Health.Status}}' 2>/dev/null || echo "none")
                if [ "$health" = "healthy" ] || [ "$health" = "none" ]; then
                    log_ok "$service ($container) is healthy"
                    break
                fi
            fi
            retries=$((retries + 1))
            if [ $retries -ge $max_retries ]; then
                log_error "$service ($container) failed health check"
                docker logs "$container" --tail 20 2>/dev/null || true
                return 1
            fi
            sleep "$retry_delay"
        done
    done

    # Check if backend API is responding
    log_info "Verifying API endpoint..."
    local api_retries=0
    local api_url="http://localhost/api/v1/health"
    if [ "$ENV" = "dev" ]; then
        api_url="http://localhost:8000/api/v1/health"
    fi

    while [ $api_retries -lt $max_retries ]; do
        if curl -sf "$api_url" &>/dev/null; then
            log_ok "API endpoint is responding"
            break
        fi
        api_retries=$((api_retries + 1))
        sleep 5
    done

    if [ $api_retries -ge $max_retries ]; then
        log_error "API endpoint failed health check"
        return 1
    fi

    # Check monitoring if enabled
    if [ "$MONITORING" = true ]; then
        if curl -sf http://localhost:9090/-/ready &>/dev/null; then
            log_ok "Prometheus is responding"
        fi
        if curl -sf http://localhost:3000/api/health &>/dev/null; then
            log_ok "Grafana is responding"
        fi
    fi

    log_ok "All health checks passed"
}

# ===== Post-deployment Info =====
show_info() {
    echo ""
    echo "=========================================="
    echo -e "  ${GREEN}Urban Heat Mitigation Platform${NC}"
    echo -e "  Environment: ${BLUE}$ENV${NC}"
    echo "=========================================="
    echo ""
    echo -e "  Frontend:  ${BLUE}http://localhost${NC}"
    echo -e "  Backend:   ${BLUE}http://localhost/api${NC}"
    echo -e "  API Docs:  ${BLUE}http://localhost/api/docs${NC}"
    echo ""

    if [ "$MONITORING" = true ]; then
        echo -e "  Grafana:   ${BLUE}http://localhost/grafana${NC}"
        echo -e "  Prometheus:${BLUE}http://localhost:9090${NC}"
        echo ""
    fi

    if [ "$ENV" = "dev" ]; then
        echo -e "  Frontend:  ${BLUE}http://localhost:5173${NC}"
        echo -e "  Backend:   ${BLUE}http://localhost:8000${NC}"
        echo -e "  MinIO:     ${BLUE}http://localhost:9001${NC}"
        echo -e "  Flower:    ${BLUE}http://localhost:5555${NC}"
        echo -e "  pgAdmin:   ${BLUE}http://localhost:5050${NC}"
    fi
    echo ""

    # Show container status
    echo "Container Status:"
    docker compose "${COMPOSE_FILES[@]}" ps 2>/dev/null || true
    echo ""

    # Show resource usage
    echo "Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null | head -20 || true
    echo ""

    echo -e "  ${GREEN}Deployment completed successfully!${NC}"
    echo "=========================================="
}

# ===== Cleanup =====
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Deployment failed with exit code $exit_code"
        echo ""
        log_info "Troubleshooting:"
        echo "  - Check logs: docker compose logs --tail=50 <service>"
        echo "  - Check disk: df -h"
        echo "  - Check ports: netstat -tlnp"
    fi
    exit $exit_code
}
trap cleanup EXIT

# ===== Main =====
main() {
    echo ""
    echo "=========================================="
    echo "  Urban Heat Mitigation Platform"
    echo "  Deployment: $ENV"
    echo "=========================================="
    echo ""

    pre_checks
    setup
    deploy
    run_migrations
    health_check
    show_info
}

main "$@"
