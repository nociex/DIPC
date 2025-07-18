"""Worker health check utilities and monitoring."""

import time
import psutil
from typing import Dict, Any
from celery import current_app
from redis import Redis
import structlog

from ..config import worker_settings

logger = structlog.get_logger(__name__)


def get_worker_health_status() -> Dict[str, Any]:
    """Get comprehensive worker health status."""
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "service": "dipc-worker",
        "version": "1.3.0",
        "timestamp": time.time(),
        "worker_info": {},
        "system_metrics": {},
        "celery_status": {},
        "dependencies": {},
        "error": None
    }
    
    try:
        # Get worker information
        health_status["worker_info"] = _get_worker_info()
        
        # Get system metrics
        health_status["system_metrics"] = _get_system_metrics()
        
        # Get Celery status
        health_status["celery_status"] = _get_celery_status()
        
        # Check dependencies
        health_status["dependencies"] = _check_dependencies()
        
        # Determine overall health
        overall_healthy = all([
            health_status["celery_status"].get("broker_healthy", False),
            health_status["dependencies"].get("redis_healthy", False),
            health_status["system_metrics"].get("memory_available", True),
            health_status["system_metrics"].get("disk_available", True)
        ])
        
        health_status["status"] = "healthy" if overall_healthy else "unhealthy"
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        logger.error("Worker health check failed", error=str(e))
    
    health_status["response_time"] = time.time() - start_time
    return health_status


def _get_worker_info() -> Dict[str, Any]:
    """Get worker-specific information."""
    try:
        import socket
        import os
        
        return {
            "hostname": socket.gethostname(),
            "process_id": os.getpid(),
            "worker_id": f"{socket.gethostname()}-{os.getpid()}",
            "environment": worker_settings.environment,
            "max_file_size_mb": worker_settings.max_file_size_mb,
            "processing_timeout": worker_settings.processing_timeout_seconds,
            "temp_dir": worker_settings.temp_directory,
            "supported_formats": [
                "pdf", "png", "jpg", "jpeg", "gif", "webp", 
                "txt", "doc", "docx", "zip"
            ]
        }
    except Exception as e:
        logger.error("Failed to get worker info", error=str(e))
        return {"error": str(e)}


def _get_system_metrics() -> Dict[str, Any]:
    """Get system performance metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_available = memory.percent < 90  # Consider unhealthy if >90% used
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_available = (disk.free / disk.total) > 0.1  # Consider unhealthy if <10% free
        
        # Process metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            },
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
            },
            "process": {
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "create_time": process.create_time()
            },
            "memory_available": memory_available,
            "disk_available": disk_available
        }
    except Exception as e:
        logger.error("Failed to get system metrics", error=str(e))
        return {"error": str(e)}


def _get_celery_status() -> Dict[str, Any]:
    """Get Celery-specific status information."""
    try:
        # Get Celery app instance
        app = current_app
        
        # Check broker connection
        broker_healthy = False
        try:
            # Test broker connection
            with app.connection() as conn:
                conn.ensure_connection(max_retries=3)
                broker_healthy = True
        except Exception as e:
            logger.warning("Broker connection failed", error=str(e))
        
        # Get active tasks
        inspect = app.control.inspect()
        active_tasks = inspect.active()
        reserved_tasks = inspect.reserved()
        
        # Get worker statistics
        stats = inspect.stats()
        
        return {
            "broker_healthy": broker_healthy,
            "broker_url": worker_settings.celery_broker_url,
            "active_tasks": len(active_tasks.get(list(active_tasks.keys())[0], [])) if active_tasks else 0,
            "reserved_tasks": len(reserved_tasks.get(list(reserved_tasks.keys())[0], [])) if reserved_tasks else 0,
            "worker_stats": stats.get(list(stats.keys())[0], {}) if stats else {},
            "queues": [
                "archive_processing",
                "document_parsing", 
                "vectorization",
                "cleanup"
            ]
        }
    except Exception as e:
        logger.error("Failed to get Celery status", error=str(e))
        return {
            "broker_healthy": False,
            "error": str(e)
        }


def _check_dependencies() -> Dict[str, Any]:
    """Check external dependencies health."""
    dependencies = {
        "redis_healthy": False,
        "llm_providers": {},
        "vector_db_healthy": False,
        "storage_healthy": False
    }
    
    # Check Redis
    try:
        redis_client = Redis.from_url(worker_settings.redis_url)
        redis_client.ping()
        dependencies["redis_healthy"] = True
        
        # Get Redis info
        redis_info = redis_client.info()
        dependencies["redis_info"] = {
            "version": redis_info.get("redis_version"),
            "connected_clients": redis_info.get("connected_clients"),
            "used_memory_human": redis_info.get("used_memory_human")
        }
    except Exception as e:
        dependencies["redis_error"] = str(e)
        logger.warning("Redis health check failed", error=str(e))
    
    # Check LLM providers (basic connectivity)
    try:
        import requests
        
        providers = {}
        if hasattr(worker_settings, 'openai_api_key') and worker_settings.openai_api_key:
            providers["openai"] = {
                "base_url": "https://api.openai.com/v1",
                "api_key": worker_settings.openai_api_key
            }
        
        if hasattr(worker_settings, 'openrouter_api_key') and worker_settings.openrouter_api_key:
            providers["openrouter"] = {
                "base_url": "https://openrouter.ai/api/v1", 
                "api_key": worker_settings.openrouter_api_key
            }
        
        for provider_name, config in providers.items():
            try:
                response = requests.get(
                    f"{config['base_url']}/models",
                    headers={"Authorization": f"Bearer {config['api_key']}"},
                    timeout=5
                )
                dependencies["llm_providers"][provider_name] = {
                    "healthy": response.status_code == 200,
                    "status_code": response.status_code
                }
            except Exception as e:
                dependencies["llm_providers"][provider_name] = {
                    "healthy": False,
                    "error": str(e)
                }
                
    except Exception as e:
        dependencies["llm_providers_error"] = str(e)
    
    # Check Vector Database (Qdrant)
    try:
        import requests
        
        qdrant_url = getattr(worker_settings, 'qdrant_url', 'http://localhost:6333')
        response = requests.get(f"{qdrant_url}/health", timeout=5)
        dependencies["vector_db_healthy"] = response.status_code == 200
        
    except Exception as e:
        dependencies["vector_db_error"] = str(e)
        logger.warning("Vector DB health check failed", error=str(e))
    
    # Check Storage (S3/MinIO)
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        s3_client = boto3.client(
            's3',
            endpoint_url=worker_settings.s3_endpoint_url,
            aws_access_key_id=worker_settings.s3_access_key_id,
            aws_secret_access_key=worker_settings.s3_secret_access_key,
            region_name='us-east-1'
        )
        
        # Test bucket access
        s3_client.head_bucket(Bucket=worker_settings.s3_bucket_name)
        dependencies["storage_healthy"] = True
        
    except Exception as e:
        dependencies["storage_error"] = str(e)
        logger.warning("Storage health check failed", error=str(e))
    
    return dependencies


def get_worker_metrics() -> Dict[str, Any]:
    """Get detailed worker performance metrics."""
    try:
        metrics = {
            "timestamp": time.time(),
            "system": _get_system_metrics(),
            "celery": _get_celery_status(),
            "task_history": _get_task_history(),
            "error_rates": _get_error_rates()
        }
        
        return metrics
        
    except Exception as e:
        logger.error("Failed to get worker metrics", error=str(e))
        return {
            "timestamp": time.time(),
            "error": str(e)
        }


def _get_task_history() -> Dict[str, Any]:
    """Get recent task execution history."""
    try:
        # This would typically query a database or Redis for task history
        # For now, return placeholder data
        return {
            "last_hour": {
                "completed": 0,
                "failed": 0,
                "avg_processing_time": 0.0
            },
            "last_24_hours": {
                "completed": 0,
                "failed": 0,
                "avg_processing_time": 0.0
            }
        }
    except Exception as e:
        return {"error": str(e)}


def _get_error_rates() -> Dict[str, Any]:
    """Get error rates and common failure patterns."""
    try:
        # This would typically analyze error logs or database records
        # For now, return placeholder data
        return {
            "error_rate_percent": 0.0,
            "common_errors": [],
            "retry_rate_percent": 0.0
        }
    except Exception as e:
        return {"error": str(e)}


def check_worker_readiness() -> bool:
    """Check if worker is ready to process tasks."""
    try:
        health_status = get_worker_health_status()
        return health_status["status"] == "healthy"
    except Exception:
        return False