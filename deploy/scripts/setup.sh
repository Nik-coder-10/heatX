#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Server Setup Script
# Prepares a fresh Ubuntu/Debian server for deployment
# Usage: sudo ./deploy/scripts/setup.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

install_system_deps() {
    log_info "Updating system packages..."
    apt-get update -qq

    log_info "Installing system dependencies..."
    apt-get install -y -qq \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common \
        ufw \
        fail2ban \
        htop \
        iotop \
        net-tools \
        dnsutils \
        git \
        make \
        jq \
        unzip \
        tree \
        vim \
        rsync \
        postgresql-client \
        redis-tools
}

install_docker() {
    log_info "Installing Docker..."

    if command -v docker &>/dev/null; then
        log_info "Docker already installed: $(docker --version)"
        return
    fi

    # Remove old versions
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # Add Docker repository
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add current user to docker group
    usermod -aG docker "${SUDO_USER:-$USER}"

    # Enable and start Docker
    systemctl enable docker
    systemctl start docker

    log_ok "Docker $(docker --version) installed"
    log_ok "Docker Compose $(docker compose version --short) installed"
}

configure_firewall() {
    log_info "Configuring firewall..."

    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing

    # SSH
    ufw allow 22/tcp comment "SSH"

    # HTTP/HTTPS
    ufw allow 80/tcp comment "HTTP"
    ufw allow 443/tcp comment "HTTPS"

    # Monitoring (internal only)
    ufw allow from 10.0.0.0/8 to any port 9090 proto tcp comment "Prometheus internal"
    ufw allow from 10.0.0.0/8 to any port 3000 proto tcp comment "Grafana internal"

    ufw --force enable

    log_ok "Firewall configured"
}

setup_fail2ban() {
    log_info "Configuring fail2ban..."

    cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5
EOF

    systemctl enable fail2ban
    systemctl restart fail2ban

    log_ok "fail2ban configured"
}

setup_logging() {
    log_info "Setting up log rotation..."

    cat > /etc/logrotate.d/urbanheat <<EOF
/var/log/urbanheat/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 0644 appuser appuser
}
EOF

    mkdir -p /var/log/urbanheat
    log_ok "Log rotation configured"
}

setup_swap() {
    log_info "Configuring swap..."

    if [ "$(swapon --show | wc -l)" -eq 0 ]; then
        fallocate -l 4G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab

        # Reduce swappiness
        echo 'vm.swappiness=10' >> /etc/sysctl.d/99-swap.conf
        sysctl -p /etc/sysctl.d/99-swap.conf

        log_ok "Swap configured (4GB)"
    else
        log_info "Swap already configured"
    fi
}

main() {
    echo ""
    echo "=========================================="
    echo "  Urban Heat Platform - Server Setup"
    echo "=========================================="
    echo ""

    check_root

    install_system_deps
    install_docker
    configure_firewall
    setup_fail2ban
    setup_logging
    setup_swap

    echo ""
    log_ok "Server setup complete!"
    echo ""
    log_info "Next steps:"
    echo "  1. Log out and back in for Docker group changes"
    echo "  2. Clone the repository: git clone <repo> /opt/urbanheat"
    echo "  3. Copy .env.production to .env and configure"
    echo "  4. Run: ./deploy/scripts/deploy.sh prod --monitoring"
    echo "  5. Run: sudo ./deploy/scripts/init-letsencrypt.sh <domain> <email>"
    echo ""
}

main "$@"
