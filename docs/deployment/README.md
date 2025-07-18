# DIPC Deployment Guide

This guide provides comprehensive instructions for deploying the Document Intelligence & Parsing Center (DIPC) in various environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Quick Start

For development and testing, you can get DIPC running quickly with Docker Compose:

```bash
# Clone the repository
git clone https://github.com/your-org/dipc.git
cd dipc

# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

The application will be available at:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 50GB available space
- Network: Stable internet connection for LLM API calls

**Recommended for Production:**
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 200GB+ SSD
- Network: High-bandwidth connection

### Software Dependencies

- Docker 20.10+
- Docker Compose 2.0+
- Git
- (Optional) Kubernetes 1.20+ for production deployment

### External Services

You'll need accounts and API keys for:
- **LLM Provider**: OpenAI, OpenRouter, or compatible service
- **Object Storage**: AWS S3, MinIO, or compatible service
- **Vector Database**: Qdrant or Milvus (optional)
- **Monitoring**: Prometheus/Grafana (recommended for production)

## Environment Configuration

### Core Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://dipc_user:secure_password@db:5432/dipc_db
POSTGRES_USER=dipc_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=dipc_db

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Object Storage (S3/MinIO)
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=dipc-storage
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_REGION=us-east-1

# LLM Provider Configuration
OPENAI_API_KEY=sk-your-openai-key
OPENROUTER_API_KEY=sk-or-your-openrouter-key
LITELM_BASE_URL=https://your-litelm-endpoint.com
LITELM_API_KEY=your-litelm-key

# Vector Database (Optional)
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=your-qdrant-key

# Application Configuration
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_PORT=3000
WORKER_CONCURRENCY=4

# Security
SECRET_KEY=your-very-secure-secret-key-here
CORS_ORIGINS=http://localhost:3000,https://your-domain.com

# Monitoring
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
```

### Security Configuration

For production deployments, ensure:

```bash
# Generate secure secrets
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Enable SSL/TLS
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem

# Configure authentication
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_EXPIRATION_HOURS=24
```

## Docker Deployment

### Development Deployment

```bash
# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Run database migrations
docker-compose exec api python -m alembic upgrade head

# Create test user (optional)
docker-compose exec api python scripts/create_test_user.py
```

### Production Deployment

```bash
# Use production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale workers based on load
docker-compose up -d --scale worker=4

# Enable monitoring
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### Service Configuration

#### API Service

```yaml
# docker-compose.yml excerpt
api:
  build: ./api
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - REDIS_URL=${REDIS_URL}
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  ports:
    - "8000:8000"
  depends_on:
    - db
    - redis
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/v1/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

#### Worker Service

```yaml
worker:
  build: ./workers
  environment:
    - CELERY_BROKER_URL=${REDIS_URL}
    - DATABASE_URL=${DATABASE_URL}
    - OPENAI_API_KEY=${OPENAI_API_KEY}
  depends_on:
    - redis
    - db
  deploy:
    replicas: 3
```

#### Frontend Service

```yaml
frontend:
  build: ./frontend
  environment:
    - NEXT_PUBLIC_API_URL=http://api:8000
  ports:
    - "3000:3000"
  depends_on:
    - api
```

## Production Deployment

### Kubernetes Deployment

For production-scale deployments, use Kubernetes:

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/database.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/workers.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml

# Check deployment status
kubectl get pods -n dipc
kubectl get services -n dipc
```

### Load Balancing

Configure load balancing for high availability:

```nginx
# nginx.conf
upstream dipc_api {
    server api-1:8000;
    server api-2:8000;
    server api-3:8000;
}

upstream dipc_frontend {
    server frontend-1:3000;
    server frontend-2:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location /api/ {
        proxy_pass http://dipc_api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location / {
        proxy_pass http://dipc_frontend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Setup

#### PostgreSQL Configuration

```sql
-- Create database and user
CREATE DATABASE dipc_db;
CREATE USER dipc_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE dipc_db TO dipc_user;

-- Configure connection limits
ALTER USER dipc_user CONNECTION LIMIT 50;

-- Enable required extensions
\c dipc_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

#### Database Migrations

```bash
# Run migrations
docker-compose exec api python -m alembic upgrade head

# Create migration (if needed)
docker-compose exec api python -m alembic revision --autogenerate -m "description"
```

### SSL/TLS Configuration

```bash
# Generate SSL certificates (Let's Encrypt)
certbot certonly --webroot -w /var/www/html -d your-domain.com

# Configure SSL in docker-compose
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt:ro
```

## Monitoring and Maintenance

### Health Checks

All services include health check endpoints:

```bash
# Check API health
curl http://localhost:8000/v1/health

# Check worker health
curl http://localhost:8001/health

# Check database connectivity
docker-compose exec api python scripts/check_db.py
```

### Monitoring Setup

#### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dipc-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    
  - job_name: 'dipc-workers'
    static_configs:
      - targets: ['worker:8001']
    metrics_path: '/metrics'
```

#### Grafana Dashboards

Import the provided Grafana dashboards:
- `monitoring/grafana/api-dashboard.json`
- `monitoring/grafana/worker-dashboard.json`
- `monitoring/grafana/system-dashboard.json`

### Log Management

```bash
# Configure log rotation
echo '/var/log/dipc/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}' > /etc/logrotate.d/dipc

# Centralized logging with ELK stack
docker-compose -f docker-compose.logging.yml up -d
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Database backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
docker-compose exec -T db pg_dump -U dipc_user dipc_db > "$BACKUP_DIR/db_backup_$DATE.sql"

# File storage backup (if using local storage)
tar -czf "$BACKUP_DIR/files_backup_$DATE.tar.gz" /path/to/file/storage

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

### Performance Tuning

#### Database Optimization

```sql
-- PostgreSQL performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
```

#### Worker Scaling

```bash
# Scale workers based on queue length
docker-compose up -d --scale worker=8

# Monitor queue metrics
docker-compose exec redis redis-cli monitor
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs api
docker-compose logs worker

# Check resource usage
docker stats

# Verify environment variables
docker-compose config
```

#### Database Connection Issues

```bash
# Test database connectivity
docker-compose exec api python -c "
from src.database.connection import get_db
try:
    db = next(get_db())
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

#### Worker Queue Issues

```bash
# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Monitor Celery workers
docker-compose exec worker celery -A tasks inspect active

# Purge stuck tasks
docker-compose exec worker celery -A tasks purge
```

#### High Memory Usage

```bash
# Monitor memory usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Restart services if needed
docker-compose restart worker
```

### Performance Issues

#### Slow API Responses

1. Check database query performance:
```sql
-- Enable query logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;
```

2. Monitor API metrics:
```bash
curl http://localhost:8000/metrics | grep http_request_duration
```

3. Scale API instances:
```bash
docker-compose up -d --scale api=3
```

#### Worker Bottlenecks

1. Monitor queue length:
```bash
docker-compose exec redis redis-cli llen celery
```

2. Scale workers:
```bash
docker-compose up -d --scale worker=6
```

3. Optimize task processing:
```python
# Adjust worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
```

### Security Issues

#### SSL Certificate Renewal

```bash
# Renew Let's Encrypt certificates
certbot renew --dry-run
certbot renew

# Restart nginx
docker-compose restart nginx
```

#### Security Scanning

```bash
# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image dipc_api:latest

# Check for exposed secrets
docker run --rm -v $(pwd):/src trufflesecurity/trufflehog filesystem /src
```

### Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/your-org/dipc/issues)
2. Review application logs for detailed error messages
3. Consult the [API documentation](http://localhost:8000/docs)
4. Contact support at support@dipc.example.com

## Maintenance Schedule

### Daily Tasks
- Monitor system health and performance metrics
- Check error logs for anomalies
- Verify backup completion

### Weekly Tasks
- Review and rotate log files
- Update security patches
- Performance optimization review

### Monthly Tasks
- Full system backup verification
- Security audit and vulnerability assessment
- Capacity planning review
- Update dependencies and base images