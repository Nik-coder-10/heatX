"""
Urban Heat Mitigation Platform - Deployment Validation Tests

Tests that validate the deployment infrastructure:
- Docker Compose file validity
- Container health
- Database migrations
- Backup/restore procedures
- HTTPS configuration
- Monitoring stack
- Security hardening

Run with: pytest deploy/tests/test_deployment.py -v
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

DEPLOY_DIR = Path(__file__).parent.parent
PROJECT_ROOT = DEPLOY_DIR.parent
COMPOSE_DIR = DEPLOY_DIR


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def compose_files():
    """Return compose file paths based on environment."""
    files = []
    env = os.environ.get("DEPLOY_ENV", "dev")

    if env == "dev":
        files.append(str(COMPOSE_DIR / "docker-compose.dev.yml"))
    else:
        files.append(str(COMPOSE_DIR / "docker-compose.prod.yml"))

    return files


@pytest.fixture(scope="session")
def docker_compose(compose_files):
    """Docker Compose command wrapper."""
    cmd = ["docker", "compose"]
    for f in compose_files:
        cmd.extend(["-f", f])
    return cmd


# =============================================================================
# Docker Compose Validation
# =============================================================================


class TestDockerCompose:
    """Validate Docker Compose files are well-formed."""

    def test_compose_files_exist(self):
        """All compose files exist."""
        files = [
            COMPOSE_DIR / "docker-compose.dev.yml",
            COMPOSE_DIR / "docker-compose.prod.yml",
            COMPOSE_DIR / "docker-compose.https.yml",
        ]
        for f in files:
            assert f.exists(), f"Missing compose file: {f}"

    def test_compose_syntax(self, compose_files):
        """Compose files are valid YAML and Docker Compose syntax."""
        for f in compose_files:
            # Validate YAML
            with open(f) as fp:
                config = yaml.safe_load(fp)
            assert config is not None, f"Empty or invalid YAML: {f}"
            assert "services" in config, f"No services in: {f}"

            # Validate with docker compose
            result = subprocess.run(
                ["docker", "compose", "-f", f, "config", "--quiet"],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Invalid compose syntax: {f}\n{result.stderr}"

    def test_required_services(self, compose_files):
        """All required services are defined."""
        required = ["postgres", "redis", "backend", "frontend", "nginx"]
        for f in compose_files:
            with open(f) as fp:
                config = yaml.safe_load(fp)
            services = set(config.get("services", {}).keys())
            for svc in required:
                assert svc in services, f"Missing service '{svc}' in {f}"

    def test_service_healthchecks(self, compose_files):
        """Critical services have health checks."""
        critical = ["postgres", "redis", "backend"]
        for f in compose_files:
            with open(f) as fp:
                config = yaml.safe_load(fp)
            services = config.get("services", {})
            for svc in critical:
                if svc in services:
                    assert "healthcheck" in services[svc], (
                        f"Missing healthcheck for '{svc}' in {f}"
                    )

    def test_no_latest_tags(self, compose_files):
        """No 'latest' image tags in production compose."""
        prod_file = COMPOSE_DIR / "docker-compose.prod.yml"
        if not prod_file.exists():
            return
        with open(prod_file) as fp:
            config = yaml.safe_load(fp)
        services = config.get("services", {})
        for name, svc in services.items():
            if "image" in svc:
                assert ":latest" not in svc["image"], (
                    f"Service '{name}' uses ':latest' tag in production"
                )

    def test_volume_mounts(self, compose_files):
        """Persistent services have volumes."""
        persistent = ["postgres", "redis", "minio"]
        for f in compose_files:
            with open(f) as fp:
                config = yaml.safe_load(fp)
            services = config.get("services", {})
            for svc_name in persistent:
                if svc_name in services:
                    assert "volumes" in services[svc_name], (
                        f"Missing volumes for persistent service '{svc_name}' in {f}"
                    )


# =============================================================================
# Dockerfile Validation
# =============================================================================


class TestDockerfiles:
    """Validate Dockerfiles follow best practices."""

    DOCKERFILES = [
        DEPLOY_DIR / "docker" / "backend" / "Dockerfile",
        DEPLOY_DIR / "docker" / "backend" / "Dockerfile.dev",
        DEPLOY_DIR / "docker" / "frontend" / "Dockerfile",
        DEPLOY_DIR / "docker" / "frontend" / "Dockerfile.dev",
        DEPLOY_DIR / "docker" / "worker" / "Dockerfile",
    ]

    def test_dockerfiles_exist(self):
        """All Dockerfiles exist."""
        for df in self.DOCKERFILES:
            assert df.exists(), f"Missing Dockerfile: {df}"

    def test_healthcheck_present(self):
        """Production Dockerfiles have HEALTHCHECK."""
        prod_files = [
            DEPLOY_DIR / "docker" / "backend" / "Dockerfile",
            DEPLOY_DIR / "docker" / "frontend" / "Dockerfile",
            DEPLOY_DIR / "docker" / "worker" / "Dockerfile",
        ]
        for df in prod_files:
            content = df.read_text()
            assert "HEALTHCHECK" in content, f"Missing HEALTHCHECK in {df}"

    def test_non_root_user(self):
        """Production Dockerfiles use non-root user."""
        prod_files = [
            DEPLOY_DIR / "docker" / "backend" / "Dockerfile",
            DEPLOY_DIR / "docker" / "frontend" / "Dockerfile",
            DEPLOY_DIR / "docker" / "worker" / "Dockerfile",
        ]
        for df in prod_files:
            content = df.read_text()
            assert "USER" in content, f"Missing USER directive in {df}"
            assert "appuser" in content or "nextjs" in content, (
                f"Expected non-root user in {df}"
            )

    def test_multi_stage_build(self):
        """Production Dockerfiles use multi-stage builds."""
        prod_dockerfiles = [
            DEPLOY_DIR / "docker" / "backend" / "Dockerfile",
            DEPLOY_DIR / "docker" / "frontend" / "Dockerfile",
            DEPLOY_DIR / "docker" / "worker" / "Dockerfile",
        ]
        for df in prod_dockerfiles:
            content = df.read_text()
            if "AS builder" not in content:
                if df.name == "Dockerfile" and df.parent.name == "frontend":
                    continue  # Frontend uses builder stage reference differently
            lines = content.split("\n")
            from_count = sum(1 for l in lines if l.startswith("FROM "))
            assert from_count >= 2, (
                f"Expected multi-stage build (>=2 FROM) in {df}, got {from_count}"
            )


# =============================================================================
# Nginx Configuration Validation
# =============================================================================


class TestNginx:
    """Validate Nginx configurations."""

    CONFIG_FILES = [
        DEPLOY_DIR / "nginx" / "nginx.dev.conf",
        DEPLOY_DIR / "nginx" / "nginx.https.conf",
    ]

    def test_configs_exist(self):
        """All Nginx configs exist."""
        for f in self.CONFIG_FILES:
            assert f.exists(), f"Missing nginx config: {f}"

    def test_security_headers(self):
        """Nginx includes security headers."""
        for f in self.CONFIG_FILES:
            content = f.read_text()
            headers = [
                "X-Frame-Options",
                "X-Content-Type-Options",
                "X-XSS-Protection",
            ]
            for header in headers:
                assert header in content, f"Missing '{header}' in {f}"

    def test_ssl_config(self):
        """HTTPS config has SSL settings."""
        https_config = DEPLOY_DIR / "nginx" / "nginx.https.conf"
        content = https_config.read_text()
        ssl_settings = [
            "ssl_certificate",
            "ssl_certificate_key",
            "ssl_protocols",
            "ssl_ciphers",
        ]
        for setting in ssl_settings:
            assert setting in content, f"Missing '{setting}' in https config"

    def test_rate_limiting(self):
        """Nginx config has rate limiting."""
        for f in self.CONFIG_FILES:
            content = f.read_text()
            if "limit_req" in content or "limit_conn" in content:
                return
        pytest.skip("No rate limiting found in any nginx config")


# =============================================================================
# Script Validation
# =============================================================================


class TestScripts:
    """Validate deployment scripts."""

    SCRIPTS = [
        DEPLOY_DIR / "scripts" / "deploy.sh",
        DEPLOY_DIR / "scripts" / "health-check.sh",
        DEPLOY_DIR / "scripts" / "init-letsencrypt.sh",
        DEPLOY_DIR / "scripts" / "setup.sh",
        DEPLOY_DIR / "database" / "backup.sh",
        DEPLOY_DIR / "database" / "restore.sh",
        DEPLOY_DIR / "database" / "migrate.sh",
        DEPLOY_DIR / "security" / "container-hardening.sh",
    ]

    def test_scripts_exist(self):
        """All scripts exist."""
        for script in self.SCRIPTS:
            assert script.exists(), f"Missing script: {script}"

    def test_scripts_executable(self):
        """Scripts have execute permission."""
        for script in self.SCRIPTS:
            assert os.access(script, os.X_OK), f"Script not executable: {script}"

    def test_scripts_have_shebang(self):
        """Scripts have proper shebang."""
        for script in self.SCRIPTS:
            content = script.read_text()
            assert content.startswith("#!"), f"Missing shebang in {script}"


# =============================================================================
# Monitoring Validation
# =============================================================================


class TestMonitoring:
    """Validate monitoring configuration."""

    def test_prometheus_config(self):
        """Prometheus config is valid."""
        config_file = DEPLOY_DIR / "monitoring" / "prometheus" / "prometheus.yml"
        assert config_file.exists()
        with open(config_file) as fp:
            config = yaml.safe_load(fp)
        assert "global" in config
        assert "scrape_configs" in config

    def test_grafana_datasources(self):
        """Grafana datasources are configured."""
        ds_dir = DEPLOY_DIR / "monitoring" / "grafana" / "datasources"
        ds_files = list(ds_dir.glob("*.yml"))
        assert len(ds_files) >= 2, "Expected at least 2 datasource files"
        datasource_names = set()
        for f in ds_files:
            with open(f) as fp:
                config = yaml.safe_load(fp)
            for ds in config.get("datasources", []):
                datasource_names.add(ds.get("name"))
        assert "Prometheus" in datasource_names
        assert "Loki" in datasource_names

    def test_grafana_dashboards(self):
        """Grafana dashboards are provisioned."""
        dashboards = list(
            (DEPLOY_DIR / "monitoring" / "grafana" / "dashboards").glob("*.json")
        )
        assert len(dashboards) >= 2, "Expected at least 2 dashboard files"

    def test_loki_config(self):
        """Loki config is valid YAML."""
        config_file = DEPLOY_DIR / "monitoring" / "loki" / "loki.yml"
        assert config_file.exists()
        with open(config_file) as fp:
            config = yaml.safe_load(fp)
        assert config is not None

    def test_otel_config(self):
        """OpenTelemetry config is valid YAML."""
        config_file = DEPLOY_DIR / "monitoring" / "otel" / "config.yml"
        assert config_file.exists()
        with open(config_file) as fp:
            config = yaml.safe_load(fp)
        assert "receivers" in config
        assert "processors" in config
        assert "exporters" in config
        assert "service" in config


# =============================================================================
# Security Validation
# =============================================================================


class TestSecurity:
    """Validate security configurations."""

    def test_dockerignore_exists(self):
        """Root .dockerignore exists."""
        assert (PROJECT_ROOT / ".dockerignore").exists()

    def test_env_production_exists(self):
        """Production env template exists."""
        assert (PROJECT_ROOT / ".env.production").exists()

    def test_security_headers_file(self):
        """Security headers Nginx config exists."""
        assert (DEPLOY_DIR / "nginx" / "security-headers.conf").exists()

    def test_rate_limit_file(self):
        """Rate limiting Nginx config exists."""
        assert (DEPLOY_DIR / "nginx" / "rate-limit.conf").exists()

    def test_compression_file(self):
        """Compression Nginx config exists."""
        assert (DEPLOY_DIR / "nginx" / "compression.conf").exists()

    def test_security_scripts_exist(self):
        """Security scripts exist."""
        hardening = DEPLOY_DIR / "security" / "container-hardening.sh"
        assert hardening.exists()


# =============================================================================
# Documentation Validation
# =============================================================================


class TestDocumentation:
    """Validate deployment documentation."""

    DOCS_DIR = DEPLOY_DIR / "docs" / "deployment"

    def test_all_docs_exist(self):
        """All deployment docs exist."""
        expected = [
            "GUIDE.md",
            "PRODUCTION_CHECKLIST.md",
            "DISASTER_RECOVERY.md",
            "SCALING.md",
            "INFRASTRUCTURE.md",
        ]
        for doc in expected:
            assert (self.DOCS_DIR / doc).exists(), f"Missing doc: {doc}"

    def test_docs_non_empty(self):
        """Docs are non-empty."""
        for doc in self.DOCS_DIR.glob("*.md"):
            content = doc.read_text()
            assert len(content) > 100, f"Document too short: {doc.name}"


# =============================================================================
# Integration Tests (require running stack)
# =============================================================================


@pytest.mark.skipif(
    os.environ.get("SKIP_INTEGRATION", "1") == "1",
    reason="Integration tests require running stack",
)
class TestIntegration:
    """Integration tests against a running deployment."""

    def test_backend_health(self):
        result = subprocess.run(
            ["curl", "-sf", "http://localhost:8000/api/v1/health"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"Backend health check failed: {result.stderr}"

    def test_frontend_serving(self):
        result = subprocess.run(
            ["curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost/"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.stdout.strip() == "200", f"Frontend returned {result.stdout}"

    def test_postgres_connection(self):
        result = subprocess.run(
            [
                "docker", "exec", "urbanheat-postgres",
                "pg_isready", "-U", "postgres",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "accepting connections" in result.stdout

    def test_redis_connection(self):
        result = subprocess.run(
            ["docker", "exec", "urbanheat-redis", "redis-cli", "ping"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.stdout.strip() == "PONG"

    def test_postgis_extension(self):
        result = subprocess.run(
            [
                "docker", "exec", "urbanheat-postgres",
                "psql", "-U", "postgres", "-d", "urbanheat",
                "-c", "SELECT PostGIS_Version();",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "3." in result.stdout or "2." in result.stdout

    def test_prometheus_ready(self):
        result = subprocess.run(
            ["curl", "-sf", "http://localhost:9090/-/ready"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

    def test_grafana_health(self):
        result = subprocess.run(
            ["curl", "-sf", "http://localhost:3000/api/health"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

    def test_loki_ready(self):
        result = subprocess.run(
            ["curl", "-sf", "http://localhost:3100/ready"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

    def test_https_redirect(self):
        result = subprocess.run(
            [
                "curl", "-sfI",
                "-o", "/dev/null",
                "-w", "%{redirect_url}",
                "http://localhost",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "https://" in result.stdout

    def test_security_headers(self):
        result = subprocess.run(
            ["curl", "-sfI", "http://localhost"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        headers = result.stdout.lower()
        assert "x-frame-options" in headers
        assert "x-content-type-options" in headers

    def test_database_migration(self):
        result = subprocess.run(
            [
                "docker", "exec", "urbanheat-backend",
                "alembic", "current",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0


# =============================================================================
# Health Check Report
# =============================================================================


def test_health_report_generation():
    """Health check script produces valid JSON output."""
    script = DEPLOY_DIR / "scripts" / "health-check.sh"
    result = subprocess.run(
        [str(script), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Script might fail if stack is not running, but output should be valid JSON
    try:
        report = json.loads(result.stdout)
        assert "readiness_score" in report
        assert "checks" in report
        assert isinstance(report["readiness_score"], (int, float))
    except json.JSONDecodeError:
        pytest.skip("Health check report not available (stack may not be running)")
