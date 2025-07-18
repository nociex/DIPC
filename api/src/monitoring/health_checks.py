"""Comprehensive health check utilities for all system components."""

import asyncio
import time
from typing import Dict, Any, Optional
import aiohttp
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database.connection import get_database_health, AsyncSessionLocal
from ..config import settings, get_llm_provider_config
import structlog

logger = structlog.get_logger(__name__)


class HealthChecker:
    """Centralized health checking for all system components."""
    
    def __init__(self):
        self.redis_client = None
        self.http_session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.redis_client = redis.from_url(settings.redis_url)
        self.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.redis_client:
            await self.redis_client.close()
        if self.http_session:
            await self.http_session.close()
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database health and performance."""
        return await get_database_health()
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis/message queue health."""
        start_time = time.time()
        health_status = {
            "healthy": False,
            "service": "redis",
            "response_time": 0.0,
            "connection_info": {},
            "error": None
        }
        
        try:
            # Test basic connectivity
            await self.redis_client.ping()
            
            # Get Redis info
            info = await self.redis_client.info()
            health_status["connection_info"] = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
            
            # Test read/write operations
            test_key = "health_check_test"
            await self.redis_client.set(test_key, "test_value", ex=60)
            test_value = await self.redis_client.get(test_key)
            
            if test_value == b"test_value":
                health_status["healthy"] = True
                await self.redis_client.delete(test_key)
            
        except Exception as e:
            health_status["error"] = str(e)
            logger.error("Redis health check failed", error=str(e))
        
        health_status["response_time"] = time.time() - start_time
        return health_status
    
    async def check_celery_queues(self) -> Dict[str, Any]:
        """Check Celery message queue status."""
        start_time = time.time()
        health_status = {
            "healthy": False,
            "service": "celery_queues",
            "response_time": 0.0,
            "queue_stats": {},
            "error": None
        }
        
        try:
            # Check queue lengths
            queue_names = ['archive_processing', 'document_parsing', 'vectorization', 'cleanup']
            queue_stats = {}
            
            for queue_name in queue_names:
                queue_length = await self.redis_client.llen(queue_name)
                queue_stats[queue_name] = {
                    "length": queue_length,
                    "status": "healthy" if queue_length < 1000 else "warning"  # Arbitrary threshold
                }
            
            health_status["queue_stats"] = queue_stats
            health_status["healthy"] = True
            
        except Exception as e:
            health_status["error"] = str(e)
            logger.error("Celery queue health check failed", error=str(e))
        
        health_status["response_time"] = time.time() - start_time
        return health_status
    
    async def check_storage(self) -> Dict[str, Any]:
        """Check S3/MinIO storage health."""
        start_time = time.time()
        health_status = {
            "healthy": False,
            "service": "s3_storage",
            "response_time": 0.0,
            "bucket_info": {},
            "error": None
        }
        
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            # Create S3 client
            s3_client = boto3.client(
                's3',
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
                region_name='us-east-1'  # Default region
            )
            
            # Test bucket access
            response = s3_client.head_bucket(Bucket=settings.s3_bucket_name)
            
            # Get bucket location and basic info
            try:
                location = s3_client.get_bucket_location(Bucket=settings.s3_bucket_name)
                health_status["bucket_info"]["region"] = location.get('LocationConstraint', 'us-east-1')
            except ClientError:
                health_status["bucket_info"]["region"] = "unknown"
            
            # Test write/read operations
            test_key = f"health-check-{int(time.time())}"
            test_content = b"health check test"
            
            # Upload test object
            s3_client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=test_key,
                Body=test_content
            )
            
            # Download test object
            response = s3_client.get_object(
                Bucket=settings.s3_bucket_name,
                Key=test_key
            )
            
            if response['Body'].read() == test_content:
                health_status["healthy"] = True
            
            # Clean up test object
            s3_client.delete_object(
                Bucket=settings.s3_bucket_name,
                Key=test_key
            )
            
            health_status["bucket_info"]["bucket_name"] = settings.s3_bucket_name
            health_status["bucket_info"]["endpoint"] = settings.s3_endpoint_url
            
        except NoCredentialsError:
            health_status["error"] = "S3 credentials not configured"
        except ClientError as e:
            health_status["error"] = f"S3 client error: {str(e)}"
        except Exception as e:
            health_status["error"] = str(e)
            logger.error("S3 storage health check failed", error=str(e))
        
        health_status["response_time"] = time.time() - start_time
        return health_status
    
    async def check_vector_database(self) -> Dict[str, Any]:
        """Check vector database (Qdrant) health."""
        start_time = time.time()
        health_status = {
            "healthy": False,
            "service": "qdrant",
            "response_time": 0.0,
            "cluster_info": {},
            "error": None
        }
        
        try:
            # Check if Qdrant is accessible
            health_url = f"{settings.qdrant_url.rstrip('/')}/health"
            
            headers = {}
            if settings.qdrant_api_key:
                headers["api-key"] = settings.qdrant_api_key
            
            async with self.http_session.get(health_url, headers=headers) as response:
                if response.status == 200:
                    health_status["healthy"] = True
                    
                    # Get cluster info
                    try:
                        cluster_url = f"{settings.qdrant_url.rstrip('/')}/cluster"
                        async with self.http_session.get(cluster_url, headers=headers) as cluster_response:
                            if cluster_response.status == 200:
                                cluster_data = await cluster_response.json()
                                health_status["cluster_info"] = cluster_data.get("result", {})
                    except Exception as e:
                        logger.warning("Could not get Qdrant cluster info", error=str(e))
                else:
                    health_status["error"] = f"HTTP {response.status}"
                    
        except Exception as e:
            health_status["error"] = str(e)
            logger.error("Qdrant health check failed", error=str(e))
        
        health_status["response_time"] = time.time() - start_time
        return health_status
    
    async def check_llm_providers(self) -> Dict[str, Any]:
        """Check LLM provider availability."""
        start_time = time.time()
        health_status = {
            "healthy": False,
            "service": "llm_providers",
            "response_time": 0.0,
            "providers": {},
            "error": None
        }
        
        try:
            providers = get_llm_provider_config()
            provider_results = {}
            healthy_providers = 0
            
            for provider_name, config in providers.items():
                provider_health = await self._check_llm_provider(provider_name, config)
                provider_results[provider_name] = provider_health
                if provider_health["healthy"]:
                    healthy_providers += 1
            
            health_status["providers"] = provider_results
            health_status["healthy"] = healthy_providers > 0
            
            if healthy_providers == 0:
                health_status["error"] = "No LLM providers are available"
            
        except Exception as e:
            health_status["error"] = str(e)
            logger.error("LLM provider health check failed", error=str(e))
        
        health_status["response_time"] = time.time() - start_time
        return health_status
    
    async def _check_llm_provider(self, provider_name: str, config: Dict[str, str]) -> Dict[str, Any]:
        """Check individual LLM provider health."""
        provider_health = {
            "healthy": False,
            "response_time": 0.0,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            # Test provider availability with a simple models list request
            models_url = f"{config['base_url'].rstrip('/')}/models"
            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json"
            }
            
            async with self.http_session.get(models_url, headers=headers) as response:
                if response.status == 200:
                    provider_health["healthy"] = True
                    data = await response.json()
                    if "data" in data:
                        provider_health["available_models"] = len(data["data"])
                elif response.status == 401:
                    provider_health["error"] = "Authentication failed"
                elif response.status == 403:
                    provider_health["error"] = "Access forbidden"
                else:
                    provider_health["error"] = f"HTTP {response.status}"
                    
        except asyncio.TimeoutError:
            provider_health["error"] = "Request timeout"
        except Exception as e:
            provider_health["error"] = str(e)
        
        provider_health["response_time"] = time.time() - start_time
        return provider_health
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive health status for all components."""
        start_time = time.time()
        
        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_celery_queues(),
            self.check_storage(),
            self.check_vector_database(),
            self.check_llm_providers(),
            return_exceptions=True
        )
        
        # Process results
        components = {}
        overall_healthy = True
        
        check_names = [
            "database",
            "redis",
            "celery_queues", 
            "storage",
            "vector_database",
            "llm_providers"
        ]
        
        for i, result in enumerate(health_checks):
            component_name = check_names[i]
            
            if isinstance(result, Exception):
                components[component_name] = {
                    "healthy": False,
                    "error": str(result),
                    "response_time": 0.0
                }
                overall_healthy = False
            else:
                components[component_name] = result
                if not result.get("healthy", False):
                    overall_healthy = False
        
        total_response_time = time.time() - start_time
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "service": "dipc-api",
            "version": "1.3.0",
            "timestamp": time.time(),
            "total_response_time": total_response_time,
            "components": components
        }


async def get_system_metrics() -> Dict[str, Any]:
    """Get system performance metrics."""
    import psutil
    
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get process-specific metrics
    process = psutil.Process()
    process_memory = process.memory_info()
    
    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            }
        },
        "process": {
            "memory": {
                "rss": process_memory.rss,
                "vms": process_memory.vms
            },
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads(),
            "create_time": process.create_time()
        },
        "timestamp": time.time()
    }


async def get_application_metrics() -> Dict[str, Any]:
    """Get application-specific metrics."""
    metrics = {
        "timestamp": time.time(),
        "database": {},
        "tasks": {},
        "error": None
    }
    
    try:
        async with AsyncSessionLocal() as session:
            # Get task statistics
            task_stats_query = text("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_processing_time
                FROM tasks 
                WHERE created_at > NOW() - INTERVAL '24 hours'
                GROUP BY status
            """)
            
            result = await session.execute(task_stats_query)
            task_stats = {}
            for row in result:
                task_stats[row.status] = {
                    "count": row.count,
                    "avg_processing_time": float(row.avg_processing_time) if row.avg_processing_time else None
                }
            
            metrics["tasks"] = task_stats
            
            # Get database metrics
            db_stats_query = text("""
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as tasks_last_hour,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as tasks_last_day
                FROM tasks
            """)
            
            result = await session.execute(db_stats_query)
            row = result.fetchone()
            metrics["database"] = {
                "total_tasks": row.total_tasks,
                "tasks_last_hour": row.tasks_last_hour,
                "tasks_last_day": row.tasks_last_day
            }
            
    except Exception as e:
        metrics["error"] = str(e)
        logger.error("Failed to get application metrics", error=str(e))
    
    return metrics