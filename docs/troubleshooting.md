# DIPC Troubleshooting Guide

This guide provides comprehensive troubleshooting information for the Document Intelligence & Parsing Center (DIPC) system.

## Table of Contents

- [System Health Monitoring](#system-health-monitoring)
- [Common Issues](#common-issues)
- [Performance Problems](#performance-problems)
- [Error Codes Reference](#error-codes-reference)
- [Log Analysis](#log-analysis)
- [Recovery Procedures](#recovery-procedures)
- [Maintenance Tasks](#maintenance-tasks)

## System Health Monitoring

### Health Check Endpoints

Monitor system health using these endpoints:

```bash
# API Gateway Health
curl http://localhost:8000/v1/health

# Worker Health
curl http://localhost:8001/health

# Database Health
curl http://localhost:8000/v1/health/db

# Redis Health
curl http://localhost:8000/v1/health/redis

# External Services Health
curl http://localhost:8000/v1/health/external
```

### Expected Health Responses

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.3.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 0.05,
      "connections": {
        "active": 5,
        "idle": 15,
        "max": 20
      }
    },
    "redis": {
      "status": "healthy",
      "response_time": 0.01,
      "memory_usage": "45MB"
    },
    "workers": {
      "status": "healthy",
      "active_workers": 4,
      "queue_length": 12
    },
    "external_services": {
      "llm_provider": {
        "status": "healthy",
        "response_time": 0.8
      },
      "storage": {
        "status": "healthy",
        "response_time": 0.2
      }
    }
  }
}
```

### Monitoring Dashboard

Access the monitoring dashboard at:
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

Key metrics to monitor:
- Request rate and response times
- Error rates by endpoint
- Queue length and processing times
- Resource utilization (CPU, memory, disk)
- External service availability

## Common Issues

### Service Startup Issues

#### API Service Won't Start

**Symptoms:**
- Container exits immediately
- Health check fails
- Port binding errors

**Diagnosis:**
```bash
# Check container logs
docker-compose logs api

# Check port availability
netstat -tulpn | grep :8000

# Verify environment variables
docker-compose exec api env | grep -E "(DATABASE|REDIS|API)"
```

**Solutions:**
1. **Port Conflict**: Change API_PORT in .env file
2. **Database Connection**: Verify DATABASE_URL and database availability
3. **Missing Environment Variables**: Check .env file completeness
4. **Permission Issues**: Ensure proper file permissions

#### Worker Service Issues

**Symptoms:**
- Workers not processing tasks
- High queue length
- Worker containers restarting

**Diagnosis:**
```bash
# Check worker status
docker-compose exec worker celery -A tasks inspect active

# Monitor queue
docker-compose exec redis redis-cli llen celery

# Check worker logs
docker-compose logs worker
```

**Solutions:**
1. **Redis Connection**: Verify REDIS_URL configuration
2. **Resource Limits**: Increase memory/CPU limits
3. **Task Failures**: Check for recurring task errors
4. **Scale Workers**: Increase worker replicas

### Database Issues

#### Connection Pool Exhaustion

**Symptoms:**
- "connection pool exhausted" errors
- Slow API responses
- Database connection timeouts

**Diagnosis:**
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Check connection limits
SELECT setting FROM pg_settings WHERE name = 'max_connections';

-- Identify long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

**Solutions:**
1. **Increase Pool Size**: Adjust database connection pool settings
2. **Kill Long Queries**: Terminate stuck queries
3. **Optimize Queries**: Review and optimize slow queries
4. **Connection Cleanup**: Implement proper connection cleanup

#### Database Performance Issues

**Symptoms:**
- Slow query responses
- High CPU usage on database
- Lock contention

**Diagnosis:**
```sql
-- Check slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check locks
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

**Solutions:**
1. **Add Indexes**: Create indexes for frequently queried columns
2. **Query Optimization**: Rewrite inefficient queries
3. **Vacuum/Analyze**: Regular database maintenance
4. **Hardware Upgrade**: Increase database server resources

### Queue and Worker Issues

#### Tasks Stuck in Queue

**Symptoms:**
- Tasks remain in pending status
- Queue length continuously growing
- No worker activity

**Diagnosis:**
```bash
# Check queue contents
docker-compose exec redis redis-cli lrange celery 0 -1

# Check worker status
docker-compose exec worker celery -A tasks inspect stats

# Monitor worker logs
docker-compose logs -f worker
```

**Solutions:**
1. **Restart Workers**: `docker-compose restart worker`
2. **Purge Queue**: `docker-compose exec worker celery -A tasks purge`
3. **Scale Workers**: `docker-compose up -d --scale worker=6`
4. **Check Task Code**: Review task implementation for errors

#### Memory Issues in Workers

**Symptoms:**
- Workers killed by OOM killer
- High memory usage
- Processing failures on large files

**Diagnosis:**
```bash
# Monitor memory usage
docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check worker memory limits
docker-compose exec worker cat /sys/fs/cgroup/memory/memory.limit_in_bytes
```

**Solutions:**
1. **Increase Memory Limits**: Update docker-compose.yml
2. **Optimize Processing**: Implement streaming for large files
3. **Add Swap**: Configure swap space on host
4. **Process Smaller Batches**: Reduce batch sizes

### External Service Issues

#### LLM API Failures

**Symptoms:**
- Tasks failing with API errors
- High response times
- Rate limiting errors

**Diagnosis:**
```bash
# Check API key validity
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Monitor API response times
grep "llm_api_call" /var/log/dipc/worker.log | tail -20
```

**Solutions:**
1. **API Key Issues**: Verify and rotate API keys
2. **Rate Limiting**: Implement exponential backoff
3. **Provider Switch**: Configure fallback providers
4. **Request Optimization**: Reduce token usage

#### Storage Service Issues

**Symptoms:**
- File upload failures
- Download errors
- Storage quota exceeded

**Diagnosis:**
```bash
# Test S3 connectivity
aws s3 ls s3://your-bucket --endpoint-url=$S3_ENDPOINT

# Check storage usage
aws s3api list-objects-v2 --bucket your-bucket --query 'sum(Contents[].Size)'
```

**Solutions:**
1. **Credentials**: Verify S3 access keys
2. **Permissions**: Check bucket policies
3. **Quota Management**: Implement cleanup policies
4. **Alternative Storage**: Configure backup storage

## Performance Problems

### High Response Times

**Symptoms:**
- API endpoints responding slowly
- User interface lag
- Timeout errors

**Investigation Steps:**

1. **Check System Resources:**
```bash
# CPU usage
top -p $(pgrep -d',' -f dipc)

# Memory usage
free -h

# Disk I/O
iostat -x 1 5

# Network
netstat -i
```

2. **Database Performance:**
```sql
-- Check active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE state = 'active' 
ORDER BY duration DESC;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE tablename = 'tasks';
```

3. **Application Metrics:**
```bash
# API response times
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/v1/health

# Queue metrics
docker-compose exec redis redis-cli info stats
```

**Solutions:**
1. **Scale Services**: Add more API/worker instances
2. **Database Tuning**: Optimize queries and indexes
3. **Caching**: Implement Redis caching for frequent queries
4. **Load Balancing**: Distribute traffic across instances

### High Memory Usage

**Symptoms:**
- Out of memory errors
- Swap usage increasing
- Container restarts

**Investigation:**
```bash
# Memory usage by process
ps aux --sort=-%mem | head -20

# Container memory usage
docker stats --no-stream

# System memory
cat /proc/meminfo
```

**Solutions:**
1. **Memory Limits**: Set appropriate container limits
2. **Memory Leaks**: Profile application for leaks
3. **Garbage Collection**: Tune GC settings
4. **Resource Cleanup**: Implement proper resource cleanup

## Error Codes Reference

### API Error Codes

| Code | Description | Cause | Solution |
|------|-------------|-------|----------|
| INVALID_REQUEST | Malformed request | Missing required fields | Check request format |
| FILE_TOO_LARGE | File exceeds size limit | File > 50MB | Reduce file size |
| UNSUPPORTED_FORMAT | File format not supported | Invalid file type | Use supported format |
| COST_LIMIT_EXCEEDED | Processing cost too high | Document too large/complex | Increase limit or reduce size |
| RATE_LIMITED | Too many requests | Exceeded rate limit | Wait and retry |
| TASK_NOT_FOUND | Task ID doesn't exist | Invalid task ID | Check task ID |
| PROCESSING_FAILED | Task processing error | Various causes | Check task logs |
| STORAGE_ERROR | File storage issue | S3/storage problem | Check storage service |
| AUTH_REQUIRED | Authentication needed | Missing/invalid auth | Provide valid credentials |
| INTERNAL_ERROR | Server error | System issue | Contact support |

### Worker Error Codes

| Code | Description | Cause | Solution |
|------|-------------|-------|----------|
| ZIP_BOMB_DETECTED | Malicious ZIP file | Compressed ratio too high | Use legitimate ZIP files |
| PATH_TRAVERSAL | Malicious file paths | Directory traversal attempt | Clean file paths |
| LLM_API_ERROR | LLM service failure | API key/quota issues | Check LLM service |
| TIMEOUT | Processing timeout | Task took too long | Reduce document size |
| MEMORY_ERROR | Out of memory | Document too large | Increase worker memory |
| NETWORK_ERROR | Network connectivity | Internet/service issue | Check connectivity |

## Log Analysis

### Log Locations

```bash
# API logs
docker-compose logs api

# Worker logs  
docker-compose logs worker

# Database logs
docker-compose logs db

# System logs
journalctl -u docker
```

### Important Log Patterns

#### Error Patterns
```bash
# API errors
grep -E "(ERROR|CRITICAL)" /var/log/dipc/api.log

# Worker failures
grep -E "(FAILED|ERROR)" /var/log/dipc/worker.log

# Database errors
grep -E "(ERROR|FATAL)" /var/log/postgresql/postgresql.log
```

#### Performance Patterns
```bash
# Slow queries
grep "slow query" /var/log/dipc/api.log

# High memory usage
grep "memory" /var/log/dipc/worker.log

# Queue buildup
grep "queue_length" /var/log/dipc/metrics.log
```

### Log Analysis Tools

```bash
# Real-time monitoring
tail -f /var/log/dipc/*.log | grep ERROR

# Log aggregation
docker-compose logs -f | grep -E "(ERROR|WARN|CRITICAL)"

# Pattern analysis
awk '/ERROR/ {print $1, $2, $NF}' /var/log/dipc/api.log | sort | uniq -c
```

## Recovery Procedures

### Service Recovery

#### Complete System Recovery
```bash
# Stop all services
docker-compose down

# Clean up containers and volumes
docker system prune -f
docker volume prune -f

# Restart services
docker-compose up -d

# Verify health
./scripts/health_check.sh
```

#### Database Recovery
```bash
# Stop API and workers
docker-compose stop api worker

# Backup current database
docker-compose exec db pg_dump -U dipc_user dipc_db > backup.sql

# Restore from backup
docker-compose exec -T db psql -U dipc_user dipc_db < backup.sql

# Restart services
docker-compose start api worker
```

#### Queue Recovery
```bash
# Clear stuck tasks
docker-compose exec redis redis-cli flushdb

# Restart workers
docker-compose restart worker

# Requeue failed tasks (if needed)
docker-compose exec api python scripts/requeue_failed_tasks.py
```

### Data Recovery

#### File Recovery
```bash
# Check S3 backup
aws s3 ls s3://dipc-backup/

# Restore files from backup
aws s3 sync s3://dipc-backup/ /local/restore/

# Update database references
docker-compose exec api python scripts/update_file_paths.py
```

#### Task Recovery
```bash
# Find incomplete tasks
docker-compose exec api python scripts/find_incomplete_tasks.py

# Restart failed tasks
docker-compose exec api python scripts/restart_failed_tasks.py

# Clean up orphaned tasks
docker-compose exec api python scripts/cleanup_orphaned_tasks.py
```

## Maintenance Tasks

### Daily Maintenance

```bash
#!/bin/bash
# daily_maintenance.sh

# Check system health
curl -f http://localhost:8000/v1/health || echo "Health check failed"

# Monitor disk usage
df -h | awk '$5 > 80 {print "Disk usage high: " $0}'

# Check error logs
grep -c ERROR /var/log/dipc/*.log

# Backup database
docker-compose exec -T db pg_dump -U dipc_user dipc_db > "backup_$(date +%Y%m%d).sql"

# Clean up old logs
find /var/log/dipc -name "*.log" -mtime +7 -delete
```

### Weekly Maintenance

```bash
#!/bin/bash
# weekly_maintenance.sh

# Update system packages
apt update && apt upgrade -y

# Restart services for memory cleanup
docker-compose restart worker

# Vacuum database
docker-compose exec db psql -U dipc_user -d dipc_db -c "VACUUM ANALYZE;"

# Clean up old files
docker-compose exec api python scripts/cleanup_old_files.py

# Generate performance report
docker-compose exec api python scripts/performance_report.py
```

### Monthly Maintenance

```bash
#!/bin/bash
# monthly_maintenance.sh

# Full system backup
./scripts/full_backup.sh

# Security updates
docker-compose pull
docker-compose up -d

# Performance optimization
docker-compose exec db psql -U dipc_user -d dipc_db -c "REINDEX DATABASE dipc_db;"

# Capacity planning review
docker-compose exec api python scripts/capacity_report.py

# Update SSL certificates
certbot renew
```

### Monitoring Scripts

```bash
#!/bin/bash
# monitor.sh - Continuous monitoring script

while true; do
    # Check service health
    if ! curl -f http://localhost:8000/v1/health > /dev/null 2>&1; then
        echo "$(date): Health check failed" >> /var/log/dipc/monitor.log
        # Send alert
        ./scripts/send_alert.sh "DIPC health check failed"
    fi
    
    # Check queue length
    QUEUE_LENGTH=$(docker-compose exec redis redis-cli llen celery)
    if [ "$QUEUE_LENGTH" -gt 100 ]; then
        echo "$(date): High queue length: $QUEUE_LENGTH" >> /var/log/dipc/monitor.log
    fi
    
    # Check disk space
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 85 ]; then
        echo "$(date): High disk usage: $DISK_USAGE%" >> /var/log/dipc/monitor.log
        ./scripts/send_alert.sh "High disk usage: $DISK_USAGE%"
    fi
    
    sleep 60
done
```

## Getting Support

### Before Contacting Support

1. **Check System Status**: Review health endpoints and monitoring dashboards
2. **Collect Logs**: Gather relevant log files and error messages
3. **Document Steps**: Record steps to reproduce the issue
4. **Check Resources**: Verify system resources (CPU, memory, disk)

### Support Information to Provide

- **System Information**: OS, Docker version, DIPC version
- **Error Messages**: Complete error messages and stack traces
- **Log Files**: Relevant log excerpts (sanitized of sensitive data)
- **Configuration**: Environment variables and configuration files
- **Timeline**: When the issue started and any recent changes

### Contact Information

- **Email**: support@dipc.example.com
- **Emergency**: emergency@dipc.example.com (for production outages)
- **Documentation**: https://docs.dipc.example.com
- **Status Page**: https://status.dipc.example.com

---

*This troubleshooting guide is regularly updated based on common issues and user feedback.*