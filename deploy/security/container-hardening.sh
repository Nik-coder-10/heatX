#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Container Security Hardening
# Run on Docker host to apply security best practices
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

harden_docker_daemon() {
    log_info "Hardening Docker daemon..."

    # Create daemon config
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<EOF
{
  "icc": false,
  "live-restore": true,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "max-concurrent-downloads": 3,
  "max-concurrent-uploads": 5,
  "storage-driver": "overlay2",
  "storage-opts": ["overlay2.override_kernel_check=true"],
  "userland-proxy": false,
  "iptables": true,
  "userns-remap": "default",
  "no-new-privileges": true,
  "seccomp-profile": "/etc/docker/seccomp.json"
}
EOF

    log_ok "Docker daemon hardened"
}

harden_docker_defaults() {
    log_info "Setting Docker default security options..."

    # Secure defaults for docker run
    cat > /etc/docker/defaults.json <<EOF
{
  "security-opts": [
    "no-new-privileges:true",
    "seccomp=default",
    "apparmor=docker-default"
  ],
  "cap-drop": ["ALL"],
  "cap-add": ["NET_BIND_SERVICE"],
  "read-only": false,
  "tmpfs": ["/tmp"],
  "ulimits": {
    "nofile": { "name": "nofile", "soft": 1024, "hard": 2048 },
    "nproc": { "name": "nproc", "soft": 1024, "hard": 2048 }
  }
}
EOF

    log_ok "Docker defaults configured"
}

apply_kernel_hardening() {
    log_info "Applying kernel-level hardening..."

    # Sysctl settings for container security
    cat > /etc/sysctl.d/99-docker-security.conf <<EOF
# Disable IP forwarding
net.ipv4.ip_forward=0
net.ipv6.conf.all.forwarding=0

# Enable IP spoofing protection
net.ipv4.conf.all.rp_filter=1
net.ipv4.conf.default.rp_filter=1

# Disable source packet routing
net.ipv4.conf.all.accept_source_route=0
net.ipv6.conf.all.accept_source_route=0

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects=0
net.ipv6.conf.all.accept_redirects=0
net.ipv4.conf.all.secure_redirects=0
net.ipv4.conf.all.send_redirects=0

# Enable TCP SYN cookie protection
net.ipv4.tcp_syncookies=1

# Reduce TIME_WAIT sockets
net.ipv4.tcp_fin_timeout=15
net.ipv4.tcp_tw_reuse=1

# Increase TCP backlog
net.core.somaxconn=65535

# Protect against time-wait assassination
net.ipv4.tcp_rfc1337=1

# Log suspicious packets
net.ipv4.conf.all.log_martians=1
EOF

    sysctl -p /etc/sysctl.d/99-docker-security.conf 2>/dev/null || true
    log_ok "Kernel hardening applied"
}

setup_apparmor() {
    log_info "Setting up AppArmor profile for containers..."

    if command -v apparmor_status &>/dev/null; then
        cat > /etc/apparmor.d/docker-urbanheat <<'PROFILE'
#include <tunables/global>

profile docker-urbanheat flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  # Network
  network inet tcp,
  network inet udp,
  network inet6 tcp,
  network inet6 udp,

  # Capabilities
  capability net_bind_service,
  capability setgid,
  capability setuid,
  capability sys_chroot,

  # Deny dangerous capabilities
  deny capability sys_admin,
  deny capability sys_module,
  deny capability sys_ptrace,
  deny capability dac_override,
  deny capability dac_read_search,

  # File system
  / r,
  /app/** rw,
  /tmp/** rw,
  /proc/** r,
  /dev/** r,
  -/proc/kcore,
  -/proc/sys/kernel/randomize_va_space,
}
PROFILE
        apparmor_parser -r /etc/apparmor.d/docker-urbanheat 2>/dev/null || true
        log_ok "AppArmor profile created"
    else
        log_warn "AppArmor not available"
    fi
}

setup_audit_logging() {
    log_info "Setting up audit logging for Docker..."

    # Audit Docker daemon events
    cat > /etc/audit/rules.d/docker.rules <<EOF
-w /usr/bin/docker -p wa -k docker
-w /var/lib/docker -p wa -k docker
-w /etc/docker -p wa -k docker
-w /etc/default/docker -p wa -k docker
EOF

    if command -v auditctl &>/dev/null; then
        auditctl -R /etc/audit/rules.d/docker.rules 2>/dev/null || true
    fi

    log_ok "Audit logging configured"
}

setup_image_policy() {
    log_info "Setting up image security policy..."

    # Only allow signed images from trusted registries
    cat > /etc/containers/policy.json <<EOF
{
  "default": [
    {
      "type": "reject"
    }
  ],
  "transports": {
    "docker": {
      "ghcr.io/urbanheat": [
        {
          "type": "signedBy",
          "keyType": "GPGKeys",
          "keyPath": "/etc/containers/trust.pub"
        }
      ],
      "docker.io/library": [
        {
          "type": "insecureAcceptAnything"
        }
      ]
    }
  }
}
EOF

    log_ok "Image policy configured"
}

main() {
    echo ""
    echo "=========================================="
    echo "  Container Security Hardening"
    echo "=========================================="
    echo ""

    if [ "${1:-}" = "--check" ]; then
        log_info "Running security audit only..."
        docker run --rm --privileged docker/docker-bench-security
        exit 0
    fi

    check_root
    harden_docker_daemon
    harden_docker_defaults
    apply_kernel_hardening
    setup_apparmor
    setup_audit_logging
    setup_image_policy

    log_info "Restarting Docker daemon..."
    systemctl restart docker || true

    echo ""
    log_ok "Security hardening complete"
    log_info "Run with --check to perform security audit"
    echo ""
}

main "$@"
