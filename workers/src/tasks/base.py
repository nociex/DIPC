"""Base task classes and utilities for Celery workers."""

import time
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import UUID

import structlog
from celery import Task
from celery.exceptions import Retry, WorkerLostError
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from celery_app import celery_app
from config import worker_settings

# Configure structured logging
logger = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskResult(BaseModel):
    """Standard task result model."""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class BaseTask(Task):
    """Base Celery task class with common functionality."""
    
    # Task configuration
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True
    
    def __init__(self):
        """Initialize base task."""
        self.start_time = None
        self.task_logger = None
    
    def before_start(self, task_id, args, kwargs):
        """Called before task execution starts."""
        self.start_time = time.time()
        self.task_logger = logger.bind(
            task_id=task_id,
            task_name=self.name,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys())
        )
        
        self.task_logger.info("Task starting")
        
        # Update task status to processing
        self.update_task_status(task_id, TaskStatus.PROCESSING)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        processing_time = time.time() - self.start_time if self.start_time else None
        
        self.task_logger.info(
            "Task completed successfully",
            processing_time=processing_time,
            result_type=type(retval).__name__
        )
        
        # Update task status to completed
        self.update_task_status(
            task_id, 
            TaskStatus.COMPLETED,
            result=retval,
            processing_time=processing_time
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        processing_time = time.time() - self.start_time if self.start_time else None
        
        # Determine if this is a retry or final failure
        retry_count = self.request.retries if hasattr(self, 'request') else 0
        max_retries = self.retry_kwargs.get('max_retries', 3)
        
        is_final_failure = retry_count >= max_retries
        status = TaskStatus.FAILED if is_final_failure else TaskStatus.RETRYING
        
        error_details = {
            'exception_type': type(exc).__name__,
            'exception_args': str(exc.args) if exc.args else None,
            'traceback': str(einfo.traceback) if einfo else None,
            'retry_count': retry_count,
            'max_retries': max_retries,
            'is_final_failure': is_final_failure
        }
        
        self.task_logger.error(
            "Task failed",
            error=str(exc),
            retry_count=retry_count,
            max_retries=max_retries,
            is_final_failure=is_final_failure,
            processing_time=processing_time,
            error_details=error_details
        )
        
        # Update task status
        self.update_task_status(
            task_id,
            status,
            error_message=str(exc),
            error_details=error_details,
            processing_time=processing_time
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        retry_count = self.request.retries if hasattr(self, 'request') else 0
        
        self.task_logger.warning(
            "Task retrying",
            error=str(exc),
            retry_count=retry_count,
            next_retry_in=self.retry_kwargs.get('countdown', 60)
        )
        
        # Update task status to retrying
        self.update_task_status(
            task_id,
            TaskStatus.RETRYING,
            error_message=f"Retry {retry_count}: {str(exc)}"
        )
    
    def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        processing_time: Optional[float] = None
    ):
        """Update task status in database."""
        try:
            # Import here to avoid circular imports during testing
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from api.src.database.repositories import TaskRepository
            
            task_repo = TaskRepository()
            
            update_data = {
                'status': status.value,
                'updated_at': datetime.utcnow()
            }
            
            if result is not None:
                update_data['results'] = result
            
            if error_message is not None:
                update_data['error_message'] = error_message
            
            if error_details is not None:
                update_data['error_details'] = error_details
            
            if processing_time is not None:
                update_data['processing_time'] = processing_time
            
            if status == TaskStatus.COMPLETED:
                update_data['completed_at'] = datetime.utcnow()
            
            task_repo.update_task(UUID(task_id), update_data)
            
        except Exception as e:
            # Log error but don't fail the task
            logger.error(
                "Failed to update task status",
                task_id=task_id,
                status=status.value,
                error=str(e)
            )
    
    def should_retry(self, exc: Exception) -> bool:
        """Determine if task should be retried based on exception type."""
        # Don't retry for certain types of errors
        non_retryable_exceptions = (
            ValueError,  # Invalid input data
            TypeError,   # Programming errors
            KeyError,    # Missing required data
        )
        
        if isinstance(exc, non_retryable_exceptions):
            return False
        
        # Don't retry if worker was lost
        if isinstance(exc, WorkerLostError):
            return False
        
        # Retry for network/service errors
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            OSError,
        )
        
        return isinstance(exc, retryable_exceptions)
    
    def apply_async_with_monitoring(self, args=None, kwargs=None, **options):
        """Apply task asynchronously with enhanced monitoring."""
        # Add correlation ID for tracing
        if 'headers' not in options:
            options['headers'] = {}
        
        options['headers']['correlation_id'] = options.get('task_id', 'unknown')
        options['headers']['submitted_at'] = datetime.utcnow().isoformat()
        
        # Apply the task
        result = self.apply_async(args=args, kwargs=kwargs, **options)
        
        logger.info(
            "Task submitted",
            task_id=result.id,
            task_name=self.name,
            queue=options.get('queue', 'default'),
            correlation_id=options['headers']['correlation_id']
        )
        
        return result


def create_task_result(
    task_id: str,
    status: TaskStatus,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    error_details: Optional[Dict[str, Any]] = None,
    processing_time: Optional[float] = None,
    retry_count: int = 0
) -> TaskResult:
    """Create a standardized task result."""
    return TaskResult(
        task_id=task_id,
        status=status,
        result=result,
        error_message=error_message,
        error_details=error_details,
        processing_time=processing_time,
        retry_count=retry_count,
        updated_at=datetime.utcnow(),
        completed_at=datetime.utcnow() if status in [TaskStatus.COMPLETED, TaskStatus.FAILED] else None
    )


def validate_task_input(data: Dict[str, Any], required_fields: list) -> None:
    """Validate task input data."""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate task_id format if present
    if 'task_id' in data:
        try:
            UUID(data['task_id'])
        except ValueError:
            raise ValueError(f"Invalid task_id format: {data['task_id']}")


def get_task_timeout(task_type: str) -> int:
    """Get timeout for specific task type."""
    timeouts = {
        'archive_processing': worker_settings.processing_timeout_seconds,
        'document_parsing': worker_settings.processing_timeout_seconds,
        'vectorization': worker_settings.processing_timeout_seconds // 2,
        'cleanup': 60  # 1 minute for cleanup tasks
    }
    
    return timeouts.get(task_type, worker_settings.processing_timeout_seconds)


# Register the base task class with Celery
celery_app.Task = BaseTask