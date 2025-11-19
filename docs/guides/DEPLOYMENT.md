# CodeGraph Deployment Guide

## Table of Contents

- [Overview](#overview)
- [Deployment Options](#deployment-options)
- [Production Setup](#production-setup)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Security](#security)
- [Monitoring & Logging](#monitoring--logging)
- [Scaling](#scaling)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

---

## Overview

CodeGraph consists of three main components:
1. **Neo4j Database** - Graph storage
2. **FastAPI Backend** - REST API and MCP server
3. **React Frontend** - Visualization UI (optional)

This guide covers deploying all components for production use.

---

## Deployment Options

### Option 1: Docker Compose (Recommended)

**Best for:** Small to medium deployments, single server

**Pros:**
- Easy setup
- Consistent environment
- Simple scaling

**Cons:**
- Single point of failure
- Limited scaling

### Option 2: Kubernetes

**Best for:** Large deployments, high availability

**Pros:**
- Automatic scaling
- High availability
- Load balancing

**Cons:**
- Complex setup
- Higher resource requirements

### Option 3: Managed Services

**Best for:** Cloud-native deployments

**Pros:**
- Minimal maintenance
- Built-in scaling
- Managed backups

**Cons:**
- Higher cost
- Vendor lock-in

---

## Production Setup

### Prerequisites

- Server with 4GB+ RAM
- 20GB+ disk space
- Docker & Docker Compose (or Kubernetes)
- Domain name (optional)
- SSL certificate (recommended)

### Environment Configuration

Create production `.env` files:

**Backend (.env)**
```env
# Neo4j Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<strong-password>  # Change this!

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com

# Security
SECRET_KEY=<random-secret-key>  # Generate with: openssl rand -hex 32
API_KEY_ENABLED=true
API_KEY=<your-api-key>

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/codegraph/app.log

# Production
DEBUG=false
ENVIRONMENT=production
```

**Frontend (.env.production)**
```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com/ws
```

---

## Docker Deployment

### Basic Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: codegraph-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_server_memory_heap_initial__size=1G
      - NEO4J_server_memory_heap_max__size=2G
      - NEO4J_server_memory_pagecache_size=1G
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - neo4j_plugins:/plugins
    restart: unless-stopped
    networks:
      - codegraph-network
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p ${NEO4J_PASSWORD} 'RETURN 1'"]
      interval: 30s
      timeout: 10s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: codegraph-backend
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - LOG_LEVEL=INFO
      - DEBUG=false
    volumes:
      - ./backend:/app
      - backend_logs:/var/log/codegraph
    depends_on:
      neo4j:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - codegraph-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
      args:
        - VITE_API_BASE_URL=https://api.yourdomain.com
    container_name: codegraph-frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - codegraph-network

  # Optional: Reverse proxy
  nginx:
    image: nginx:alpine
    container_name: codegraph-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
    networks:
      - codegraph-network

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:
  backend_logs:

networks:
  codegraph-network:
    driver: bridge
```

### Production Dockerfile (Backend)

**backend/Dockerfile.prod:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 codegraph && \
    chown -R codegraph:codegraph /app

USER codegraph

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Production Dockerfile (Frontend)

**frontend/Dockerfile.prod:**
```dockerfile
# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

**nginx.conf:**
```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/x-javascript application/xml+rss application/json;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # Backend upstream
    upstream backend {
        server backend:8000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        # SSL configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Frontend
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        # API proxy
        location /api/ {
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # WebSocket proxy
        location /ws {
            proxy_pass http://backend/ws;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```

### Deploy with Docker Compose

```bash
# Set environment variables
export NEO4J_PASSWORD=your_strong_password

# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

---

## Cloud Deployment

### AWS Deployment

#### Using EC2

1. **Launch EC2 Instance**
   - Instance type: t3.medium or larger
   - Storage: 30GB+ EBS volume
   - Security group: Allow ports 22, 80, 443

2. **Install Docker**
```bash
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user
```

3. **Deploy with Docker Compose**
```bash
git clone https://github.com/yourusername/codegraph.git
cd codegraph
docker-compose -f docker-compose.prod.yml up -d
```

#### Using ECS (Elastic Container Service)

**Task Definition:**
```json
{
  "family": "codegraph",
  "containerDefinitions": [
    {
      "name": "neo4j",
      "image": "neo4j:5.15-community",
      "memory": 2048,
      "portMappings": [
        {"containerPort": 7474},
        {"containerPort": 7687}
      ],
      "environment": [
        {"name": "NEO4J_AUTH", "value": "neo4j/password"}
      ]
    },
    {
      "name": "backend",
      "image": "your-registry/codegraph-backend:latest",
      "memory": 1024,
      "portMappings": [
        {"containerPort": 8000}
      ],
      "environment": [
        {"name": "NEO4J_URI", "value": "bolt://neo4j:7687"}
      ],
      "dependsOn": [
        {
          "containerName": "neo4j",
          "condition": "HEALTHY"
        }
      ]
    }
  ]
}
```

#### Using RDS for Neo4j (Alternative)

Use AWS Neptune (graph database) or run Neo4j on a dedicated EC2 instance.

### Google Cloud Platform

#### Using Compute Engine

```bash
# Create instance
gcloud compute instances create codegraph \
  --machine-type=e2-medium \
  --boot-disk-size=30GB \
  --tags=http-server,https-server

# SSH and deploy
gcloud compute ssh codegraph
# Follow Docker deployment steps
```

#### Using Cloud Run

Deploy backend as serverless container:

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/codegraph-backend

# Deploy to Cloud Run
gcloud run deploy codegraph-backend \
  --image gcr.io/PROJECT_ID/codegraph-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure

#### Using App Service

```bash
# Create resource group
az group create --name codegraph-rg --location eastus

# Create App Service plan
az appservice plan create \
  --name codegraph-plan \
  --resource-group codegraph-rg \
  --is-linux \
  --sku B1

# Create web app
az webapp create \
  --name codegraph-api \
  --resource-group codegraph-rg \
  --plan codegraph-plan \
  --deployment-container-image-name your-registry/codegraph-backend:latest
```

### DigitalOcean

#### Using App Platform

Create `app.yaml`:

```yaml
name: codegraph
services:
  - name: backend
    github:
      repo: yourusername/codegraph
      branch: main
      deploy_on_push: true
    dockerfile_path: backend/Dockerfile.prod
    http_port: 8000
    instance_count: 2
    instance_size_slug: basic-xs
    envs:
      - key: NEO4J_URI
        value: ${neo4j.PRIVATE_URL}
      - key: NEO4J_PASSWORD
        scope: RUN_TIME
        type: SECRET
        value: ${NEO4J_PASSWORD}

databases:
  - name: neo4j
    engine: NEO4J
    version: "5"
```

Deploy:
```bash
doctl apps create --spec app.yaml
```

---

## Security

### Authentication & Authorization

#### API Key Authentication

**Enable in backend:**

```python
# app/middleware/auth.py
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Apply to protected routes
@app.get("/protected", dependencies=[Depends(verify_api_key)])
async def protected_route():
    return {"message": "Authorized"}
```

**Client usage:**
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/validate
```

#### OAuth2 (Optional)

For enterprise deployments, integrate OAuth2:

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Validate JWT token
    # Return user object
    pass
```

### Neo4j Security

**Strong password:**
```env
NEO4J_PASSWORD=$(openssl rand -base64 32)
```

**Disable external access:**
```yaml
# docker-compose.prod.yml
neo4j:
  ports:
    - "127.0.0.1:7474:7474"  # Only localhost
    - "127.0.0.1:7687:7687"
```

**Enable encryption:**
```env
NEO4J_dbms_connector_bolt_tls__level=REQUIRED
```

### HTTPS/TLS

#### Using Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt-get install certbot

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be in:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem

# Auto-renewal
sudo crontab -e
# Add: 0 0 * * * certbot renew --quiet
```

Update nginx config to use certificates (see nginx.conf above).

### Firewall Configuration

```bash
# Ubuntu/Debian with ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# RedHat/CentOS with firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Network Segmentation

Use Docker networks to isolate components:

```yaml
networks:
  frontend-network:
    driver: bridge
  backend-network:
    driver: bridge
    internal: true  # No external access

services:
  neo4j:
    networks:
      - backend-network  # Only accessible from backend

  backend:
    networks:
      - frontend-network
      - backend-network

  frontend:
    networks:
      - frontend-network
```

---

## Monitoring & Logging

### Application Logging

**Structured logging:**

```python
# backend/app/logging_config.py
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": "/var/log/codegraph/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### Metrics with Prometheus

**Add metrics endpoint:**

```python
# backend/app/metrics.py
from prometheus_client import Counter, Histogram, generate_latest

indexing_requests = Counter('codegraph_indexing_requests_total', 'Total indexing requests')
validation_duration = Histogram('codegraph_validation_duration_seconds', 'Validation duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Prometheus config:**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'codegraph'
    static_configs:
      - targets: ['backend:8000']
```

### Grafana Dashboard

Import pre-built dashboard or create custom:

```json
{
  "dashboard": {
    "title": "CodeGraph Metrics",
    "panels": [
      {
        "title": "Indexing Rate",
        "targets": [
          {
            "expr": "rate(codegraph_indexing_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Validation Duration",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, codegraph_validation_duration_seconds)"
          }
        ]
      }
    ]
  }
}
```

### Health Checks

**Kubernetes liveness/readiness probes:**

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Scaling

### Horizontal Scaling

#### Backend Scaling

Run multiple backend instances behind load balancer:

```yaml
# docker-compose.prod.yml
backend:
  deploy:
    replicas: 3
```

Or with Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codegraph-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: codegraph-backend
  template:
    metadata:
      labels:
        app: codegraph-backend
    spec:
      containers:
      - name: backend
        image: your-registry/codegraph-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URI
          value: "bolt://neo4j:7687"
```

#### Neo4j Clustering

For high availability, use Neo4j Enterprise with clustering:

```yaml
neo4j-core-1:
  image: neo4j:5.15-enterprise
  environment:
    - NEO4J_dbms_mode=CORE
    - NEO4J_causal__clustering_initial__discovery__members=neo4j-core-1:5000,neo4j-core-2:5000,neo4j-core-3:5000

neo4j-core-2:
  # Same config with different hostname

neo4j-core-3:
  # Same config with different hostname
```

### Vertical Scaling

**Neo4j memory tuning:**

```env
# For 8GB server
NEO4J_server_memory_heap_initial__size=2G
NEO4J_server_memory_heap_max__size=4G
NEO4J_server_memory_pagecache_size=2G
```

**Backend workers:**

```bash
# Increase workers based on CPU cores
uvicorn app.main:app --workers $(nproc)
```

---

## Backup & Recovery

### Neo4j Backup

**Automated backups:**

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR=/backups/neo4j
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
docker exec codegraph-neo4j neo4j-admin database dump neo4j \
  --to-path=/backups --to-stdout > $BACKUP_DIR/neo4j_$DATE.dump

# Compress
gzip $BACKUP_DIR/neo4j_$DATE.dump

# Delete old backups (keep last 7 days)
find $BACKUP_DIR -name "*.dump.gz" -mtime +7 -delete
```

**Schedule with cron:**
```bash
0 2 * * * /path/to/backup.sh
```

**Restore from backup:**

```bash
# Stop Neo4j
docker-compose -f docker-compose.prod.yml stop neo4j

# Restore
gunzip -c neo4j_backup.dump.gz | \
  docker exec -i codegraph-neo4j neo4j-admin database load neo4j \
  --from-stdin

# Start Neo4j
docker-compose -f docker-compose.prod.yml start neo4j
```

### Disaster Recovery

**Offsite backups:**

```bash
# Upload to S3
aws s3 cp neo4j_backup.dump.gz s3://mybucket/backups/

# Upload to Google Cloud Storage
gsutil cp neo4j_backup.dump.gz gs://mybucket/backups/
```

**Recovery plan:**
1. Provision new infrastructure
2. Deploy application from git
3. Restore Neo4j from latest backup
4. Test health endpoint
5. Update DNS to point to new instance

---

## Troubleshooting

### Common Issues

#### Out of Memory

**Symptom:** Neo4j crashes or becomes unresponsive

**Solution:**
```env
# Increase memory limits
NEO4J_server_memory_heap_max__size=4G
NEO4J_server_memory_pagecache_size=2G
```

#### Connection Timeouts

**Symptom:** API requests timeout

**Solution:**
```nginx
# Increase nginx timeouts
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

#### Database Lock

**Symptom:** "Database is locked" error

**Solution:**
```bash
# Ensure only one Neo4j instance is running
docker ps | grep neo4j

# Check for orphaned processes
ps aux | grep neo4j
```

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=DEBUG
DEBUG=true
```

View logs:
```bash
# Docker Compose
docker-compose logs -f backend

# Kubernetes
kubectl logs -f deployment/codegraph-backend
```

---

## Performance Tuning

### Neo4j Tuning

```env
# Thread pool size (based on CPU cores)
NEO4J_dbms_threads_worker_count=8

# Query timeout
NEO4J_dbms_transaction_timeout=30s

# Index configuration
NEO4J_dbms_index_fulltext_eventually__consistent=true
```

### Backend Tuning

```python
# app/main.py
app = FastAPI(
    # Connection pooling
    timeout=30.0,
    # Limit concurrent requests
    limit_concurrency=100
)
```

### Caching

Add Redis for caching:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="codegraph:")
```

---

## Checklist

Before going to production:

- [ ] Strong passwords set
- [ ] HTTPS/TLS configured
- [ ] Firewall rules applied
- [ ] Backups configured and tested
- [ ] Monitoring and alerting set up
- [ ] Health checks configured
- [ ] Resource limits set
- [ ] Logging configured
- [ ] Error tracking enabled (e.g., Sentry)
- [ ] Load testing performed
- [ ] Disaster recovery plan documented
- [ ] Security audit completed

---

**Last Updated:** 2025-01-19
**Version:** 1.0.0
