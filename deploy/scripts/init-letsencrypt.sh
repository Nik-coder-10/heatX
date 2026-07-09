#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Let's Encrypt Certificate Initialization
# Usage: sudo ./deploy/scripts/init-letsencrypt.sh <domain> <email>
# Example: sudo ./deploy/scripts/init-letsencrypt.sh urbanheat.io admin@urbanheat.io
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

usage() {
    echo "Usage: sudo $0 <domain> <email>"
    echo ""
    echo "Arguments:"
    echo "  domain   Domain name for the certificate"
    echo "  email    Email address for Let's Encrypt notifications"
    echo ""
    echo "Example:"
    echo "  sudo $0 urbanheat.io admin@urbanheat.io"
    exit 1
}

check_prerequisites() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root (sudo)"
        exit 1
    fi

    if [ $# -ne 2 ]; then
        usage
    fi

    if ! command -v docker &>/dev/null; then
        log_error "Docker is required"
        exit 1
    fi
}

init_certificate() {
    local domain="$1"
    local email="$2"

    log_info "Initializing Let's Encrypt certificate for $domain..."

    # Create required directories
    mkdir -p "$PROJECT_ROOT/data/certbot/conf"
    mkdir -p "$PROJECT_ROOT/data/certbot/www"

    # Pull certbot image
    docker pull certbot/certbot:v2.9.0

    # Stop any running nginx that might conflict
    docker stop urbanheat-nginx 2>/dev/null || true

    # Run temporary nginx for ACME challenge
    docker run --rm -d \
        --name urbanheat-certbot-nginx \
        -p 80:80 \
        -v "$PROJECT_ROOT/data/certbot/www:/var/www/certbot" \
        nginx:1.25-alpine \
        sh -c "echo 'server { listen 80; location /.well-known/acme-challenge/ { root /var/www/certbot; } }' > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"

    sleep 2

    # Run certbot
    docker run --rm \
        -v "$PROJECT_ROOT/data/certbot/conf:/etc/letsencrypt" \
        -v "$PROJECT_ROOT/data/certbot/www:/var/www/certbot" \
        certbot/certbot:v2.9.0 \
        certonly --webroot \
        --webroot-path=/var/www/certbot \
        --email "$email" \
        --domain "$domain" \
        --agree-tos \
        --non-interactive \
        --force-renewal

    # Clean up temporary nginx
    docker stop urbanheat-certbot-nginx 2>/dev/null || true

    log_ok "Certificate obtained successfully for $domain"
}

verify_certificate() {
    local domain="$1"

    log_info "Verifying certificate..."

    local cert_path="$PROJECT_ROOT/data/certbot/conf/live/$domain/fullchain.pem"

    if [ -f "$cert_path" ]; then
        local expiry
        expiry=$(openssl x509 -enddate -noout -in "$cert_path" | cut -d= -f2)
        log_ok "Certificate exists, expires: $expiry"
    else
        log_error "Certificate not found at $cert_path"
        exit 1
    fi
}

setup_auto_renewal() {
    log_info "Setting up auto-renewal cron job..."

    local cron_job="0 3 * * * root docker run --rm -v $PROJECT_ROOT/data/certbot/conf:/etc/letsencrypt -v $PROJECT_ROOT/data/certbot/www:/var/www/certbot certbot/certbot:v2.9.0 renew --webroot -w /var/www/certbot --quiet && docker exec urbanheat-nginx nginx -s reload"

    if ! grep -q "certbot" /etc/crontab 2>/dev/null; then
        echo "$cron_job" >> /etc/crontab
        log_ok "Auto-renewal cron job installed"
    else
        log_info "Auto-renewal cron job already exists"
    fi
}

show_instructions() {
    local domain="$1"

    echo ""
    echo "=========================================="
    echo -e "  ${GREEN}Let's Encrypt Setup Complete${NC}"
    echo "=========================================="
    echo ""
    echo "  Certificate: /etc/letsencrypt/live/$domain/"
    echo "  Auto-renewal: Daily at 3 AM"
    echo ""
    echo "  Next steps:"
    echo "  1. Copy certificates to the Nginx certbot volume:"
    echo "     cp -r $PROJECT_ROOT/data/certbot/conf/* $PROJECT_ROOT/deploy/certbot/conf/"
    echo ""
    echo "  2. Deploy with HTTPS:"
    echo "     ./deploy/scripts/deploy.sh prod --https"
    echo ""
    echo "  3. Verify HTTPS:"
    echo "     curl -I https://$domain"
    echo ""
    echo "=========================================="
}

main() {
    local domain="$1"
    local email="$2"

    echo ""
    echo "=========================================="
    echo "  Let's Encrypt Certificate Setup"
    echo "=========================================="
    echo ""

    check_prerequisites "$@"
    init_certificate "$domain" "$email"
    verify_certificate "$domain"
    setup_auto_renewal
    show_instructions "$domain"
}

main "$@"
