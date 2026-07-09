# Infrastructure Architecture

## Architecture Diagram

```
                                   Internet
                                      │
                                   [DNS]
                                      │
                                 [CDN (optional)]
                                      │
                            ┌─────────▼─────────┐
                            │    Nginx :443      │
                            │  (Reverse Proxy)   │
                            └──┬──────────┬──────┘
                               │          │
                    ┌──────────▼──┐  ┌────▼──────────┐
                    │  Frontend   │  │   Backend     │
                    │  React SPA  │  │  FastAPI      │
                    │  :80/443    │  │  :8000        │
                    └──────┬──────┘  └──┬────────────┘
                               │          │
                               │   ┌──────▼───────┐
                               │   │   Worker     │
                               │   │  (Celery)    │
                               │   └──────┬───────┘
                               │          │
                    ┌──────────▼──────────▼──────────┐
                    │         Message Queue          │
                    │        (Redis/Broker)          │
                    └───────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  PostgreSQL   │  │    Redis     │  │       MinIO         │   │
│  │  + PostGIS    │  │   (Cache)    │  │  (Object Storage)   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                     Observability Stack                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Prometheus   │  │   Grafana    │  │        Loki          │   │
│  │  (Metrics)    │  │ (Dashboards) │  │   (Logs Aggregation) │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐                              │
│  │  Promtail    │  │  OpenTelemetry│                             │
│  │ (Log Shipper)│  │  (Traces)     │                              │
│  └──────────────┘  └──────────────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

## Network Architecture

```
Public Network (80, 443)
  │
  ├── Nginx (Reverse Proxy)
  │     ├── /api/* → Backend :8000
  │     ├── /ws/*  → Backend :8000
  │     ├── /*     → Frontend :80
  │     └── /grafana/* → Grafana :3000
  │
Internal Network (urbanheat-network)
  ├── postgres:5432
  ├── redis:6379
  ├── minio:9000
  ├── prometheus:9090
  ├── loki:3100
  └── otel-collector:4317
```

## Data Flow

```
User Request
  │
  ▼
Nginx (HTTPS termination, rate limiting, caching)
  │
  ├── Static assets → Frontend (served directly)
  │
  └── API request → Backend (FastAPI)
        │
        ├── Read → Cache (Redis) → DB (PostgreSQL)
        │
        ├── Write → DB (PostgreSQL) → Queue (Redis)
        │                              │
        │                              └── Worker (Celery)
        │                                    ├── Satellite acquisition
        │                                    ├── Raster processing
        │                                    ├── ML training
        │                                    └── Report generation
        │
        ├── ML → ML Engine → Feature Store → Model Registry
        │
        ├── Storage → MinIO (rasters, models, exports)
        │
        └── Metrics → OpenTelemetry → Prometheus/Loki
```

## Docker Compose Structure

```
deploy/
├── docker-compose.dev.yml     # Development stack
├── docker-compose.prod.yml     # Production stack
├── docker-compose.https.yml    # HTTPS overlay
├── docker/                     # Dockerfiles
├── nginx/                      # Nginx configurations
├── monitoring/                 # Observability configs
├── database/                   # DB scripts
├── scripts/                    # Deployment scripts
├── security/                   # Hardening scripts
└── docs/deployment/            # Documentation
```

## Production Topology

### Single Server (Recommended for < 1000 users)

All services on one machine with Docker Compose.

### Multi-Server (1000+ users)

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Load Balancer  │  │  Load Balancer  │  │  Load Balancer  │
│  (HAProxy/Nginx)│  │  (HAProxy/Nginx)│  │  (HAProxy/Nginx)│
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                   │                     │
    ┌────▼────┐         ┌────▼────┐          ┌─────▼────┐
    │ Node 1  │         │ Node 2  │          │  Node 3  │
    │ Backend │         │ Backend │          │  Backend │
    │ Worker  │         │ Worker  │          │  Worker  │
    └─────────┘         └─────────┘          └──────────┘
         │                   │                     │
         └───────────────────┼─────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Shared Services│
                    │  PostgreSQL     │
                    │  Redis          │
                    │  MinIO          │
                    └─────────────────┘
```

## Deployment Environments

| Environment | Purpose | Frequency |
|-------------|---------|-----------|
| Development | Local dev with hot-reload | Continuous |
| Staging | Pre-production validation | Per PR |
| Production | Live platform | Tagged releases |
| DR | Disaster recovery | On-demand |

## Cost Estimation

| Service | Small | Medium | Large |
|---------|-------|--------|-------|
| VM (CPU/RAM) | $30/mo | $100/mo | $400/mo |
| Storage (disk) | $10/mo | $30/mo | $100/mo |
| Object storage | $5/mo | $20/mo | $80/mo |
| Bandwidth | $10/mo | $50/mo | $200/mo |
| Monitoring | $0 (self-hosted) | $0 | $0 |
| **Total** | **~$55/mo** | **~$200/mo** | **~$780/mo** |
