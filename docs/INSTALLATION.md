# Urban Heat Mitigation Platform — Installation Guide

**Version 1.0.0** | July 2026

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Windows Installation](#2-windows-installation)
3. [Linux Installation](#3-linux-installation-ubuntudebian)
4. [macOS Installation](#4-macos-installation)
5. [Docker Installation](#5-docker-installation)
6. [Cloud Deployment](#6-cloud-deployment)
7. [Development Setup](#7-development-setup)
8. [Production Setup](#8-production-setup)
9. [Verifying the Installation](#9-verifying-the-installation)
10. [Troubleshooting Installation Issues](#10-troubleshooting-installation-issues)

---

## 1. Prerequisites

### 1.1 Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| **CPU** | 4 cores (x86_64) | 8+ cores |
| **RAM** | 16 GB | 32 GB |
| **Storage** | 50 GB free | 200 GB+ (NVMe SSD) |
| **GPU** | Not required | NVIDIA GPU with 8 GB VRAM (for model training) |
| **Network** | Broadband (50 Mbps) | Broadband (100 Mbps+) |

**Storage breakdown:**
- Application code + dependencies: ~5 GB
- Satellite imagery cache: ~20 GB (adjustable)
- ML model storage: ~2 GB per model
- Database: ~10 GB (1000+ scenes)
- Logs: ~5 GB (rolling)

### 1.2 Software Requirements

| Software | Minimum Version | Purpose |
|---|---|---|
| **Python** | 3.11 | Backend runtime |
| **Node.js** | 20 (LTS) | Frontend runtime |
| **Docker** | 24+ | Containerization |
| **Docker Compose** | 2.20+ | Multi-container orchestration |
| **PostgreSQL** | 15 | Primary database |
| **PostGIS** | 3.4 | Spatial extensions |
| **Redis** | 7 | Caching & task queue |
| **MinIO** | (latest) | Object storage (S3-compatible) |
| **GDAL** | 3.7 | Geospatial data processing |
| **Nginx** | 1.24 | Reverse proxy (production) |

---

## 2. Windows Installation

### 2.1 Install Python 3.11

1. Download Python 3.11 from [python.org/downloads](https://python.org/downloads).
2. Run the installer. **Check "Add Python to PATH"** during installation.
3. Verify:
   ```powershell
   python --version
   # Expected: Python 3.11.x
   ```

### 2.2 Install Node.js 20 (LTS)

1. Download Node.js 20 LTS from [nodejs.org](https://nodejs.org).
2. Run the MSI installer with default options.
3. Verify:
   ```powershell
   node --version
   # Expected: v20.x.x
   npm --version
   # Expected: 10.x.x
   ```

### 2.3 Install Docker Desktop

1. Download Docker Desktop for Windows from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop).
2. Run the installer. Ensure **WSL 2 Integration** is enabled.
3. After installation, launch Docker Desktop and wait for the engine to start.
4. Verify:
   ```powershell
   docker --version
   docker compose version
   ```

### 2.4 Install PostgreSQL + PostGIS

**Option A: Using Docker (Recommended)**

Run PostgreSQL + PostGIS in a Docker container:

```powershell
docker run -d ^
  --name uhmp-postgis ^
  -e POSTGRES_USER=uhmp ^
  -e POSTGRES_PASSWORD=uhmp_secret ^
  -e POSTGRES_DB=uhmp ^
  -p 5432:5432 ^
  -v uhmp_pgdata:/var/lib/postgresql/data ^
  postgis/postgis:15-3.4
```

**Option B: Native Installation**

1. Download PostgreSQL 15+ from [enterprisedb.com/downloads/postgres-postgresql-downloads](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads).
2. Run the installer. Include the Stack Builder option.
3. Launch **Stack Builder** and install **PostGIS 3.4** Bundle.
4. Create the database:
   ```powershell
   psql -U postgres -c "CREATE DATABASE uhmp;"
   psql -U postgres -c "CREATE USER uhmp WITH PASSWORD 'uhmp_secret';"
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE uhmp TO uhmp;"
   psql -U postgres -d uhmp -c "CREATE EXTENSION postgis;"
   psql -U postgres -d uhmp -c "CREATE EXTENSION postgis_raster;"
   ```

### 2.5 Install GDAL

Using conda (recommended on Windows):

```powershell
conda install -c conda-forge gdal=3.7
```

Or download from [gdal.org/download.html](https://gdal.org/download.html).

Verify:
```powershell
gdalinfo --version
```

### 2.6 Clone and Configure the Application

```powershell
git clone https://github.com/yourorg/uhmp.git
cd uhmp

# Create environment file
copy .env.example .env
# Edit .env with your settings (see CONFIGURATION.md)

# Set up Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2.7 Run the Application

Start the application in separate terminal windows:

**Terminal 1 — Backend:**
```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Celery Worker:**
```powershell
.\venv\Scripts\Activate.ps1
celery -A app.tasks worker --loglevel=info --concurrency=4
```

**Terminal 3 — Frontend:**
```powershell
cd frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Flower (Celery monitor): http://localhost:5555

---

## 3. Linux Installation (Ubuntu/Debian)

### 3.1 System Packages

```bash
sudo apt update && sudo apt upgrade -y

# Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# PostgreSQL + PostGIS
sudo apt install -y postgresql-15 postgresql-15-postgis-3 postgresql-15-postgis-3-scripts

# GDAL
sudo apt install -y gdal-bin libgdal-dev

# Redis
sudo apt install -y redis-server

# Nginx
sudo apt install -y nginx

# Build tools
sudo apt install -y build-essential curl git
```

### 3.2 Database Setup

```bash
sudo -u postgres psql -c "CREATE USER uhmp WITH PASSWORD 'uhmp_secret';"
sudo -u postgres psql -c "CREATE DATABASE uhmp OWNER uhmp;"
sudo -u postgres psql -d uhmp -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -d uhmp -c "CREATE EXTENSION postgis_raster;"
sudo -u postgres psql -c "ALTER USER uhmp CREATEDB;"
```

### 3.3 Docker CE Installation

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

### 3.4 Application Setup

```bash
git clone https://github.com/yourorg/uhmp.git
cd uhmp

# Python virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env

# Frontend
cd frontend
npm install
npm run build
cd ..
```

### 3.5 Running with Systemd (Production)

Create systemd service files:

**/etc/systemd/system/uhmp-api.service:**
```ini
[Unit]
Description=UHMP API Server
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/uhmp
Environment=PATH=/opt/uhmp/venv/bin
ExecStart=/opt/uhmp/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**/etc/systemd/system/uhmp-celery.service:**
```ini
[Unit]
Description=UHMP Celery Worker
After=network.target redis-server.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/uhmp
Environment=PATH=/opt/uhmp/venv/bin
ExecStart=/opt/uhmp/venv/bin/celery -A app.tasks worker --loglevel=info --concurrency=4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable uhmp-api uhmp-celery
sudo systemctl start uhmp-api uhmp-celery
```

---

## 4. macOS Installation

### 4.1 Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 4.2 Install Dependencies

```bash
# Python 3.11
brew install python@3.11

# Node.js
brew install node@20

# PostgreSQL + PostGIS
brew install postgresql@15
brew install postgis

# Redis
brew install redis

# GDAL
brew install gdal

# Docker Desktop
# Download from https://www.docker.com/products/docker-desktop
```

### 4.3 Database Setup

```bash
brew services start postgresql@15
brew services start redis

# Create DB
psql postgres -c "CREATE USER uhmp WITH PASSWORD 'uhmp_secret';"
createdb uhmp
psql -d uhmp -c "CREATE EXTENSION postgis;"
psql -d uhmp -c "CREATE EXTENSION postgis_raster;"
```

### 4.4 Application Setup

```bash
git clone https://github.com/yourorg/uhmp.git
cd uhmp

# Virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Environment
cp .env.example .env

# Frontend
cd frontend
npm install
cd ..
```

### 4.5 Running

```bash
# Terminal 1: Backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Celery
source venv/bin/activate
celery -A app.tasks worker --loglevel=info --concurrency=4

# Terminal 3: Frontend
cd frontend && npm run dev
```

---

## 5. Docker Installation

### 5.1 Development Deployment

**docker-compose.dev.yml:**
```yaml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app/app
      - ./data:/app/data
    environment:
      - DATABASE_URL=postgresql+asyncpg://uhmp:uhmp_secret@db:5432/uhmp
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - ENVIRONMENT=development
    depends_on:
      - db
      - redis
      - minio
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend/src:/app/src
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - api
    restart: unless-stopped

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile.dev
    command: celery -A app.tasks worker --loglevel=info --concurrency=4
    volumes:
      - ./app:/app/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://uhmp:uhmp_secret@db:5432/uhmp
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    depends_on:
      - db
      - redis
      - minio
    restart: unless-stopped

  db:
    image: postgis/postgis:15-3.4
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=uhmp
      - POSTGRES_PASSWORD=uhmp_secret
      - POSTGRES_DB=uhmp
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    restart: unless-stopped

  flower:
    image: mher/flower
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  pgdata:
  redis_data:
  minio_data:
```

**Run:**
```bash
docker compose -f docker-compose.dev.yml up -d
```

### 5.2 Production Deployment

**docker-compose.prod.yml:**
```yaml
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://uhmp:${DB_PASSWORD}@db:5432/uhmp
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
      - SENTRY_DSN=${SENTRY_DSN}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "2"
          memory: "4G"
    depends_on:
      - db
      - redis
      - minio
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=https://api.uhmp.example.com
    depends_on:
      - api
    restart: unless-stopped

  nginx:
    image: nginx:1.24-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - api
      - frontend
    restart: unless-stopped

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.tasks worker --loglevel=warning --concurrency=4 --max-tasks-per-child=100
    environment:
      - DATABASE_URL=postgresql+asyncpg://uhmp:${DB_PASSWORD}@db:5432/uhmp
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    deploy:
      replicas: 2
    depends_on:
      - db
      - redis
      - minio
    restart: unless-stopped

  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A app.tasks beat --loglevel=warning
    environment:
      - DATABASE_URL=postgresql+asyncpg://uhmp:${DB_PASSWORD}@db:5432/uhmp
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgis/postgis:15-3.4
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=uhmp
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=uhmp
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: "8G"
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: "2G"
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  pgdata:
  redis_data:
  minio_data:
  prometheus_data:
  grafana_data:
```

**Deploy:**
```bash
# Create environment file
cp .env.prod.example .env
# Edit .env with secure passwords

# Deploy
docker compose -f docker-compose.prod.yml up -d

# Scale workers
docker compose -f docker-compose.prod.yml up -d --scale celery_worker=4
```

---

## 6. Cloud Deployment

### 6.1 AWS EC2

**Prerequisites:** AWS CLI configured, Terraform or CloudFormation experience.

**Manual setup:**
```bash
# SSH into instance
ssh -i your-key.pem ubuntu@<ec2-public-ip>

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker ubuntu

# Clone and deploy
git clone https://github.com/yourorg/uhmp.git
cd uhmp
cp .env.prod.example .env
# Edit .env with RDS endpoint, ElastiCache, S3 bucket, etc.
docker compose -f docker-compose.prod.yml up -d
```

**Recommended AWS services:**

| Service | Purpose |
|---|---|
| **EC2 (m6i.xlarge)** | Application server |
| **RDS PostgreSQL** | Managed database |
| **ElastiCache Redis** | Managed caching |
| **S3** | Object storage (replaces MinIO) |
| **ALB** | Load balancer (SSL termination) |
| **Route 53** | DNS management |
| **CloudWatch** | Monitoring & logging |

### 6.2 Azure VM

```bash
# SSH into VM
ssh azureuser@<vm-ip>

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker azureuser

# Clone and deploy
git clone https://github.com/yourorg/uhmp.git
cd uhmp
docker compose -f docker-compose.prod.yml up -d
```

**Recommended Azure services:**

| Service | Purpose |
|---|---|
| **VM (Standard_D4s_v3)** | Application server |
| **Azure Database for PostgreSQL** | Managed database with PostGIS |
| **Azure Cache for Redis** | Managed caching |
| **Blob Storage** | Object storage |
| **Application Gateway** | Load balancer / SSL |
| **Azure Monitor** | Monitoring |

**PostGIS note:** Azure Database for PostgreSQL supports PostGIS. Enable with:
```sql
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_raster;
```

### 6.3 GCP Compute Engine

```bash
# SSH into instance
gcloud compute ssh uhmp-instance

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Clone and deploy
git clone https://github.com/yourorg/uhmp.git
cd uhmp
docker compose -f docker-compose.prod.yml up -d
```

**Recommended GCP services:**

| Service | Purpose |
|---|---|
| **Compute Engine (n2-standard-4)** | Application server |
| **Cloud SQL for PostgreSQL** | Managed database (enable PostGIS extension) |
| **Memorystore Redis** | Managed caching |
| **Cloud Storage** | Object storage |
| **Cloud Load Balancing** | Load balancer / SSL |
| **Cloud Monitoring** | Monitoring |

### 6.4 Railway

1. Push your repository to GitHub.
2. Go to [railway.app](https://railway.app) and create a new project from your repository.
3. Add services:
   - **Web Service:** `api` — start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Web Service:** `frontend` — root directory: `frontend`, build: `npm install && npm run build`, start: `npx serve -s dist -l $PORT`
   - **Worker:** `celery_worker` — start command: `celery -A app.tasks worker --loglevel=info`
   - **PostgreSQL plugin** (enables PostGIS automatically)
   - **Redis plugin**
4. Configure environment variables via the Railway dashboard.
5. Deploy — Railway auto-builds and deploys on push.

### 6.5 Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Launch
cd uhmp
fly launch

# Set secrets
fly secrets set DATABASE_URL=postgresql+asyncpg://... SECRET_KEY=...
fly secrets set MINIO_ENDPOINT=<fly-minio.internal> MINIO_ACCESS_KEY=...

# Deploy
fly deploy
```

**fly.toml:**
```toml
app = "uhmp"

[build]
  dockerfile = "Dockerfile"

[[services]]
  port = 8000
  protocol = "tcp"
  [[services.ports]]
    port = 80
    handlers = ["http"]
  [[services.ports]]
    port = 443
    handlers = ["tls"]
```

---

## 7. Development Setup

### 7.1 Clone the Repository

```bash
git clone https://github.com/yourorg/uhmp.git
cd uhmp
```

### 7.2 Backend Setup

```bash
# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\Activate.ps1

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements-dev.txt

# Create environment file
cp .env.example .env
```

### 7.3 Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 7.4 Initialize the Database

```bash
# Run migrations
alembic upgrade head

# Seed initial data (admin user, test data)
python scripts/seed.py
```

### 7.5 Running the Full Stack

```bash
# Terminal 1: Database + Redis + MinIO (Docker)
docker compose -f docker-compose.dev.yml up -d db redis minio

# Terminal 2: Backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Celery Worker
source venv/bin/activate
celery -A app.tasks worker --loglevel=info --concurrency=4

# Terminal 4: Celery Beat (scheduler)
source venv/bin/activate
celery -A app.tasks beat --loglevel=info

# Terminal 5: Frontend
cd frontend && npm run dev
```

**Or, use the all-in-one dev command:**
```bash
# Requires tmux (Linux/macOS) or PowerShell ConPTY (Windows)
python scripts/dev.py
```

### 7.6 Quick Start Script

```bash
#!/bin/bash
# dev-start.sh — Start all services for development

echo "Starting dependencies (Docker)..."
docker compose -f docker-compose.dev.yml up -d db redis minio

echo "Starting Celery worker..."
source venv/bin/activate
celery -A app.tasks worker --loglevel=info --concurrency=2 &
CELERY_PID=$!

echo "Starting Celery beat..."
celery -A app.tasks beat --loglevel=info &
BEAT_PID=$!

echo "Starting API server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "All services started."
echo "API: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Flower: http://localhost:5555"
echo "MinIO Console: http://localhost:9001"
echo ""
echo "Press Ctrl+C to stop all services."

trap "kill $CELERY_PID $BEAT_PID $API_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

---

## 8. Production Setup

### 8.1 Environment Variables

Create a `.env` file (see **CONFIGURATION.md** for all variables):

```bash
# Required
SECRET_KEY=<generate-with-openssl rand -hex 64>
DATABASE_URL=postgresql+asyncpg://uhmp:${DB_PASSWORD}@db:5432/uhmp
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=<generate-32-char-string>
MINIO_SECRET_KEY=<generate-64-char-string>

# Security
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=/etc/ssl/private/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/etc/ssl/certs/jwt_public.pem
CORS_ORIGINS=https://uhmp.example.com
RATE_LIMIT_PER_MINUTE=60

# ML
MODEL_DIR=/data/models
ACTIVE_MODEL_VERSION=v1.0.0
DRIFT_THRESHOLD=0.15

# Monitoring
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
```

### 8.2 SSL Certificate

```bash
# Using Let's Encrypt (Certbot)
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d uhmp.example.com

# Or with Docker
docker run -it --rm -p 80:80 -p 443:443 \
  -v nginx_ssl:/etc/letsencrypt \
  certbot/certbot certonly --standalone -d uhmp.example.com
```

### 8.3 Nginx Configuration

See **CONFIGURATION.md** for the full Nginx configuration. Key points:

- SSL termination
- Reverse proxy to backend (port 8000)
- Serve static frontend files
- Rate limiting (60 req/min per IP)
- Gzip compression
- Security headers (CSP, HSTS, X-Frame-Options)
- Request body size limit (2 GB for uploads)

### 8.4 Monitoring Stack

```bash
# Prometheus is included in docker-compose.prod.yml
# Grafana is included in docker-compose.prod.yml

# Access
# Prometheus: http://uhmp.example.com:9090
# Grafana: http://uhmp.example.com:3000 (admin / <GRAFANA_PASSWORD>)
```

**Pre-configured Grafana dashboards:**
1. **API Performance** — Request rate, latency, error rate, endpoints breakdown
2. **Celery Workers** — Queue depth, task success/failure, worker count
3. **Database** — Connection count, query time, cache hit ratio
4. **System Resources** — CPU, RAM, disk, network per container
5. **ML Model** — Prediction requests, inference time, drift score

### 8.5 Backup Strategy

```bash
# Database backup
pg_dump -U uhmp -h localhost uhmp > /backups/uhmp_$(date +%Y%m%d).sql

# Automated backup script — add to cron (daily)
0 2 * * * /opt/uhmp/scripts/backup.sh
```

**backup.sh:**
```bash
#!/bin/bash
BACKUP_DIR=/backups
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Database
pg_dump -U uhmp -h localhost uhmp | gzip > $BACKUP_DIR/db_$TIMESTAMP.sql.gz

# MinIO data
rclone sync minio:uhmp $BACKUP_DIR/minio_$TIMESTAMP --backup-dir $BACKUP_DIR/minio_prev

# Configuration
cp /opt/uhmp/.env $BACKUP_DIR/env_$TIMESTAMP

# Cleanup old backups
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "minio_*" -mtime +$RETENTION_DAYS -exec rm -rf {} \;
find $BACKUP_DIR -name "env_*" -mtime +$RETENTION_DAYS -delete
```

---

## 9. Verifying the Installation

### 9.1 Health Check Endpoint

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-07-02T12:00:00Z",
  "components": {
    "database": { "status": "connected", "latency_ms": 3 },
    "redis": { "status": "connected", "latency_ms": 1 },
    "minio": { "status": "connected", "latency_ms": 5 },
    "celery": { "status": "connected", "workers": 4 }
  },
  "uptime_seconds": 86400
}
```

### 9.2 Running Tests

```bash
# Backend tests (pytest)
source venv/bin/activate
pytest tests/ -v --cov=app --cov-report=term-missing

# Frontend tests (Vitest)
cd frontend && npm run test

# Lint checks
ruff check app/
mypy app/ --strict
cd frontend && npm run lint && npm run typecheck
```

### 9.3 Integration Test

```bash
# Upload a test scene
curl -X POST http://localhost:8000/api/v1/scenes/upload \
  -F "file=@tests/fixtures/sample_scene.tif" \
  -H "Authorization: Bearer <token>"

# Run preprocessing
curl -X POST http://localhost:8000/api/v1/scenes/1/preprocess \
  -H "Authorization: Bearer <token>"

# Check status
curl http://localhost:8000/api/v1/scenes/1 \
  -H "Authorization: Bearer <token>"
```

### 9.4 Frontend Smoke Test

```bash
# Check that the frontend serves
curl -s http://localhost:5173 | head -5
# Expected: HTML with <div id="root">
```

---

## 10. Troubleshooting Installation Issues

| # | Problem | Cause | Solution |
|---|---|---|---|
| 1 | `pip install` fails with GDAL error | GDAL library not found or version mismatch | Install GDAL system package first, then `pip install GDAL==$(gdal-config --version)` |
| 2 | `docker compose up` fails with port conflict | Port 5432 or 6379 already in use | Stop local PostgreSQL/Redis, or change mapped ports in docker-compose.yml |
| 3 | Database connection refused | PostgreSQL not running or wrong credentials | Check `pg_isready`, verify DATABASE_URL in .env |
| 4 | Alembic migration fails | Database schema mismatch | Drop and recreate: `dropdb uhmp && createdb uhmp && psql -d uhmp -c "CREATE EXTENSION postgis;"` |
| 5 | "No module named 'app'" | PYTHONPATH not set or wrong directory | Run from project root or `export PYTHONPATH=$PWD` |
| 6 | Map tiles not rendering | MapLibre token missing or API limit | Check `VITE_MAPBOX_TOKEN` or switch to free tile provider |
| 7 | Celery tasks not executing | Redis not running or wrong broker URL | Verify `redis-cli ping` returns PONG |
| 8 | MinIO connection refused | MinIO container not started | `docker compose ps` to check; verify MINIO_ENDPOINT |
| 9 | Permission denied on volume mount | Docker Desktop file sharing not configured | Add project directory to Docker Desktop → Settings → Resources → File Sharing |
| 10 | Nginx 502 Bad Gateway | Backend not running or wrong proxy_pass | `systemctl status uhmp-api`; check nginx error log |

---

*© 2026 Urban Heat Mitigation Platform. All rights reserved.*
*For installation support, contact devops@uhmp.example.com*
