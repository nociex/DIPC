"""Celery application configuration and setup."""

import os
from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from kombu import Queue
import structlog

from config import worker_settings, get_celery_config, validate_worker_settings

# Configure structured logging
logger = structlog.get_logger(__name__)

# Create Celery application
celery_app = Celery('document_intelligence_workers')

# Load configuration
celery_config = get_celery_config()
celery_app.conf.update(celery_config)

# Define queues with specific routing and priority
celery_app.conf.task_routes = {
    'workers.tasks.archive.process_archive_task': {'queue': 'archive_processing'},
    'workers.tasks.parsing.parse_document_task': {'queue': 'document_parsing'},
    'workers.tasks.vectorization.vectorize_content_task': {'queue': 'vectorization'},
    'workers.tasks.cleanup.cleanup_temporary_files_task': {'queue': 'cleanup'},
}

# Configure queues with different priorities and settings
celery_app.conf.task_queues = (
    # High priority for archive processing
    Queue('archive_processing', routing_key='archive_processing', 
          queue_arguments={'x-max-priority': 10}),
    
    # Main processing queue
    Queue('document_parsing', routing_key='document_parsing',
          queue_arguments={'x-max-priority': 5}),
    
    # Lower priority for vectorization
    Queue('vectorization', routing_key='vectorization',
          queue_arguments={'x-max-priority': 3}),
    
    # Lowest priority for cleanup tasks
    Queue('cleanup', routing_key='cleanup',
          queue_arguments={'x-max-priority': 1}),
)

# Additional Celery configuration
celery_app.conf.update(
    # Task execution settings
    task_time_limit=worker_settings.processing_timeout_seconds,
    task_soft_time_limit=worker_settings.processing_timeout_seconds - 30,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Monitoring and health checks
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Security settings
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    
    # Serialization settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone settings
    timezone='UTC',
    enable_utc=True,
)


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    try:
        validate_worker_settings()
        logger.info(
            "Worker started successfully",
            worker_id=sender.hostname if sender else "unknown",
            queues=list(celery_app.conf.task_queues or []),
            environment=worker_settings.environment
        )
    except Exception as e:
        logger.error(
            "Worker startup validation failed",
            error=str(e),
            worker_id=sender.hostname if sender else "unknown"
        )
        raise


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info(
        "Worker shutting down",
        worker_id=sender.hostname if sender else "unknown"
    )


def get_celery_health_status():
    """Get Celery worker and broker health status."""
    try:
        # Check broker connection
        inspect = celery_app.control.inspect()
        
        # Get active workers
        active_workers = inspect.active()
        registered_tasks = inspect.registered()
        
        # Check if broker is responsive
        broker_status = "healthy" if active_workers is not None else "unhealthy"
        
        # Count active workers
        worker_count = len(active_workers) if active_workers else 0
        
        # Get queue lengths (requires additional setup with Redis)
        queue_stats = {}
        try:
            from redis import Redis
            redis_client = Redis.from_url(worker_settings.redis_url)
            
            for queue_name in ['archive_processing', 'document_parsing', 'vectorization', 'cleanup']:
                queue_length = redis_client.llen(queue_name)
                queue_stats[queue_name] = queue_length
                
        except Exception as e:
            logger.warning("Could not get queue statistics", error=str(e))
            queue_stats = {"error": "Unable to fetch queue stats"}
        
        return {
            "status": "healthy" if broker_status == "healthy" and worker_count > 0 else "unhealthy",
            "broker_status": broker_status,
            "active_workers": worker_count,
            "queue_stats": queue_stats,
            "registered_tasks": list(registered_tasks.keys()) if registered_tasks else [],
            "configuration": {
                "max_file_size_mb": worker_settings.max_file_size_mb,
                "processing_timeout": worker_settings.processing_timeout_seconds,
                "environment": worker_settings.environment
            }
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Auto-discover tasks
celery_app.autodiscover_tasks(['workers.tasks'])

# Export the app
__all__ = ['celery_app', 'get_celery_health_status']