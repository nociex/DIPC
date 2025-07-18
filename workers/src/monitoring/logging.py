"""Centralized logging configuration and utilities for workers."""

import logging
import sys
import time
import uuid
from typing import Dict, Any, Optional
from contextvars import ContextVar
import structlog
from structlog.types import EventDict, Processor
import json

from ..config import worker_settings

# Context variables for task tracing
task_id_var: ContextVar[Optional[str]] = ContextVar('task_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
worker_id_var: ContextVar[Optional[str]] = ContextVar('worker_id', default=None)


def add_worker_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add worker context to log entries."""
    task_id = task_id_var.get()
    user_id = user_id_var.get()
    worker_id = worker_id_var.get()
    
    if task_id:
        event_dict['task_id'] = task_id
    if user_id:
        event_dict['user_id'] = user_id
    if worker_id:
        event_dict['worker_id'] = worker_id
    
    return event_dict


def add_service_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service context to log entries."""
    event_dict['service'] = 'dipc-worker'
    event_dict['version'] = '1.3.0'
    event_dict['environment'] = worker_settings.environment
    return event_dict


def add_performance_metrics(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add performance metrics to log entries."""
    # Add timestamp if not present
    if 'timestamp' not in event_dict:
        event_dict['timestamp'] = time.time()
    
    return event_dict


def filter_sensitive_data(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Filter sensitive data from log entries."""
    sensitive_keys = [
        'password', 'token', 'api_key', 'secret', 'authorization',
        'cookie', 'session', 'csrf_token', 'private_key'
    ]
    
    def _filter_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively filter sensitive data from dictionaries."""
        filtered = {}
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                filtered[key] = '[REDACTED]'
            elif isinstance(value, dict):
                filtered[key] = _filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [_filter_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                filtered[key] = value
        return filtered
    
    # Filter the entire event dict
    for key, value in list(event_dict.items()):
        if isinstance(value, dict):
            event_dict[key] = _filter_dict(value)
        elif any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            event_dict[key] = '[REDACTED]'
    
    return event_dict


def configure_worker_logging():
    """Configure structured logging for workers."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, worker_settings.log_level.upper())
    )
    
    # Configure processors based on environment
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_service_context,
        add_worker_context,
        add_performance_metrics,
        filter_sensitive_data,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add appropriate renderer based on environment
    if worker_settings.environment == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class TaskTracker:
    """Context manager for tracking task execution in workers."""
    
    def __init__(self, task_id: str, task_type: str, user_id: Optional[str] = None, worker_id: Optional[str] = None):
        self.task_id = task_id
        self.task_type = task_type
        self.user_id = user_id
        self.worker_id = worker_id or self._get_worker_id()
        self.start_time = time.time()
        self.logger = structlog.get_logger(__name__)
        
        # Store previous context values
        self.prev_task_id = None
        self.prev_user_id = None
        self.prev_worker_id = None
    
    def _get_worker_id(self) -> str:
        """Generate worker ID from hostname and PID."""
        import socket
        import os
        return f"{socket.gethostname()}-{os.getpid()}"
    
    def __enter__(self):
        """Enter task tracking context."""
        # Store previous values
        self.prev_task_id = task_id_var.get()
        self.prev_user_id = user_id_var.get()
        self.prev_worker_id = worker_id_var.get()
        
        # Set new values
        task_id_var.set(self.task_id)
        if self.user_id:
            user_id_var.set(self.user_id)
        if self.worker_id:
            worker_id_var.set(self.worker_id)
        
        self.logger.info(
            "Task started",
            task_type=self.task_type
        )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit task tracking context."""
        # Restore previous values
        task_id_var.set(self.prev_task_id)
        user_id_var.set(self.prev_user_id)
        worker_id_var.set(self.prev_worker_id)
        
        # Log task completion
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                "Task failed",
                task_type=self.task_type,
                duration=duration,
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None
            )
        else:
            self.logger.info(
                "Task completed successfully",
                task_type=self.task_type,
                duration=duration
            )


class WorkerPerformanceLogger:
    """Utility for logging worker performance metrics."""
    
    def __init__(self, operation_name: str, logger: Optional[structlog.BoundLogger] = None):
        self.operation_name = operation_name
        self.logger = logger or structlog.get_logger(__name__)
        self.start_time = None
        self.metrics = {}
    
    def start(self):
        """Start performance tracking."""
        self.start_time = time.time()
        self.logger.debug(
            "Operation started",
            operation=self.operation_name
        )
    
    def add_metric(self, name: str, value: Any):
        """Add a custom metric."""
        self.metrics[name] = value
    
    def finish(self, success: bool = True, error: Optional[str] = None):
        """Finish performance tracking and log results."""
        if self.start_time is None:
            self.logger.warning("Performance tracking not started", operation=self.operation_name)
            return
        
        duration = time.time() - self.start_time
        
        log_data = {
            "operation": self.operation_name,
            "duration": duration,
            "success": success,
            **self.metrics
        }
        
        if error:
            log_data["error"] = error
        
        if success:
            self.logger.info("Operation completed", **log_data)
        else:
            self.logger.error("Operation failed", **log_data)


class WorkerErrorTracker:
    """Utility for tracking and categorizing worker errors."""
    
    def __init__(self, logger: Optional[structlog.BoundLogger] = None):
        self.logger = logger or structlog.get_logger(__name__)
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "error",
        category: Optional[str] = None
    ):
        """Log an error with context and categorization."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity,
        }
        
        if category:
            error_data["error_category"] = category
        
        if context:
            error_data["context"] = context
        
        # Add stack trace for debugging
        if worker_settings.environment == "development":
            import traceback
            error_data["stack_trace"] = traceback.format_exc()
        
        self.logger.error("Error occurred", **error_data)
    
    def log_task_error(self, error: Exception, task_type: str, file_path: Optional[str] = None):
        """Log task processing errors."""
        context = {"task_type": task_type}
        if file_path:
            context["file_path"] = file_path
        
        self.log_error(
            error,
            context=context,
            category="task_processing"
        )
    
    def log_llm_error(self, error: Exception, provider: str, model: str):
        """Log LLM service errors."""
        self.log_error(
            error,
            context={"provider": provider, "model": model},
            category="llm_service"
        )
    
    def log_storage_error(self, error: Exception, operation: str, file_path: Optional[str] = None):
        """Log storage errors."""
        context = {"operation": operation}
        if file_path:
            context["file_path"] = file_path
        
        self.log_error(
            error,
            context=context,
            category="storage"
        )
    
    def log_vector_db_error(self, error: Exception, operation: str):
        """Log vector database errors."""
        self.log_error(
            error,
            context={"operation": operation},
            category="vector_database"
        )


class WorkerMetricsCollector:
    """Utility for collecting worker metrics."""
    
    def __init__(self, logger: Optional[structlog.BoundLogger] = None):
        self.logger = logger or structlog.get_logger(__name__)
    
    def log_task_metrics(
        self,
        task_type: str,
        status: str,
        duration: float,
        file_size: Optional[int] = None,
        processing_cost: Optional[float] = None,
        tokens_used: Optional[int] = None
    ):
        """Log task processing metrics."""
        metrics = {
            "metric_type": "task_processing",
            "task_type": task_type,
            "status": status,
            "duration": duration
        }
        
        if file_size:
            metrics["file_size"] = file_size
        if processing_cost:
            metrics["processing_cost"] = processing_cost
        if tokens_used:
            metrics["tokens_used"] = tokens_used
        
        self.logger.info("Task metrics", **metrics)
    
    def log_resource_usage(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float
    ):
        """Log system resource usage."""
        self.logger.info(
            "Resource usage",
            metric_type="resource_usage",
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent
        )
    
    def log_llm_usage(
        self,
        provider: str,
        model: str,
        tokens_used: int,
        cost: float,
        duration: float
    ):
        """Log LLM usage metrics."""
        self.logger.info(
            "LLM usage",
            metric_type="llm_usage",
            provider=provider,
            model=model,
            tokens_used=tokens_used,
            cost=cost,
            duration=duration
        )


# Global instances
worker_error_tracker = WorkerErrorTracker()
worker_metrics_collector = WorkerMetricsCollector()


def get_task_id() -> Optional[str]:
    """Get current task ID from context."""
    return task_id_var.get()


def get_user_id() -> Optional[str]:
    """Get current user ID from context."""
    return user_id_var.get()


def get_worker_id() -> Optional[str]:
    """Get current worker ID from context."""
    return worker_id_var.get()


def create_worker_logger(name: str, **context) -> structlog.BoundLogger:
    """Create a worker logger with additional context."""
    logger = structlog.get_logger(name)
    return logger.bind(**context)


# Initialize logging configuration
configure_worker_logging()